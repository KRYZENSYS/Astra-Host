import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from app.services.redis_service import redis_service
from app.routers.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/jobs", tags=["Background Jobs"])


@router.get("/{job_id}")
async def get_job_status(job_id: str, current_user: User = Depends(get_current_user)):
    """Polls async background task status."""
    r = await redis_service.get_client()
    raw = await r.get(f"bothost:job:{job_id}")
    if not raw:
        raise HTTPException(status_code=404, detail="Vazifa topilmadi yoki muddati tugagan.")
    return json.loads(raw)


@router.get("/{job_id}/sse")
async def stream_job_progress(job_id: str, current_user: User = Depends(get_current_user)):
    """SSE stream of job progress for real-time frontend updates."""
    async def event_generator():
        r = await redis_service.get_client()
        last_progress = -1
        idle_ticks = 0

        while idle_ticks < 120:  # 2 minutes max wait
            raw = await r.get(f"bothost:job:{job_id}")
            if raw:
                data = json.loads(raw)
                if data.get("progress_percent") != last_progress or data.get("status") in ["completed", "failed"]:
                    last_progress = data.get("progress_percent")
                    yield f"data: {json.dumps(data)}\n\n"

                if data.get("status") in ["completed", "failed"]:
                    break
            else:
                yield f'data: {{"status": "queued", "progress_percent": 0, "stage_message": "Navbatda turibdi..."}}\n\n'

            await asyncio.sleep(1.0)
            idle_ticks += 1

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
