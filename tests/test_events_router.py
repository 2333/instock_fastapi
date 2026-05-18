from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.core.dependencies import get_current_user
from app.main import app
from app.models.stock_model import UserEvent
from app.services.event_service import EventService
from tests.conftest import async_session_factory_test


def _event_payload() -> dict:
    return {
        "event_type": "filter_run",
        "page": "  /selection  ",
        "referrer": "/",
        "event_data": {
            "filter_keys": ["market", "priceMin", "pattern"],
            "filter_count": 3,
            "market": "main_board",
            "result_count": 12,
            "trade_date": "20240102",
        },
    }


@pytest.fixture
def current_user_override():
    current_user = SimpleNamespace(
        id=7,
        username="alice",
        email="alice@example.com",
        is_active=True,
        is_superuser=False,
    )
    app.dependency_overrides[get_current_user] = lambda: current_user
    yield current_user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(autouse=True)
def reset_event_rate_limit_state():
    EventService.reset_rate_limit_state()
    yield
    EventService.reset_rate_limit_state()


@pytest.mark.asyncio
async def test_track_event_requires_authentication(client):
    response = await client.post("/api/v1/events/track", json=_event_payload())

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_track_event_persists_whitelisted_payload(client, current_user_override):
    response = await client.post("/api/v1/events/track", json=_event_payload())

    assert response.status_code == 202
    assert response.json() == {"accepted": True, "persisted": True}

    async with async_session_factory_test() as session:
        result = await session.execute(select(UserEvent).where(UserEvent.user_id == 7))
        event = result.scalar_one()

    assert event.event_type == "filter_run"
    assert event.page == "/selection"
    assert event.referrer == "/"
    assert event.event_version == 1
    assert event.event_data == {
        "filter_keys": ["market", "priceMin", "pattern"],
        "filter_count": 3,
        "market": "main_board",
        "result_count": 12,
        "trade_date": "20240102",
    }


@pytest.mark.asyncio
async def test_track_event_rejects_unknown_event_type(client, current_user_override):
    payload = _event_payload()
    payload["event_type"] = "search_run"

    response = await client.post("/api/v1/events/track", json=payload)

    assert response.status_code == 422
    assert "event_type" in response.text


@pytest.mark.asyncio
async def test_track_event_rejects_non_whitelisted_event_data_field(client, current_user_override):
    payload = _event_payload()
    payload["event_data"]["notes"] = "free text is not allowed"

    response = await client.post("/api/v1/events/track", json=payload)

    assert response.status_code == 422
    assert "notes" in response.text


@pytest.mark.asyncio
async def test_track_event_rejects_non_object_event_data_with_422(client, current_user_override):
    payload = _event_payload()
    payload["event_data"] = ["market", "pattern"]

    response = await client.post("/api/v1/events/track", json=payload)

    assert response.status_code == 422
    assert "event_data" in response.text
    assert "object" in response.text


@pytest.mark.asyncio
async def test_track_event_degrades_when_persistence_fails(client, current_user_override):
    with patch(
        "app.services.event_service.EventService._persist_event",
        new=AsyncMock(side_effect=RuntimeError("db write failed")),
    ):
        response = await client.post("/api/v1/events/track", json=_event_payload())

    assert response.status_code == 202
    assert response.json() == {"accepted": True, "persisted": False}


@pytest.mark.asyncio
async def test_track_event_enforces_server_side_rate_limit(client, current_user_override):
    for _ in range(100):
        response = await client.post("/api/v1/events/track", json=_event_payload())
        assert response.status_code == 202

    response = await client.post("/api/v1/events/track", json=_event_payload())

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many event requests"


@pytest.mark.asyncio
async def test_track_event_failed_attempts_still_count_toward_rate_limit(
    client, current_user_override
):
    with patch(
        "app.services.event_service.EventService._persist_event",
        new=AsyncMock(side_effect=RuntimeError("db write failed")),
    ):
        for _ in range(100):
            response = await client.post("/api/v1/events/track", json=_event_payload())
            assert response.status_code == 202
            assert response.json() == {"accepted": True, "persisted": False}

        response = await client.post("/api/v1/events/track", json=_event_payload())

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many event requests"


@pytest.mark.asyncio
async def test_track_event_keeps_first_wave_sequence_queryable(client, current_user_override):
    payloads = [
        {
            "event_type": "page_view",
            "page": "/selection",
            "referrer": "/",
            "event_data": {"route_name": "Selection"},
        },
        {
            "event_type": "dashboard_card_click",
            "page": "/",
            "referrer": "/selection",
            "event_data": {"card": "selection", "target_path": "/selection"},
        },
        _event_payload(),
        {
            "event_type": "backtest_run",
            "page": "/backtest",
            "referrer": "/selection",
            "event_data": {
                "strategy": "ma_crossover",
                "stock_code": "600519",
                "period": "2y",
                "start_date": "20240101",
                "end_date": "20240131",
                "param_keys": ["short", "long"],
            },
        },
        {
            "event_type": "pattern_view",
            "page": "/stock/600519",
            "referrer": "/selection",
            "event_data": {
                "stock_code": "600519",
                "pattern_name": "HAMMER",
                "pattern_type": "reversal",
                "confidence": 85,
                "trade_date": "20240102",
            },
        },
        {
            "event_type": "attention_action",
            "page": "/attention",
            "referrer": "/stock/600519",
            "event_data": {
                "action": "add",
                "stock_code": "600519",
                "source": "attention_page",
            },
        },
    ]

    for payload in payloads:
        response = await client.post("/api/v1/events/track", json=payload)
        assert response.status_code == 202
        assert response.json() == {"accepted": True, "persisted": True}

    async with async_session_factory_test() as session:
        result = await session.execute(
            select(UserEvent.event_type, UserEvent.page)
            .where(UserEvent.user_id == 7)
            .order_by(UserEvent.id)
        )
        rows = result.all()

    assert rows == [
        ("page_view", "/selection"),
        ("dashboard_card_click", "/"),
        ("filter_run", "/selection"),
        ("backtest_run", "/backtest"),
        ("pattern_view", "/stock/600519"),
        ("attention_action", "/attention"),
    ]
