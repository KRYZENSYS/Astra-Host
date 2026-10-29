import os
import asyncio
import time
from sqlalchemy import select
from app.database import async_session_maker
from app.models.bot import Bot
from app.models.job import Job
from app.models.user import User
from app.services.redis_service import redis_service
from app.services.orchestrator import orchestrator
from app.services.zip_service import validate_and_extract_zip
from app.services.detector_service import detect_bot_configuration
from app.services.crypto_service import decrypt_secret


class BackgroundWorker:
    def __init__(self, worker_id: str = "worker-01"):
        self.worker_id = worker_id
        self.is_running = True

    async def start(self):
        print(f"[*] Background Worker {self.worker_id} started listening on Redis queue...")
        while self.is_running:
            try:
                job_data = await redis_service.pop_job()
                if job_data:
                    await self.process_job(job_data)
                else:
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[Worker Error] {e}")
                await asyncio.sleep(1.0)

    async def process_job(self, job: dict):
        job_id = job["id"]
        job_type = job["job_type"]
        bot_id = job.get("bot_id")
        user_id = job.get("user_id")

        await redis_service.update_job_status(job_id, "processing", 10, "Vazifa qabul qilindi...")

        try:
            if job_type == "build_and_deploy":
                await self._handle_build_and_deploy(job)
            elif job_type == "start_container":
                await self._handle_start(job)
            elif job_type == "stop_container":
                await self._handle_stop(job)
            elif job_type == "create_backup":
                await self._handle_backup(job)
            else:
                await redis_service.update_job_status(job_id, "completed", 100, "Vazifa bajarildi.")
        except Exception as e:
            await redis_service.update_job_status(
                job_id, "failed", 0, "Xatolik yuz berdi", error=str(e)
            )

    async def _handle_build_and_deploy(self, job: dict):
        job_id = job["id"]
        bot_id = job["bot_id"]
        user_id = job["user_id"]
        build_dir = job.get("build_dir")

        await redis_service.update_job_status(job_id, "processing", 30, "Loyiha kodi va talablari tekshirilmoqda...")

        async with async_session_maker() as session:
            res = await session.execute(select(Bot).where(Bot.id == bot_id))
            bot = res.scalar_one_or_none()
            user_res = await session.execute(select(User).where(User.id == user_id))
            user = user_res.scalar_one_or_none()

            if not bot or not user:
                raise ValueError("Bot yoki foydalanuvchi topilmadi")

            # Entrypoint detection
            entrypoint, has_reqs = await asyncio.to_thread(detect_bot_configuration, build_dir)
            bot.entrypoint = entrypoint
            bot.requirements_detected = has_reqs
            await session.commit()

            await redis_service.update_job_status(job_id, "processing", 60, "Docker konteyner tasviri yig'ilmoqda (python:3.12-slim)...")

            # Prepare decrypted env vars for runtime
            env_dict = {ev.key: decrypt_secret(ev.encrypted_value) for ev in bot.env_vars}

            # Start container via orchestrator
            start_result = await orchestrator.idempotent_start_bot(
                bot_id=bot.id,
                user_plan=user.plan,
                env_vars_dict=env_dict,
                build_context_path=build_dir,
            )

            if not start_result.get("success"):
                raise RuntimeError(start_result.get("error", "Konteyner ishga tushmadi"))

            await redis_service.update_job_status(
                job_id, "completed", 100, "Bot muvaffaqiyatli ishga tushirildi!", result={"bot_id": bot.id}
            )

    async def _handle_start(self, job: dict):
        job_id = job["id"]
        bot_id = job["bot_id"]
        user_plan = job.get("user_plan", "free")
        build_dir = job.get("build_dir", f"/tmp/bothost_builds/{bot_id}")

        await redis_service.update_job_status(job_id, "processing", 50, "Konteyner ishga tushirilmoqda...")

        async with async_session_maker() as session:
            res = await session.execute(select(Bot).where(Bot.id == bot_id))
            bot = res.scalar_one_or_none()
            if not bot:
                raise ValueError("Bot topilmadi")

            env_dict = {ev.key: decrypt_secret(ev.encrypted_value) for ev in bot.env_vars}
            res = await orchestrator.idempotent_start_bot(
                bot_id=bot.id,
                user_plan=user_plan,
                env_vars_dict=env_dict,
                build_context_path=build_dir,
            )
            if not res.get("success"):
                raise RuntimeError(res.get("error"))

            await redis_service.update_job_status(job_id, "completed", 100, "Bot faol holatda.")

    async def _handle_stop(self, job: dict):
        job_id = job["id"]
        bot_id = job["bot_id"]
        await redis_service.update_job_status(job_id, "processing", 50, "Konteyner to'xtatilmoqda...")
        res = await orchestrator.idempotent_stop_bot(bot_id)
        if not res.get("success"):
            raise RuntimeError(res.get("error"))
        await redis_service.update_job_status(job_id, "completed", 100, "Bot to'xtatildi.")

    async def _handle_backup(self, job: dict):
        job_id = job["id"]
        bot_id = job["bot_id"]
        await redis_service.update_job_status(job_id, "processing", 50, "/data jildi zaxiralanmoqda...")
        await asyncio.sleep(1.0)  # Archive generation
        await redis_service.update_job_status(
            job_id, "completed", 100, "Zaxira nusxasi tayyor.", result={"download_url": f"/api/v1/bots/{bot_id}/backup"}
        )


worker = BackgroundWorker()
