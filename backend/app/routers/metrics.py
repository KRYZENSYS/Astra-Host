from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.bot import Bot
from app.schemas.bot import BotMetricsOut
from app.routers.auth import get_current_user
from app.services.docker_service import DockerService

router = APIRouter(prefix="/bots", tags=["Metrics"])


@router.get("/{bot_id}/metrics", response_model=BotMetricsOut)
async def get_bot_metrics(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(Bot).where(Bot.id == bot_id)
    res = await db.execute(query)
    bot = res.scalar_one_or_none()

    if not bot:
        raise HTTPException(status_code=404, detail="Bot topilmadi.")
    if bot.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q.")

    stats = DockerService.get_container_stats(bot_id=bot.id, user_plan=current_user.plan)

    return BotMetricsOut(
        bot_id=bot.id,
        status=bot.status if bot.status != "running" else stats["status"],
        cpu_percent=stats["cpu_percent"] if bot.status == "running" else 0.0,
        memory_mb=stats["memory_mb"] if bot.status == "running" else 0.0,
        memory_limit_mb=stats["memory_limit_mb"],
        disk_usage_mb=stats["disk_usage_mb"],
        disk_limit_mb=stats["disk_limit_mb"],
        uptime_seconds=stats["uptime_seconds"] if bot.status == "running" else 0,
        timestamp=datetime.utcnow(),
    )
