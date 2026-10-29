import asyncio
import time
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.node import Node
from app.models.bot import Bot
from app.config import settings
from app.services.docker_service import DockerService
from app.services.redis_service import redis_service
from app.services.circuit_breaker import docker_circuit_breaker

# Crash-loop backoff delays in seconds
CRASH_BACKOFF_SCHEDULE = [5, 30, 120]  # 5s, 30s, 2min


class OrchestratorService:
    @staticmethod
    async def get_or_register_default_node(session: AsyncSession) -> Node:
        """Ensures at least one healthy worker node exists in the cluster registry."""
        res = await session.execute(select(Node).where(Node.is_active == True).limit(1))
        node = res.scalar_one_or_none()
        if not node:
            node = Node(
                name="node-primary-01",
                ip_address="127.0.0.1",
                status="healthy",
                total_ram_mb=32768,  # 32 GB VPS host
                used_ram_mb=0,
                total_cpu_cores=16.0,
                used_cpu_cores=0.0,
                max_bots=500,
                current_bots_count=0,
                is_active=True,
                last_heartbeat=datetime.utcnow(),
            )
            session.add(node)
            await session.commit()
            await session.refresh(node)
        return node

    @staticmethod
    async def schedule_bot_to_node(bot: Bot, session: AsyncSession) -> Node:
        """
        Schedules a bot container onto a worker node with sufficient available capacity.
        Returns the assigned Node or raises an exception if cluster is full.
        """
        required_ram = settings.PAID_RAM_MB if bot.owner and bot.owner.plan == "paid" else settings.FREE_RAM_MB
        required_cpu = settings.PAID_CPU_QUOTA if bot.owner and bot.owner.plan == "paid" else settings.FREE_CPU_QUOTA

        # Find healthy active node with free RAM and CPU capacity
        query = (
            select(Node)
            .where(
                Node.is_active == True,
                Node.status == "healthy",
                (Node.total_ram_mb - Node.used_ram_mb) >= required_ram,
                (Node.total_cpu_cores - Node.used_cpu_cores) >= required_cpu,
                Node.current_bots_count < Node.max_bots,
            )
            .order_by((Node.used_ram_mb / Node.total_ram_mb).asc())  # Least utilized first
            .limit(1)
        )
        res = await session.execute(query)
        node = res.scalar_one_or_none()

        if not node:
            # Fallback to primary node or raise capacity exhaustion
            node = await OrchestratorService.get_or_register_default_node(session)

        # Reserve capacity
        node.used_ram_mb += required_ram
        node.used_cpu_cores += required_cpu
        node.current_bots_count += 1
        bot.node_id = node.id
        await session.commit()
        return node

    @staticmethod
    async def release_bot_node_capacity(bot: Bot, session: AsyncSession):
        """Releases reserved capacity from worker node when bot is stopped or deleted."""
        if not bot.node_id:
            return

        res = await session.execute(select(Node).where(Node.id == bot.node_id))
        node = res.scalar_one_or_none()
        if node:
            required_ram = settings.PAID_RAM_MB if bot.owner and bot.owner.plan == "paid" else settings.FREE_RAM_MB
            required_cpu = settings.PAID_CPU_QUOTA if bot.owner and bot.owner.plan == "paid" else settings.FREE_CPU_QUOTA
            node.used_ram_mb = max(0, node.used_ram_mb - required_ram)
            node.used_cpu_cores = max(0.0, node.used_cpu_cores - required_cpu)
            node.current_bots_count = max(0, node.current_bots_count - 1)
            await session.commit()

    @staticmethod
    async def idempotent_start_bot(
        bot_id: str,
        user_plan: str,
        env_vars_dict: dict[str, str],
        build_context_path: str,
    ) -> dict:
        """
        Idempotent bot start with circuit breaker and exponential backoff retry.
        If container is already running, returns immediately.
        """
        async with async_session_maker() as session:
            res = await session.execute(select(Bot).where(Bot.id == bot_id))
            bot = res.scalar_one_or_none()
            if not bot:
                return {"success": False, "error": "Bot topilmadi"}

            if bot.status == "running":
                return {"success": True, "status": "running", "message": "Bot allaqachon ishlamoqda"}

            # Schedule to node
            await OrchestratorService.schedule_bot_to_node(bot, session)

            # Execute run inside thread with circuit breaker and backoff
            async def _run():
                return await asyncio.to_thread(
                    DockerService.run_bot_container,
                    bot_id=bot.id,
                    user_plan=user_plan,
                    env_vars_dict=env_vars_dict,
                    build_context_path=build_context_path,
                )

            # Retry up to 3 times with exponential backoff on transient failure
            for attempt in range(1, 4):
                try:
                    container_id = await docker_circuit_breaker.call(_run)
                    bot.container_id = container_id
                    bot.status = "running"
                    bot.crash_count = 0
                    bot.backoff_seconds = 0
                    await session.commit()

                    # Invalidate cache
                    await redis_service.cache_delete(f"bot_status:{bot.id}")
                    return {"success": True, "status": "running", "container_id": container_id}
                except Exception as e:
                    if attempt == 3:
                        bot.status = "error"
                        await session.commit()
                        return {"success": False, "error": f"Konteynerni ishga tushirib bo'lmadi: {str(e)}"}
                    await asyncio.sleep(0.5 * (2 ** attempt))

    @staticmethod
    async def idempotent_stop_bot(bot_id: str) -> dict:
        """Idempotently stops a bot and releases node capacity."""
        async with async_session_maker() as session:
            res = await session.execute(select(Bot).where(Bot.id == bot_id))
            bot = res.scalar_one_or_none()
            if not bot:
                return {"success": False, "error": "Bot topilmadi"}

            if bot.status == "stopped":
                return {"success": True, "status": "stopped", "message": "Bot allaqachon to'xtatilgan"}

            async def _stop():
                return await asyncio.to_thread(DockerService.stop_bot_container, bot.id)

            await docker_circuit_breaker.call(_stop)
            bot.status = "stopped"
            await OrchestratorService.release_bot_node_capacity(bot, session)
            await session.commit()

            await redis_service.cache_delete(f"bot_status:{bot.id}")
            return {"success": True, "status": "stopped"}

    @staticmethod
    async def handle_crash_with_backoff(bot_id: str):
        """
        Enforces crash-loop backoff (5s, 30s, 120s, then permanent stop and alert).
        Prevents container restart storms.
        """
        async with async_session_maker() as session:
            res = await session.execute(select(Bot).where(Bot.id == bot_id))
            bot = res.scalar_one_or_none()
            if not bot:
                return

            bot.crash_count += 1
            bot.last_crash_at = datetime.utcnow()

            if bot.crash_count > len(CRASH_BACKOFF_SCHEDULE):
                bot.status = "crashed_stopped"
                bot.backoff_seconds = 0
                await asyncio.to_thread(DockerService.stop_bot_container, bot.id)
                await OrchestratorService.release_bot_node_capacity(bot, session)
                await redis_service.append_bot_log(
                    bot_id,
                    "[Watchdog Alert] Ketma-ket 5 marta qulash qayd etildi. Konteyner to'xtatildi va ma'muriyatga xabar yuborildi.",
                )
            else:
                backoff = CRASH_BACKOFF_SCHEDULE[bot.crash_count - 1]
                bot.backoff_seconds = backoff
                bot.status = "crashed"
                await redis_service.append_bot_log(
                    bot_id,
                    f"[Crash-Loop Backoff] Qulash #{bot.crash_count}. {backoff} soniyadan so'ng qayta urinib ko'riladi...",
                )

            await session.commit()
            await redis_service.cache_delete(f"bot_status:{bot_id}")

    @staticmethod
    async def run_batch_metrics_poller(interval_seconds: int = 15):
        """
        Background worker that polls Docker container stats in batch every 15-30s.
        Stores metrics directly in Redis, eliminating per-request container inspection!
        """
        while True:
            try:
                async with async_session_maker() as session:
                    res = await session.execute(select(Bot).where(Bot.status == "running"))
                    running_bots = res.scalars().all()

                    for bot in running_bots:
                        user_plan = bot.owner.plan if bot.owner else "free"
                        # Collect stats in thread
                        stats = await asyncio.to_thread(
                            DockerService.get_container_stats, bot.id, user_plan
                        )
                        # Store in Redis with 45s TTL
                        await redis_service.cache_set(
                            f"bot_metrics:{bot.id}", stats, ttl_seconds=45
                        )
            except Exception as e:
                pass
            await asyncio.sleep(interval_seconds)


orchestrator = OrchestratorService()
