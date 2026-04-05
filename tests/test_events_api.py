from unittest.mock import AsyncMock, patch

from sqlalchemy import select

from app.core.dependencies import get_current_user_optional
from app.main import app
from app.models.stock_model import User
from app.models.user_event_model import UserEvent
from tests.conftest import async_session_factory_test


class TestEventsAPI:
    async def test_track_event_accepts_json_body_and_persists_anonymous_event(self, client):
        response = await client.post(
            "/api/v1/events/track",
            json={
                "event_type": "page_view",
                "event_data": {"page_section": "hero"},
                "page": "/dashboard",
                "referrer": "/login",
            },
            headers={"user-agent": "pytest-agent"},
        )

        assert response.status_code == 202
        assert response.json() == {"status": "ok"}

        async with async_session_factory_test() as session:
            result = await session.execute(select(UserEvent))
            event = result.scalar_one()

        assert event.user_id is None
        assert event.event_type == "page_view"
        assert event.event_data == {"page_section": "hero"}
        assert event.page == "/dashboard"
        assert event.referrer == "/login"
        assert event.user_agent == "pytest-agent"
        assert event.ip_hash

    async def test_track_event_uses_optional_authenticated_user_when_bearer_token_present(self, client):
        user = User(
            id=99,
            username="analytics-user",
            email="analytics@example.com",
            hashed_password="hashed",
            is_active=True,
        )

        app.dependency_overrides[get_current_user_optional] = lambda: user
        try:
            response = await client.post(
                "/api/v1/events/track",
                json={"event_type": "filter_run", "page": "/selection"},
            )
        finally:
            app.dependency_overrides.pop(get_current_user_optional, None)

        assert response.status_code == 202
        assert response.json() == {"status": "ok"}

        async with async_session_factory_test() as session:
            result = await session.execute(
                select(UserEvent).where(UserEvent.event_type == "filter_run")
            )
            event = result.scalar_one()

        assert event.user_id == 99
        assert event.page == "/selection"

    async def test_track_event_degrades_when_commit_fails(self, client):
        with patch(
            "app.api.routers.events_router.AsyncSession.commit",
            new=AsyncMock(side_effect=RuntimeError("db unavailable")),
        ):
            response = await client.post(
                "/api/v1/events/track",
                json={"event_type": "backtest_run", "page": "/backtest"},
            )

        assert response.status_code == 202
        assert response.json() == {"status": "degraded"}
