from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.core.dependencies import get_current_user, get_db
from app.main import app


@pytest.mark.asyncio
async def test_register_endpoint_returns_created_user(client):
    user = SimpleNamespace(
        id=1,
        username="alice",
        email="alice@example.com",
        is_active=True,
        is_superuser=False,
    )

    with patch(
        "app.api.routers.auth_router.AuthService.register", new=AsyncMock(return_value=user)
    ):
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123"},
        )

    assert response.status_code == 201
    assert response.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_register_endpoint_returns_400_on_duplicate(client):
    with patch(
        "app.api.routers.auth_router.AuthService.register",
        new=AsyncMock(side_effect=ValueError("用户名或邮箱已存在")),
    ):
        response = await client.post(
            "/api/v1/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "secret123"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "用户名或邮箱已存在"


@pytest.mark.asyncio
async def test_login_endpoint_returns_tokens(client):
    user = SimpleNamespace(id=1)

    with (
        patch(
            "app.api.routers.auth_router.AuthService.authenticate",
            new=AsyncMock(return_value=user),
        ),
        patch(
            "app.api.routers.auth_router.AuthService.create_access_token",
            return_value="access-token",
        ),
        patch(
            "app.api.routers.auth_router.AuthService.create_refresh_token",
            return_value="refresh-token",
        ),
    ):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "secret123"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access-token",
        "refresh_token": "refresh-token",
        "token_type": "bearer",
    }


@pytest.mark.asyncio
async def test_login_endpoint_rejects_invalid_credentials(client):
    with patch(
        "app.api.routers.auth_router.AuthService.authenticate",
        new=AsyncMock(return_value=None),
    ):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "wrong"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "用户名或密码错误"


@pytest.mark.asyncio
async def test_refresh_endpoint_rejects_invalid_token(client):
    with patch(
        "app.api.routers.auth_router.AuthService.verify_refresh_token",
        side_effect=Exception("bad token"),
    ):
        response = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bad"})

    assert response.status_code == 401
    assert response.json()["detail"] == "无效的 refresh token"


@pytest.mark.asyncio
async def test_me_and_settings_endpoints_use_current_user_override(client):
    current_user = SimpleNamespace(
        id=7,
        username="alice",
        email="alice@example.com",
        is_active=True,
        is_superuser=False,
    )
    existing_settings = SimpleNamespace(
        id=1,
        user_id=7,
        language="zh-CN",
        theme="dark",
        timezone="Asia/Shanghai",
        extra={},
    )
    first_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    second_result = SimpleNamespace(scalar_one_or_none=lambda: existing_settings)

    async def refresh_settings(obj):
        if getattr(obj, "id", None) is None:
            obj.id = 1

    fake_db = SimpleNamespace(
        execute=AsyncMock(side_effect=[first_result, second_result]),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock(side_effect=refresh_settings),
    )

    async def override_auth_db():
        yield fake_db

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = override_auth_db

    try:
        me_response = await client.get("/api/v1/auth/me")
        settings_response = await client.get("/api/v1/auth/settings")
        update_response = await client.put(
            "/api/v1/auth/settings",
            json={"language": "en-US", "theme": "light", "extra": {"density": "compact"}},
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"

    assert settings_response.status_code == 200
    assert settings_response.json()["language"] == "zh-CN"

    assert update_response.status_code == 200
    assert update_response.json()["language"] == "en-US"
    assert update_response.json()["theme"] == "light"
