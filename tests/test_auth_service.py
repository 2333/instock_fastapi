from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from jose import JWTError

from app.services.auth_service import AuthService, pwd_context


@pytest.mark.asyncio
async def test_register_creates_user_with_hashed_password():
    result = Mock()
    result.scalar_one_or_none.return_value = None
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    db.add = Mock()

    user = await AuthService.register(db, "alice", "alice@example.com", "secret123")

    assert user.username == "alice"
    assert user.email == "alice@example.com"
    assert user.hashed_password != "secret123"
    assert pwd_context.verify("secret123", user.hashed_password)
    db.add.assert_called_once_with(user)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_register_rejects_duplicate_user():
    result = Mock()
    result.scalar_one_or_none.return_value = object()
    db = Mock()
    db.execute = AsyncMock(return_value=result)
    db.add = Mock()

    with pytest.raises(ValueError, match="用户名或邮箱已存在"):
        await AuthService.register(db, "alice", "alice@example.com", "secret123")

    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_authenticate_returns_user_for_valid_password():
    hashed_password = pwd_context.hash("secret123")
    expected_user = SimpleNamespace(username="alice", hashed_password=hashed_password)
    result = Mock()
    result.scalar_one_or_none.return_value = expected_user
    db = Mock()
    db.execute = AsyncMock(return_value=result)

    user = await AuthService.authenticate(db, "alice", "secret123")

    assert user is expected_user


@pytest.mark.asyncio
async def test_authenticate_returns_none_for_invalid_password():
    expected_user = SimpleNamespace(username="alice", hashed_password=pwd_context.hash("secret123"))
    result = Mock()
    result.scalar_one_or_none.return_value = expected_user
    db = Mock()
    db.execute = AsyncMock(return_value=result)

    user = await AuthService.authenticate(db, "alice", "wrong-password")

    assert user is None


def test_access_and_refresh_tokens_round_trip():
    access_token = AuthService.create_access_token(7)
    refresh_token = AuthService.create_refresh_token(7)

    assert AuthService.verify_access_token(access_token) == 7
    assert AuthService.verify_refresh_token(refresh_token) == 7


def test_verify_token_rejects_wrong_token_type():
    refresh_token = AuthService.create_refresh_token(7)

    with pytest.raises(JWTError, match="Token type mismatch"):
        AuthService.verify_access_token(refresh_token)
