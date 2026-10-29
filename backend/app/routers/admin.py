from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.models.bot import Bot
from app.models.audit_log import AuditLog
from app.schemas.auth import UserOut
from app.schemas.bot import BotOut, EnvVarOut
from app.schemas.admin import UserPlanUpdate, UserBanUpdate, SystemStatsOut
from app.routers.auth import get_current_admin
from app.services.docker_service import DockerService
from app.services.crypto_service import mask_secret

router = APIRouter(prefix="/admin", tags=["Admin Panel"])


@router.get("/users", response_model=list[UserOut])
async def list_all_users(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.put("/users/{user_id}/plan", response_model=UserOut)
async def update_user_plan(
    user_id: str,
    payload: UserPlanUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    old_plan = user.plan
    user.plan = payload.plan

    # Record in audit log
    db.add(
        AuditLog(
            user_email=admin.email,
            action="CHANGE_PLAN",
            details=f"Foydalanuvchi {user.email} rejasi '{old_plan}' dan '{payload.plan}' ga o'zgartirildi.",
        )
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.put("/users/{user_id}/ban", response_model=UserOut)
async def toggle_user_ban(
    user_id: str,
    payload: UserBanUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="O'z hisobingizni bloklay olmaysiz.")

    user.is_banned = payload.is_banned

    # If banned, stop all user's running bots
    if user.is_banned:
        bots_result = await db.execute(select(Bot).where(Bot.user_id == user.id))
        user_bots = bots_result.scalars().all()
        for bot in user_bots:
            if bot.status == "running":
                DockerService.stop_bot_container(bot.id)
                bot.status = "stopped"

    db.add(
        AuditLog(
            user_email=admin.email,
            action="BAN_USER" if payload.is_banned else "UNBAN_USER",
            details=f"Foydalanuvchi {user.email} holati: is_banned={payload.is_banned}",
        )
    )
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/bots", response_model=list[BotOut])
async def list_all_bots(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Bot).options(selectinload(Bot.env_vars)).order_by(Bot.created_at.desc())
    )
    bots = result.scalars().all()
    return [
        BotOut(
            id=b.id,
            user_id=b.user_id,
            name=b.name,
            source_type=b.source_type,
            source_url=b.source_url,
            entrypoint=b.entrypoint,
            requirements_detected=b.requirements_detected,
            status=b.status,
            crash_count=b.crash_count,
            created_at=b.created_at,
            updated_at=b.updated_at,
            env_vars=[
                EnvVarOut(id=ev.id, key=ev.key, masked_value=mask_secret(ev.encrypted_value))
                for ev in b.env_vars
            ],
        )
        for b in bots
    ]


@router.post("/bots/{bot_id}/emergency-stop")
async def admin_emergency_stop(
    bot_id: str,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin emergency killswitch for malicious or attack bots."""
    result = await db.execute(select(Bot).where(Bot.id == bot_id))
    bot = result.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot topilmadi.")

    DockerService.stop_bot_container(bot.id)
    bot.status = "stopped"

    db.add(
        AuditLog(
            user_email=admin.email,
            action="EMERGENCY_STOP",
            details=f"Admin tomonidan bot majburiy to'xtatildi: {bot.name} (ID: {bot.id})",
        )
    )
    await db.commit()
    return {"message": f"Bot {bot.name} majburiy to'xtatildi."}


@router.get("/stats", response_model=SystemStatsOut)
async def get_system_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    users_result = await db.execute(select(User))
    users = users_result.scalars().all()

    bots_result = await db.execute(select(Bot))
    bots = bots_result.scalars().all()

    running_bots = sum(1 for b in bots if b.status == "running")
    stopped_bots = sum(1 for b in bots if b.status == "stopped")
    crashed_bots = sum(1 for b in bots if "crash" in b.status)

    free_users = sum(1 for u in users if u.plan == "free")
    paid_users = sum(1 for u in users if u.plan == "paid")

    return SystemStatsOut(
        total_users=len(users),
        total_bots=len(bots),
        running_bots=running_bots,
        stopped_bots=stopped_bots,
        crashed_bots=crashed_bots,
        total_cpu_allocated=round(running_bots * 0.25, 2),
        total_memory_allocated_mb=running_bots * 256,
        free_plan_users=free_users,
        paid_plan_users=paid_users,
    )
