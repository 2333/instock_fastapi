from types import SimpleNamespace

import pytest

from app.core.dependencies import get_current_user
from app.main import app
from app.models.stock_model import SelectionCondition
from tests.conftest import async_session_factory_test


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


@pytest.mark.asyncio
async def test_selection_run_supports_pattern_filter(client, current_user_override):
    response = await client.post("/api/v1/selection", json={"filters": {"pattern": "HAMMER"}})

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert len(payload["data"]) == 1

    item = payload["data"][0]
    assert item["code"] == "000001"
    assert item["reason_summary"] == "Pattern = HAMMER"
    assert item["evidence"][-1]["key"] == "pattern"
    assert item["evidence"][-1]["condition"] == "HAMMER"


@pytest.mark.asyncio
async def test_selection_today_summary_aggregates_saved_conditions(client, current_user_override):
    async with async_session_factory_test() as session:
        session.add_all(
            [
                SelectionCondition(
                    user_id=current_user_override.id,
                    name="Hammer 组合",
                    category="custom",
                    description="锤子线",
                    params={"pattern": "HAMMER"},
                    is_active=True,
                ),
                SelectionCondition(
                    user_id=current_user_override.id,
                    name="价格过滤",
                    category="custom",
                    description="价格和涨跌幅过滤",
                    params={"priceMin": 10, "changeMin": 1},
                    is_active=True,
                ),
                SelectionCondition(
                    user_id=current_user_override.id,
                    name="停用条件",
                    category="custom",
                    description="不应参与统计",
                    params={"priceMin": 999},
                    is_active=False,
                ),
            ]
        )
        await session.commit()

    response = await client.get("/api/v1/selection/today-summary")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["trade_date"] == "20240102"
    assert payload["total_conditions"] == 3
    assert payload["active_conditions"] == 2
    assert payload["total_hits"] == 2

    hammer = next(item for item in payload["items"] if item["name"] == "Hammer 组合")
    assert hammer["hit_count"] == 1
    assert hammer["pattern"] == "HAMMER"
    assert hammer["top_hits"][0]["code"] == "000001"
    assert hammer["top_hits"][0]["reason_summary"] == "Pattern = HAMMER"


@pytest.mark.asyncio
async def test_selection_today_summary_requires_authentication(client):
    response = await client.get("/api/v1/selection/today-summary")

    assert response.status_code == 401
    assert response.json()["detail"] == "无法验证凭据"
