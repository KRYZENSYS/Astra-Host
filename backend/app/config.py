import os
from pydantic_settings import BaseSettings
from cryptography.fernet import Fernet


class Settings(BaseSettings):
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    APP_NAME: str = "BotHost"
    APP_URL: str = os.getenv("APP_URL", "http://localhost")

    # Database: Supports Postgres 16 in Docker & SQLite dev fallback
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///./bothost_stage1.db"
    )

    # Cryptography: Fernet key for symmetric encryption of env vars
    # Key MUST be 32 url-safe base64-encoded bytes
    FERNET_SECRET_KEY: str = os.getenv(
        "FERNET_SECRET_KEY", Fernet.generate_key().decode()
    )

    # Auth & Cookies: JWT stored in HttpOnly, Secure, SameSite=Lax cookie
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-jwt-key-2026-bothost")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    COOKIE_NAME: str = "bothost_access_token"
    COOKIE_SECURE: bool = (os.getenv("ENVIRONMENT", "development") == "production")
    COOKIE_SAMESITE: str = "lax"

    # Rate Limiting: 10 attempts per 10 minutes per IP on auth
    AUTH_RATE_LIMIT_ATTEMPTS: int = 10
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 600  # 10 minutes

    # Limits & Storage
    MAX_BOTS_PER_USER: int = int(os.getenv("MAX_BOTS_PER_USER", "1"))
    BOT_STORAGE_DIR: str = os.getenv("BOT_STORAGE_DIR", "/var/lib/bothost/bots")
    DOCKER_SOCKET_PATH: str = os.getenv("DOCKER_SOCKET_PATH", "/var/run/docker.sock")

    # Zip Upload Safeguards
    MAX_ZIP_SIZE_BYTES: int = 20 * 1024 * 1024        # 20 MB max archive
    MAX_UNCOMPRESSED_BYTES: int = 100 * 1024 * 1024   # 100 MB max uncompressed (zip-bomb protection)
    MAX_ARCHIVE_FILES: int = 2000                     # Max files per bot

    class Config:
        case_sensitive = True


settings = Settings()
