from types import SimpleNamespace

import pytest

from app.core.dependencies import get_current_user
from app.main import app
from app.schemas.selection_schema import ScreeningScope, SelectionFilters
from app.services.strategy_service import StrategyService


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


def test_build_selection_strategy_params_preserves_screening_structure():
    params = StrategyService.build_selection_strategy_params(
        selection_filters=SelectionFilters(price_min=10, pattern="HAMMER"),
        selection_scope=ScreeningScope(market="sz", limit=100),
        entry_rules={"mode": "screening_match", "custom": True},
        exit_rules={"mode": "configurable", "rules": [{"name": "stop_loss_pct"}]},
    )

    assert params["source"] == "selection"
    assert params["template_name"] == "selection_bridge"
    assert params["selection_filters"] == {"priceMin": 10, "pattern": "HAMMER"}
    assert params["selection_scope"] == {"market": "sz", "limit": 100}
    assert params["entry_rules"]["custom"] is True
    assert params["exit_rules"]["rules"][0]["name"] == "stop_loss_pct"
    assert params["backtest_config"] == {}
    assert params["strategy_params"] == {}


def test_build_strategy_params_normalizes_manual_backtest_payload():
    params = StrategyService.build_strategy_params(
        {
            "strategy_type": "ma_crossover",
            "stock_code": "600519",
            "period": "2y",
            "initial_capital": 100000,
            "position_size": 10,
            "max_position": 50,
            "stop_loss": 5,
            "take_profit": 15,
            "min_hold_days": 1,
            "commission_rate": 0.03,
            "min_commission": 5,
            "slippage": 0.1,
            "strategy_params": {"fast_ma": 5, "slow_ma": 20},
        }
    )

    assert params["source"] == "backtest"
    assert params["template_name"] == "ma_crossover"
    assert params["backtest_config"]["strategy_type"] == "ma_crossover"
    assert params["backtest_config"]["stock_code"] == "600519"
    assert params["strategy_params"] == {"fast_ma": 5, "slow_ma": 20}
    assert params["entry_rules"]["mode"] == "template_signal"
    assert params["entry_rules"]["template_name"] == "ma_crossover"
    assert params["exit_rules"]["mode"] == "fixed_risk"
    assert params["exit_rules"]["stop_loss_pct"] == 5
    assert params["exit_rules"]["take_profit_pct"] == 15
    assert params["exit_rules"]["max_hold_days"] == 1
    assert "strategy_type" not in params
    assert "stock_code" not in params


@pytest.mark.asyncio
async def test_strategy_templates_expose_selection_bridge_metadata(client, current_user_override):
    response = await client.get("/api/v1/strategies/templates")

    assert response.status_code == 200
    templates = response.json()
    selection_template = next(item for item in templates if item["name"] == "selection_bridge")

    assert selection_template["source"] == "selection"
    assert "priceMin" in selection_template["selection_schema"]["filters"]["properties"]
    assert selection_template["entry_rules_template"]["mode"] == "screening_match"
    assert selection_template["exit_rules_template"]["rules"][0]["name"] == "take_profit_pct"


@pytest.mark.asyncio
async def test_strategy_create_route_normalizes_selection_payload(client, current_user_override):
    response = await client.post(
        "/api/v1/strategies/my",
        json={
            "name": "筛选策略-001",
            "description": "由筛选条件生成的策略",
            "params": {
                "source": "selection",
                "template_name": "selection_bridge",
                "selection_filters": {"priceMin": 10, "pattern": "HAMMER"},
                "selection_scope": {"market": "sz", "limit": 100},
                "entry_rules": {
                    "mode": "screening_match",
                    "filters": {"priceMin": 10, "pattern": "HAMMER"},
                    "scope": {"market": "sz", "limit": 100},
                },
                "exit_rules": {
                    "mode": "configurable",
                    "rules": [{"name": "take_profit_pct", "label": "止盈百分比"}],
                },
            },
            "is_active": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["params"]["source"] == "selection"
    assert payload["params"]["selection_filters"] == {"priceMin": 10, "pattern": "HAMMER"}
    assert payload["params"]["selection_scope"] == {"market": "sz", "limit": 100}
    assert payload["params"]["entry_rules"]["mode"] == "screening_match"
    assert payload["params"]["exit_rules"]["rules"][0]["name"] == "take_profit_pct"
    assert payload["params"]["backtest_config"] == {}
    assert payload["params"]["strategy_params"] == {}


@pytest.mark.asyncio
async def test_strategy_from_selection_endpoint_saves_structured_params(
    client, current_user_override
):
    response = await client.post(
        "/api/v1/strategies/my/from-selection",
        json={
            "name": "筛选策略-002",
            "description": "通过筛选条件保存",
            "params": {
                "selection_filters": {"changeMin": 1, "macdBullish": True},
                "selection_scope": {"market": "sh", "limit": 120},
                "entry_rules": {"mode": "screening_match"},
                "exit_rules": {"mode": "configurable", "rules": []},
            },
            "is_active": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["params"]["source"] == "selection"
    assert payload["params"]["selection_filters"] == {"changeMin": 1, "macdBullish": True}
    assert payload["params"]["selection_scope"] == {"market": "sh", "limit": 120}
    assert payload["params"]["entry_rules"]["mode"] == "screening_match"
    assert payload["params"]["backtest_config"] == {}
    assert payload["params"]["strategy_params"] == {}
