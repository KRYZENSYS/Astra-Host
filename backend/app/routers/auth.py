from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserSignup, UserLogin, UserOut
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_jwt_token,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user,
    check_auth_rate_limit,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=UserOut)
async def signup(
    payload: UserSignup,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Registers a new user account.
    - Rate limited to 10 attempts per 10 minutes per IP.
    - Argon2id password hashing.
    - Generic error messages: does not reveal if email is already registered.
    - Sets JWT in an HttpOnly, Secure, SameSite=Lax cookie.
    """
    check_auth_rate_limit(request)

    # Check if email is already taken
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        # Generic error message to prevent account enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ushbu ma'lumotlar bilan ro'yxatdan o'tib bo'lmadi. Boshqa elektron pochta kiriting yoki tizimga kiring.",
        )

    new_user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Issue JWT in HttpOnly cookie
    token = create_jwt_token(new_user.id, new_user.email)
    set_auth_cookie(response, token)

    return UserOut.model_validate(new_user)


@router.post("/login", response_model=UserOut)
async def login(
    payload: UserLogin,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Authenticates user and sets HttpOnly cookie.
    - Rate limited to 10 attempts per 10 minutes per IP.
    - Generic error message: 'Elektron pochta yoki parol noto'g'ri.'
    """
    check_auth_rate_limit(request)

    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        # Generic error message
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Elektron pochta yoki parol noto'g'ri.",
        )

    token = create_jwt_token(user.id, user.email)
    set_auth_cookie(response, token)

    return UserOut.model_validate(user)


@router.post("/logout")
async def logout(response: Response):
    """Clears the HttpOnly auth cookie."""
    clear_auth_cookie(response)
    return {"message": "Tizimdan muvaffaqiyatli chiqildi."}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns authenticated user profile."""
    return UserOut.model_validate(current_user)
