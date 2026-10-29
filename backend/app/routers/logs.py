import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.bot import Bot
from app.routers.auth import get_current_user
from app.services.redis_service import redis_service

router = APIRouter(prefix="/bots", tags=["Logs"])


@router.get("/{bot_id}/logs")
async def get_bot_logs(
    bot_id: str,
    tail: int = Query(150, ge=10, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Reads directly from Redis ring buffer (last ~1000 lines). Zero Postgres overhead!
    """
    res = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = res.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot topilmadi.")
    if bot.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q.")

    logs = await redis_service.get_bot_logs(bot_id, tail=tail)
    return {"bot_id": bot.id, "logs": "\n".join(logs) if logs else "Jurnallar bo'sh."}


@router.get("/{bot_id}/logs/sse")
async def stream_bot_logs_sse(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE Log Streaming with Backpressure and Single-Stream Enforcement:
    - Only 1 active log stream per user per bot is allowed at any time.
    - Automatically releases stream lock on disconnect or idle timeout.
    """
    res = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = res.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot topilmadi.")
    if bot.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q.")

    r = await redis_service.get_client()
    lock_key = f"bothost:log_stream:{current_user.id}:{bot_id}"

    # Enforce single stream per user per bot
    existing_lock = await r.get(lock_key)
    if existing_lock:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Ushbu bot uchun jurnallar oqimi boshqa oynada allaqachon ochilgan. Resurslarni tejash uchun bir vaqtda faqat 1 ta oqimga ruxsat etiladi.",
        )

    await r.set(lock_key, "active", ex=300)  # 5 min auto-expire guard

    async def log_event_generator():
        last_seen_count = 0
        idle_seconds = 0
        max_idle_seconds = 300  # 5 minutes auto-close

        try:
            while idle_seconds < max_idle_seconds:
                # Refresh stream lock
                await r.expire(lock_key, 60)

                current_logs = await redis_service.get_bot_logs(bot_id, tail=50)
                if len(current_logs) > last_seen_count or last_seen_count == 0:
                    new_lines = current_logs[last_seen_count:] if last_seen_count > 0 else current_logs
                    last_seen_count = len(current_logs)
                    for line in new_lines:
                        yield f"data: {json.dumps({'timestamp': time.time(), 'message': line})}\n\n"
                    idle_seconds = 0
                else:
                    # Heartbeat to keep connection open and detect client disconnect
                    yield ": ping\n\n"
                    idle_seconds += 2

                await asyncio.sleep(2.0)
        finally:
            # Clean up stream lock on client disconnect
            await r.delete(lock_key)

    import time
    return StreamingResponse(
        log_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
