import pytest
from app.services.crypto_service import hash_password, verify_password, encrypt_secret, decrypt_secret, mask_secret


def test_argon2_password_hashing():
    password = "MySecureBotPassword2026!"
    hashed = hash_password(password)

    # Hash must be formatted with argon2id
    assert "$argon2id$" in hashed
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False


def test_fernet_secret_encryption():
    telegram_token = "7123456789:AAH1234567890abcdefghijklmnopqrstuvwxyz"
    encrypted = encrypt_secret(telegram_token)

    assert encrypted != telegram_token
    assert len(encrypted) > 40

    decrypted = decrypt_secret(encrypted)
    assert decrypted == telegram_token


def test_secret_masking():
    token = "7123456789:AAH1234567890abcdefghijklmnopqrstuvwxyz"
    masked = mask_secret(token)
    assert masked.startswith("••••")
    assert token[-4:] in masked
    assert token[:10] not in masked


@pytest.mark.asyncio
async def test_signup_and_login_flow(client):
    # 1. Sign up new user
    signup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "operator@bothost.uz", "password": "StrongPassword123!"},
    )
    assert signup_resp.status_code == 200
    signup_data = signup_resp.json()
    assert signup_data["email"] == "operator@bothost.uz"
    assert "bothost_access_token" in signup_resp.cookies

    # 2. Duplicate signup should return generic 400 without leaking details
    dup_resp = await client.post(
        "/api/v1/auth/signup",
        json={"email": "operator@bothost.uz", "password": "AnotherPassword456!"},
    )
    assert dup_resp.status_code == 400
    assert "ro'yxatdan o'tib bo'lmadi" in dup_resp.json()["detail"]

    # 3. Login with wrong password returns generic 401
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@bothost.uz", "password": "WrongPassword999!"},
    )
    assert bad_login.status_code == 401
    assert "Elektron pochta yoki parol noto'g'ri" in bad_login.json()["detail"]

    # 4. Login with correct password
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@bothost.uz", "password": "StrongPassword123!"},
    )
    assert login_resp.status_code == 200
    assert "bothost_access_token" in login_resp.cookies

    # 5. Get current user
    me_resp = await client.get("/api/v1/auth/me", cookies=login_resp.cookies)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "operator@bothost.uz"
