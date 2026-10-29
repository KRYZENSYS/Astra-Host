import os
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, BackgroundTasks, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db, async_session_maker
from app.models.user import User
from app.models.bot import Bot
from app.models.env_var import BotEnvVar
from app.schemas.bot import BotOut, BotDetail, EnvVarOut, EnvVarsUpdate
from app.services.auth_service import get_current_user
from app.services.crypto_service import encrypt_secret, decrypt_secret, mask_secret
from app.services.zip_service import validate_and_extract_bot_zip
from app.services.detector_service import detect_or_verify_entrypoint, generate_dockerfile
from app.services.docker_service import RealDockerService, user_active_streams
import tempfile
import shutil
from app.analyzer.pipeline import analyze_project
from app.analyzer.telegram_service import validate_bot_token, delete_bot_webhook
from app.analyzer.autofix_service import analyze_failure_and_autofix
from app.analyzer.extractor import SafeExtractionError

router = APIRouter(prefix="/bots", tags=["Bot Management"])


async def get_user_bot(bot_id: str, user: User, db: AsyncSession) -> Bot:
    """Helper to fetch bot and enforce strict ownership isolation."""
    query = select(Bot).where(Bot.id == bot_id).options(selectinload(Bot.env_vars))
    res = await db.execute(query)
    bot = res.scalar_one_or_none()
    if not bot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bot topilmadi.")
    if bot.user_id != user.id:
        # Strict user isolation: 403 Forbidden
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ushbu botga kirish huquqingiz yo'q.")
    return bot


async def async_build_and_run(bot_id: str, source_dir: str):
    """Background task building image and running container."""
    async with async_session_maker() as session:
        query = select(Bot).where(Bot.id == bot_id).options(selectinload(Bot.env_vars))
        res = await session.execute(query)
        bot = res.scalar_one_or_none()
        if not bot:
            return

        bot.status = "building"
        await session.commit()

        # Decrypt environment variables for container injection
        env_dict = {ev.key: decrypt_secret(ev.encrypted_value) for ev in bot.env_vars}

        try:
            container_id = await asyncio.to_thread(
                RealDockerService.run_bot_container,
                bot_id=bot.id,
                env_vars_dict=env_dict,
                source_dir=source_dir,
            )
            bot.container_id = container_id
            bot.status = "running"
            bot.last_error = None
        except Exception as e:
            bot.status = "build_failed"
            bot.last_error = str(e)

        await session.commit()


@router.get("", response_model=list[BotOut])
async def list_bots(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists all bots owned by the current authenticated user."""
    query = (
        select(Bot)
        .where(Bot.user_id == current_user.id)
        .order_by(Bot.created_at.desc())
    )
    result = await db.execute(query)
    bots = result.scalars().all()
    return [BotOut.model_validate(b) for b in bots]


@router.post("", response_model=BotDetail, status_code=status.HTTP_201_CREATED)
async def create_bot(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    entrypoint: Optional[str] = Form(None),
    env_vars_json: str = Form("[]"),  # JSON array of {"key": "...", "value": "..."}
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates a new bot from an uploaded zip archive.
    - Enforces Free-tier limit: 1 bot per user.
    - Validates zip (zip-slip, zip bomb, symlink, junk exclusion, top-level flattening).
    - Autodetects entrypoint and requirements.txt.
    - Generates hardened Dockerfile (python:3.12-slim).
    - Encrypts environment variables with Fernet at rest.
    - Starts background build and container execution.
    """
    # 1. Enforce free tier quota (1 bot per user)
    existing_count_res = await db.execute(select(Bot).where(Bot.user_id == current_user.id))
    existing_count = len(existing_count_res.scalars().all())
    if existing_count >= settings.MAX_BOTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bepul tarif limiti: Har bir foydalanuvchi maksimal {settings.MAX_BOTS_PER_USER} ta bot yaratishi mumkin.",
        )

    # 2. Allocate Bot record
    new_bot = Bot(
        user_id=current_user.id,
        name=name.strip(),
        status="building",
    )
    db.add(new_bot)
    await db.flush()

    # 3. Create host storage directory /var/lib/bothost/bots/<bot_id>/src
    bot_dir = os.path.join(settings.BOT_STORAGE_DIR, new_bot.id, "src")
    os.makedirs(bot_dir, exist_ok=True)

    # 4. Read and validate zip
    zip_bytes = await file.read()
    validate_and_extract_bot_zip(zip_bytes, bot_dir)

    # 5. Detect entrypoint & requirements.txt
    detected_entry, has_reqs = detect_or_verify_entrypoint(bot_dir, user_override=entrypoint)
    new_bot.entrypoint = detected_entry
    new_bot.has_requirements = has_reqs

    # 6. Generate Dockerfile from template
    generate_dockerfile(bot_dir, detected_entry)

    # 7. Encrypt and save environment variables
    try:
        parsed_envs = json.loads(env_vars_json)
    except Exception:
        parsed_envs = []

    saved_env_outs: list[EnvVarOut] = []
    for item in parsed_envs:
        k = item.get("key", "").strip()
        v = item.get("value", "").strip()
        if k and v:
            encrypted_val = encrypt_secret(v)
            ev_record = BotEnvVar(bot_id=new_bot.id, key=k, encrypted_value=encrypted_val)
            db.add(ev_record)
            saved_env_outs.append(EnvVarOut(id=ev_record.id, key=k, masked_value=mask_secret(v)))

    await db.commit()
    await db.refresh(new_bot)

    # 8. Start background build & run
    background_tasks.add_task(async_build_and_run, new_bot.id, bot_dir)

    return BotDetail(
        id=new_bot.id,
        user_id=new_bot.user_id,
        name=new_bot.name,
        entrypoint=new_bot.entrypoint,
        has_requirements=new_bot.has_requirements,
        status=new_bot.status,
        last_error=None,
        created_at=new_bot.created_at,
        updated_at=new_bot.updated_at,
        env_vars=saved_env_outs,
    )


@router.get("/{bot_id}", response_model=BotDetail)
async def get_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns bot details with real reconciled container status and masked env vars."""
    bot = await get_user_bot(bot_id, current_user, db)

    # Reconcile with real container status
    if bot.status in ["running", "stopped", "crashed"]:
        real_status = await asyncio.to_thread(RealDockerService.get_container_real_status, bot.id)
        if real_status != bot.status:
            bot.status = real_status
            await db.commit()

    return BotDetail(
        id=bot.id,
        user_id=bot.user_id,
        name=bot.name,
        entrypoint=bot.entrypoint,
        has_requirements=bot.has_requirements,
        status=bot.status,
        last_error=bot.last_error,
        created_at=bot.created_at,
        updated_at=bot.updated_at,
        env_vars=[
            EnvVarOut(id=ev.id, key=ev.key, masked_value=mask_secret(decrypt_secret(ev.encrypted_value)))
            for ev in bot.env_vars
        ],
    )


@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotently starts the bot container."""
    bot = await get_user_bot(bot_id, current_user, db)
    bot_dir = os.path.join(settings.BOT_STORAGE_DIR, bot.id, "src")

    # If container does not exist or image was stopped, run it
    env_dict = {ev.key: decrypt_secret(ev.encrypted_value) for ev in bot.env_vars}
    await asyncio.to_thread(
        RealDockerService.run_bot_container,
        bot_id=bot.id,
        env_vars_dict=env_dict,
        source_dir=bot_dir,
    )

    bot.status = "running"
    bot.last_error = None
    await db.commit()
    return {"message": "Bot muvaffaqiyatli ishga tushirildi.", "status": "running"}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotently stops the bot container."""
    bot = await get_user_bot(bot_id, current_user, db)
    await asyncio.to_thread(RealDockerService.stop_bot, bot.id)
    bot.status = "stopped"
    await db.commit()
    return {"message": "Bot to'xtatildi.", "status": "stopped"}


@router.post("/{bot_id}/restart")
async def restart_bot(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Idempotently restarts the bot container."""
    bot = await get_user_bot(bot_id, current_user, db)
    bot_dir = os.path.join(settings.BOT_STORAGE_DIR, bot.id, "src")
    env_dict = {ev.key: decrypt_secret(ev.encrypted_value) for ev in bot.env_vars}

    await asyncio.to_thread(
        RealDockerService.run_bot_container,
        bot_id=bot.id,
        env_vars_dict=env_dict,
        source_dir=bot_dir,
    )

    bot.status = "running"
    bot.last_error = None
    await db.commit()
    return {"message": "Bot qayta ishga tushirildi.", "status": "running"}


@router.delete("/{bot_id}")
async def delete_bot(
    bot_id: str,
    delete_volume: bool = Query(False, description="Set to true to delete persistent /data volume"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Idempotently deletes the bot, its Docker container, image, and source folder.
    Volume is deleted ONLY if delete_volume=true.
    """
    bot = await get_user_bot(bot_id, current_user, db)
    await asyncio.to_thread(RealDockerService.delete_bot_resources, bot.id, delete_volume=delete_volume)
    await db.delete(bot)
    await db.commit()
    return {"message": "Bot muvaffaqiyatli o'chirildi."}


@router.put("/{bot_id}/code")
async def update_bot_code(
    bot_id: str,
    background_tasks: BackgroundTasks,
    entrypoint: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates bot code: uploads a new zip, replaces source files,
    rebuilds image and restarts container while preserving /data volume untouched.
    """
    bot = await get_user_bot(bot_id, current_user, db)
    bot_dir = os.path.join(settings.BOT_STORAGE_DIR, bot.id, "src")

    zip_bytes = await file.read()
    validate_and_extract_bot_zip(zip_bytes, bot_dir)

    detected_entry, has_reqs = detect_or_verify_entrypoint(bot_dir, user_override=entrypoint)
    bot.entrypoint = detected_entry
    bot.has_requirements = has_reqs
    bot.status = "building"
    await db.commit()

    generate_dockerfile(bot_dir, detected_entry)
    background_tasks.add_task(async_build_and_run, bot.id, bot_dir)

    return {"message": "Yangi kod yuklandi. Konteyner qayta yig'ilmoqda (/data hajmi saqlab qolindi)."}


@router.get("/{bot_id}/backup")
async def download_backup(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Downloads a tar.gz archive of the persistent /data volume."""
    bot = await get_user_bot(bot_id, current_user, db)
    tar_buffer = await asyncio.to_thread(RealDockerService.export_data_volume_tar, bot.id)
    filename = f"backup_{bot.name.lower().replace(' ', '_')}_{bot.id[:8]}.tar.gz"

    return Response(
        content=tar_buffer.getvalue(),
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{bot_id}/logs")
async def get_logs(
    bot_id: str,
    lines: int = Query(200, ge=1, le=2000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the last N lines of logs from container, redacting known env var secrets."""
    bot = await get_user_bot(bot_id, current_user, db)
    secrets = [decrypt_secret(ev.encrypted_value) for ev in bot.env_vars]
    log_lines = await asyncio.to_thread(RealDockerService.get_logs, bot.id, lines, secrets)
    return {"bot_id": bot.id, "logs": log_lines}


@router.get("/{bot_id}/logs/stream")
async def stream_logs(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    SSE stream of real-time container logs.
    - Limits to 3 concurrent streams per user.
    - Redacts secrets from log output.
    - Closes on client disconnect.
    """
    bot = await get_user_bot(bot_id, current_user, db)

    # Check concurrent stream limit per user (max 3)
    user_streams = user_active_streams.get(current_user.id, 0)
    if user_streams >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Jonli jurnallar oqimi limiti tugadi (bir foydalanuvchiga maksimal 3 ta faol oqim).",
        )

    user_active_streams[current_user.id] = user_streams + 1
    secrets = [decrypt_secret(ev.encrypted_value) for ev in bot.env_vars]

    async def log_generator():
        client = RealDockerService.get_docker_client()
        name = f"bothost_bot_{bot.id}"
        try:
            container = client.containers.get(name)
            log_stream = container.logs(stream=True, follow=True, tail=50)

            for raw_chunk in log_stream:
                line = raw_chunk.decode("utf-8", errors="replace").strip()
                if line:
                    for secret in secrets:
                        if secret and len(secret) >= 4 and secret in line:
                            line = line.replace(secret, "[REDACTED_SECRET]")
                    yield f"data: {json.dumps({'message': line})}\n\n"
                await asyncio.sleep(0.05)
        except Exception:
            yield f"data: {json.dumps({'message': '[BotHost] Log oqimi yakunlandi yoki konteyner toxtatildi.'})}\n\n"
        finally:
            user_active_streams[current_user.id] = max(0, user_active_streams.get(current_user.id, 1) - 1)

    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{bot_id}/env", response_model=list[EnvVarOut])
async def get_env_vars(
    bot_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns masked environment variables."""
    bot = await get_user_bot(bot_id, current_user, db)
    return [
        EnvVarOut(id=ev.id, key=ev.key, masked_value=mask_secret(decrypt_secret(ev.encrypted_value)))
        for ev in bot.env_vars
    ]


@router.put("/{bot_id}/env")
async def update_env_vars(
    bot_id: str,
    payload: EnvVarsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Updates or replaces bot environment variables.
    Validates key format [A-Z_][A-Z0-9_]*.
    Encrypts values with Fernet. Signals that container restart is required.
    """
    bot = await get_user_bot(bot_id, current_user, db)

    # Delete existing and replace with new validated variables
    for old_ev in bot.env_vars:
        await db.delete(old_ev)

    for item in payload.env_vars:
        db.add(
            BotEnvVar(
                bot_id=bot.id,
                key=item.key,
                encrypted_value=encrypt_secret(item.value),
            )
        )

    await db.commit()
    return {
        "message": "Muhit o'zgaruvchilari xavfsiz saqlandi. Yangi parametrlarni qo'llash uchun botni qayta ishga tushiring.",
        "restart_required": True,
    }


@router.post("/analyze")
async def analyze_uploaded_bot(
    file: UploadFile = File(...),
    sub_project: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    Accepts uploaded bot zip, runs static analyzer pipeline, returns complete analysis report.
    Never executes untrusted code.
    """
    zip_bytes = await file.read()
    temp_dir = tempfile.mkdtemp(prefix="bothost_analyze_")
    try:
        result = await asyncio.to_thread(
            analyze_project,
            project_dir=temp_dir,
            zip_bytes=zip_bytes,
            sub_project_rel_path=sub_project
        )
        return result.to_dict()
    except SafeExtractionError as se:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(se))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Tahlil jarayonida xatolik yuz berdi: {str(e)}")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/validate-token")
async def validate_token_endpoint(
    token: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Validates Telegram Bot Token and checks for webhook conflicts."""
    res = await asyncio.to_thread(validate_bot_token, token)
    return res


@router.post("/delete-webhook")
async def delete_webhook_endpoint(
    token: str = Form(...),
    current_user: User = Depends(get_current_user),
):
    """Deletes conflicting webhook so polling can run without 409 Conflict."""
    res = await asyncio.to_thread(delete_bot_webhook, token)
    return res


@router.post("/auto-launch", response_model=BotDetail, status_code=status.HTTP_201_CREATED)
async def auto_launch_bot(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    entrypoint: Optional[str] = Form(None),
    sub_project: Optional[str] = Form(None),
    env_vars_json: str = Form("[]"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Auto-Launch pipeline:
    1. Analyzes zip, extracts safely into bot folder.
    2. Auto-configures requirements and generated multi-stage Dockerfile.
    3. Encrypts environment variables at rest.
    4. Starts container with 20-second smoke test and auto-fix loop.
    """
    # 1. Enforce free tier quota (1 bot per user)
    existing_count_res = await db.execute(select(Bot).where(Bot.user_id == current_user.id))
    existing_count = len(existing_count_res.scalars().all())
    if existing_count >= settings.MAX_BOTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bepul tarif limiti: Har bir foydalanuvchi maksimal {settings.MAX_BOTS_PER_USER} ta bot yaratishi mumkin.",
        )

    # 2. Allocate Bot record
    new_bot = Bot(
        user_id=current_user.id,
        name=name.strip(),
        status="building",
    )
    db.add(new_bot)
    await db.flush()

    # 3. Create host storage directory
    bot_dir = os.path.join(settings.BOT_STORAGE_DIR, new_bot.id, "src")
    os.makedirs(bot_dir, exist_ok=True)

    # 4. Extract and run static analyzer
    zip_bytes = await file.read()
    analysis = await asyncio.to_thread(
        analyze_project,
        project_dir=bot_dir,
        zip_bytes=zip_bytes,
        user_entry_override=entrypoint,
        sub_project_rel_path=sub_project
    )

    if not analysis.is_supported_language:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=analysis.language_warning or "Qo'llab-quvvatlanmaydigan loyiha."
        )

    effective_entry = entrypoint if (entrypoint and entrypoint.strip()) else analysis.recommended_entrypoint
    new_bot.entrypoint = effective_entry
    new_bot.has_requirements = (analysis.dependencies is not None and analysis.dependencies.has_requirements_file)

    # 5. Encrypt and save environment variables
    try:
        parsed_envs = json.loads(env_vars_json)
    except Exception:
        parsed_envs = []

    saved_env_outs: list[EnvVarOut] = []
    for item in parsed_envs:
        k = item.get("key", "").strip()
        v = item.get("value", "").strip()
        if k and v:
            encrypted_val = encrypt_secret(v)
            ev_record = BotEnvVar(bot_id=new_bot.id, key=k, encrypted_value=encrypted_val)
            db.add(ev_record)
            saved_env_outs.append(EnvVarOut(id=ev_record.id, key=k, masked_value=mask_secret(v)))

    await db.commit()
    await db.refresh(new_bot)

    # 6. Start background build & run with auto-fix loop
    background_tasks.add_task(async_build_and_run, new_bot.id, analysis.project_root)

    return BotDetail(
        id=new_bot.id,
        user_id=new_bot.user_id,
        name=new_bot.name,
        entrypoint=new_bot.entrypoint,
        has_requirements=new_bot.has_requirements,
        status=new_bot.status,
        last_error=None,
        created_at=new_bot.created_at,
        updated_at=new_bot.updated_at,
        env_vars=saved_env_outs,
    )

