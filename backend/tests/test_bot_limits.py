import pytest
from app.config import settings
from app.routers.bots import check_bot_quota
from app.models.user import User
from fastapi import HTTPException


def test_free_plan_limits():
    free_user = User(id="u1", email="user@test.uz", plan="free", is_admin=False)

    # 0 bots -> allowed
    check_bot_quota(free_user, current_bot_count=0)

    # 1 bot -> quota exceeded on next creation attempt
    with pytest.raises(HTTPException) as exc_info:
        check_bot_quota(free_user, current_bot_count=settings.FREE_MAX_BOTS)

    assert exc_info.value.status_code == 400
    assert "Reja limiti tugadi" in exc_info.value.detail


def test_paid_plan_limits():
    paid_user = User(id="u2", email="vip@test.uz", plan="paid", is_admin=False)

    # 1 to 4 bots -> allowed
    for count in range(settings.PAID_MAX_BOTS):
        check_bot_quota(paid_user, current_bot_count=count)

    # 5 bots -> quota exceeded on next creation attempt
    with pytest.raises(HTTPException) as exc_info:
        check_bot_quota(paid_user, current_bot_count=settings.PAID_MAX_BOTS)

    assert exc_info.value.status_code == 400
    assert f"maksimal {settings.PAID_MAX_BOTS}" in exc_info.value.detail
