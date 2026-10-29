from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bot import Bot
from app.config import settings
from app.services.docker_service import DockerService


class WatchdogService:
    @staticmethod
    async def record_bot_crash(bot_id: str, db: AsyncSession) -> Bot | None:
        """
        Increments crash count for a bot.
        If crash_count reaches MAX_CRASH_RETRIES (5), stops the container permanently
        and marks status as 'crashed_stopped'.
        """
        result = await db.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()
        if not bot:
            return None

        bot.crash_count += 1
        if bot.crash_count >= settings.MAX_CRASH_RETRIES:
            bot.status = "crashed_stopped"
            # Stop Docker container
            DockerService.stop_bot_container(bot_id)
        else:
            bot.status = "crashed"

        await db.commit()
        await db.refresh(bot)
        return bot

    @staticmethod
    async def reset_bot_crash_count(bot_id: str, db: AsyncSession) -> Bot | None:
        """Resets the crash count when a user manually starts or restarts successfully."""
        result = await db.execute(select(Bot).where(Bot.id == bot_id))
        bot = result.scalar_one_or_none()
        if not bot:
            return None

        bot.crash_count = 0
        bot.status = "running"
        await db.commit()
        await db.refresh(bot)
        return bot
