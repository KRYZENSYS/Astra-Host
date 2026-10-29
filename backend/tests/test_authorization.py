import pytest
from app.models.user import User
from app.models.bot import Bot
from app.services.auth_service import create_jwt_token, hash_password


@pytest.mark.asyncio
async def test_user_bot_isolation(client, db_session):
    # 1. Create User A and User B
    user_a = User(email="usera@bothost.uz", password_hash=hash_password("Pass1234!"))
    user_b = User(email="userb@bothost.uz", password_hash=hash_password("Pass5678!"))
    db_session.add_all([user_a, user_b])
    await db_session.flush()

    # 2. Create Bot belonging to User A
    bot_a = Bot(user_id=user_a.id, name="User A Telegram Bot", status="stopped")
    db_session.add(bot_a)
    await db_session.commit()

    # 3. Authenticate as User B
    token_b = create_jwt_token(user_b.id, user_b.email)
    cookies_b = {"bothost_access_token": token_b}

    # 4. User B attempts to access User A's bot -> must return 403 Forbidden
    get_resp = await client.get(f"/api/v1/bots/{bot_a.id}", cookies=cookies_b)
    assert get_resp.status_code == 403
    assert "huquqingiz yo'q" in get_resp.json()["detail"]

    # 5. User B attempts to start User A's bot -> 403 Forbidden
    start_resp = await client.post(f"/api/v1/bots/{bot_a.id}/start", cookies=cookies_b)
    assert start_resp.status_code == 403

    # 6. User B attempts to delete User A's bot -> 403 Forbidden
    del_resp = await client.delete(f"/api/v1/bots/{bot_a.id}", cookies=cookies_b)
    assert del_resp.status_code == 403

    # 7. User B attempts to download backup of User A's bot -> 403 Forbidden
    backup_resp = await client.get(f"/api/v1/bots/{bot_a.id}/backup", cookies=cookies_b)
    assert backup_resp.status_code == 403
