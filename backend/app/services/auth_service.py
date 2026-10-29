import time
from datetime import datetime, timedelta
from typing import Optional
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Request, Response, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

# Argon2 Password Hasher
ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    salt_len=16,
)

# In-memory IP rate limiter: ip -> list of timestamps
ip_attempt_history: dict[str, list[float]] = {}


def check_auth_rate_limit(request: Request):
    """
    Enforces maximum 10 login/signup attempts per 10 minutes per IP address.
    """
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_seconds = settings.AUTH_RATE_LIMIT_WINDOW_SECONDS
    max_attempts = settings.AUTH_RATE_LIMIT_ATTEMPTS

    timestamps = ip_attempt_history.get(client_ip, [])
    # Keep only timestamps within window
    timestamps = [t for t in timestamps if now - t < window_seconds]

    if len(timestamps) >= max_attempts:
        retry_after = int(window_seconds - (now - timestamps[0]))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Kirish urinishlari ko'payib ketdi. Iltimos, {max(1, retry_after)} soniyadan keyin qayta urinib ko'ring.",
            headers={"Retry-After": str(max(1, retry_after))},
        )

    timestamps.append(now)
    ip_attempt_history[client_ip] = timestamps


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except Exception:
        return False


def create_jwt_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def set_auth_cookie(response: Response, token: str):
    """Sets JWT access token in an HttpOnly, Secure, SameSite=Lax cookie."""
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookie(response: Response):
    """Clears the auth cookie on logout."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts JWT from HttpOnly cookie (or Authorization Bearer header fallback),
    validates token, and returns the authenticated User.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        # Fallback to header if present
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tizimga kirilmagan yoki sessiya muddati tugagan.",
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yaroqsiz token.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Yaroqsiz yoki eskirgan token.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Foydalanuvchi topilmadi.")

    return user
