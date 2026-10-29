import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app.database import engine, Base, async_session_maker
from app.models.user import User
from app.services.crypto_service import hash_password
from app.services.reconciler import start_reconciler_loop, reconcile_all_bots
from app.routers import auth, bots


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Initial Docker reconciliation on startup
    await reconcile_all_bots()

    # 3. Spawn background reconciler loop (every 15s)
    reconciler_task = asyncio.create_task(start_reconciler_loop(interval_seconds=15))

    yield

    # 4. Graceful shutdown: cancel reconciler and dispose engine
    reconciler_task.cancel()
    await engine.dispose()


app = FastAPI(
    title="BotHost API",
    description="Python Telegram Bot Hosting Platform Engine (Stage 1)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["Health"])
async def health_check():
    """Liveness probe confirming API service status."""
    return {"status": "ok", "service": "bothost-api", "version": "1.0.0"}


# Mount Stage 1 Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(bots.router, prefix="/api/v1")
