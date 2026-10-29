import asyncio
from sqlalchemy import select
from app.database import async_session_maker
from app.models.bot import Bot
from app.services.docker_service import RealDockerService


async def reconcile_all_bots():
    """
    Syncs the database bot status with the actual real state of Docker containers.
    Runs on startup and every 15 seconds in background.
    """
    try:
        async with async_session_maker() as session:
            result = await session.execute(select(Bot))
            bots = result.scalars().all()

            for bot in bots:
                # Only reconcile if not in transient building/starting states
                if bot.status in ["running", "stopped", "crashed"]:
                    real_status = await asyncio.to_thread(
                        RealDockerService.get_container_real_status, bot.id
                    )
                    if real_status != bot.status:
                        bot.status = real_status
            await session.commit()
    except Exception as e:
        # Ignore Docker socket errors if offline during startup
        pass


async def start_reconciler_loop(interval_seconds: int = 15):
    """Background task running reconciliation every 15 seconds."""
    while True:
        await asyncio.sleep(interval_seconds)
        await reconcile_all_bots()
