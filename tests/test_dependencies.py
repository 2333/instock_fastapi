from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from jose import JWTError

from app.core.dependencies import get_admin_user, get_current_active_user, get_current_user


@pytest.mark.asyncio
async def test_get_current_user_returns_user_when_token_is_valid():
    db = Mock()
    db.get = AsyncMock(return_value=SimpleNamespace(id=7, is_active=True))

    with patch("app.core.dependencies.AuthService.verify_access_token", return_value=7):
        user = await get_current_user(token="valid-token", db=db)

    assert user.id == 7
    db.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_current_user_rejects_invalid_token():
    db = Mock()
    db.get = AsyncMock()

    with patch("app.core.dependencies.AuthService.verify_access_token", side_effect=JWTError()):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="bad-token", db=db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "无法验证凭据"


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user():
    db = Mock()
    db.get = AsyncMock(return_value=SimpleNamespace(id=7, is_active=False))

    with patch("app.core.dependencies.AuthService.verify_access_token", return_value=7):
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(token="valid-token", db=db)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_active_user_rejects_inactive_user():
    with pytest.raises(HTTPException) as exc_info:
        await get_current_active_user(SimpleNamespace(is_active=False))

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "用户未激活"


@pytest.mark.asyncio
async def test_get_admin_user_rejects_non_admin():
    with pytest.raises(HTTPException) as exc_info:
        await get_admin_user(SimpleNamespace(is_superuser=False))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "需要管理员权限"
