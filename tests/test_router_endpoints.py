from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.build_info import get_build_info
from app.core.dependencies import get_current_user
from app.database import get_db
from app.main import app


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
async def test_attention_endpoints(client, current_user_override):
    now = datetime.utcnow().isoformat()

    with (
        patch(
            "app.api.routers.attention_router.AttentionService.get_list",
            new=AsyncMock(
                return_value=[
                    {
                        "id": 1,
                        "code": "000001",
                        "stock_name": "平安银行",
                        "created_at": now,
                        "ts_code": "000001.SZ",
                    }
                ]
            ),
        ),
        patch(
            "app.api.routers.attention_router.AttentionService.add",
            new=AsyncMock(return_value={"status": "success", "code": "000001"}),
        ),
        patch(
            "app.api.routers.attention_router.AttentionService.remove",
            new=AsyncMock(return_value={"status": "success", "code": "000001"}),
        ),
    ):
        list_response = await client.get("/api/v1/attention")
        add_response = await client.post("/api/v1/attention", json={"code": "000001"})
        remove_response = await client.delete("/api/v1/attention/000001")

    assert list_response.status_code == 200
    assert list_response.json()[0]["code"] == "000001"
    assert add_response.json()["status"] == "success"
    assert remove_response.json()["status"] == "success"


@pytest.mark.asyncio
async def test_backtest_endpoints(client, current_user_override):
    with (
        patch(
            "app.api.routers.backtest_router.BacktestService.run_backtest",
            new=AsyncMock(return_value={"id": "bt-1", "status": "success"}),
        ),
        patch(
            "app.api.routers.backtest_router.BacktestService.get_result",
            new=AsyncMock(return_value={"id": "bt-1", "status": "done"}),
        ),
    ):
        run_response = await client.post(
            "/api/v1/backtest",
            json={"strategy": "enter", "start_date": "20240101", "end_date": "20240131"},
        )
        get_response = await client.get("/api/v1/backtest/bt-1")

    assert run_response.status_code == 200
    assert run_response.json()["id"] == "bt-1"
    assert get_response.json()["status"] == "done"


@pytest.mark.asyncio
async def test_etf_and_fund_flow_endpoints(client):
    with (
        patch(
            "app.api.routers.etf_router.StockService.get_etf_list",
            new=AsyncMock(return_value=[{"code": "510300", "name": "沪深300ETF"}]),
        ),
        patch(
            "app.api.routers.etf_router.StockService.get_etf_detail",
            new=AsyncMock(return_value={"code": "510300", "name": "沪深300ETF"}),
        ),
        patch(
            "app.api.routers.fund_flow_router.FundFlowService.get_fund_flow",
            new=AsyncMock(return_value=[{"code": "000001"}]),
        ),
        patch(
            "app.api.routers.fund_flow_router.FundFlowService.get_industry_fund_flow",
            new=AsyncMock(return_value=[{"sector": "银行"}]),
        ),
        patch(
            "app.api.routers.fund_flow_router.FundFlowService.get_concept_fund_flow",
            new=AsyncMock(return_value=[{"concept": "AI"}]),
        ),
    ):
        etf_list = await client.get("/api/v1/etf")
        etf_detail = await client.get("/api/v1/etf/510300")
        fund_flow = await client.get("/api/v1/fund-flow/000001")
        industry = await client.get("/api/v1/fund-flow/sector/industry")
        concept = await client.get("/api/v1/fund-flow/sector/concept")

    assert etf_list.status_code == 200
    assert etf_list.json()[0]["code"] == "510300"
    assert etf_detail.json()["name"] == "沪深300ETF"
    assert fund_flow.json()[0]["code"] == "000001"
    assert industry.json()[0]["sector"] == "银行"
    assert concept.json()[0]["concept"] == "AI"


@pytest.mark.asyncio
async def test_indicator_and_market_endpoints(client):
    with (
        patch(
            "app.api.routers.indicator_router.IndicatorService.get_indicators",
            new=AsyncMock(return_value=[{"code": "000001", "rsi_6": 56.7}]),
        ),
        patch(
            "app.api.routers.indicator_router.IndicatorService.get_latest_indicator",
            new=AsyncMock(return_value={"code": "000001", "rsi_6": 57.8}),
        ),
        patch(
            "app.api.routers.market_router.MarketDataService.get_fund_flow_rank",
            new=AsyncMock(return_value=[{"code": "000001"}]),
        ),
        patch(
            "app.api.routers.market_router.MarketDataService.get_block_trades",
            new=AsyncMock(return_value=[{"code": "000001"}]),
        ),
        patch(
            "app.api.routers.market_router.MarketDataService.get_lhb",
            new=AsyncMock(return_value=[{"code": "000001"}]),
        ),
        patch(
            "app.api.routers.market_router.MarketDataService.get_north_bound_funds",
            new=AsyncMock(return_value=[{"value": 123}]),
        ),
    ):
        indicators = await client.get("/api/v1/indicators", params={"code": "000001"})
        latest_indicator = await client.get("/api/v1/indicators/latest", params={"code": "000001"})
        market_fund = await client.get("/api/v1/market/fund-flow")
        block_trades = await client.get("/api/v1/market/block-trades")
        lhb = await client.get("/api/v1/market/lhb")
        north_bound = await client.get("/api/v1/market/north-bound")

    assert indicators.status_code == 200
    assert indicators.json()[0]["code"] == "000001"
    assert latest_indicator.json()["rsi_6"] == 57.8
    assert market_fund.json()[0]["code"] == "000001"
    assert block_trades.json()[0]["code"] == "000001"
    assert lhb.json()[0]["code"] == "000001"
    assert north_bound.json()[0]["value"] == 123


@pytest.mark.asyncio
async def test_pattern_endpoints_cover_latest_trade_date_branch(client):
    with (
        patch(
            "app.api.routers.pattern_router.PatternService.get_patterns",
            new=AsyncMock(return_value=[{"code": "000001", "pattern_name": "HAMMER"}]),
        ),
        patch(
            "app.api.routers.pattern_router.PatternService.get_latest_trade_date",
            new=AsyncMock(return_value="20240102"),
        ),
        patch(
            "app.api.routers.pattern_router.PatternService.get_composite_patterns",
            new=AsyncMock(return_value=[{"code": "000001", "pattern_name": "HAMMER"}]),
        ),
    ):
        patterns = await client.get("/api/v1/patterns", params={"code": "000001"})
        today = await client.get("/api/v1/patterns/today", params={"pattern_names": "HAMMER,DOJI"})

    assert patterns.status_code == 200
    assert patterns.json()[0]["pattern_name"] == "HAMMER"
    assert today.json()[0]["pattern_name"] == "HAMMER"


@pytest.mark.asyncio
async def test_health_and_info_include_build_metadata(client):
    build_info = get_build_info()

    health = await client.get("/health")
    info = await client.get("/api/v1/info")

    assert health.status_code == 200
    assert health.json()["version"] == build_info.version
    assert health.json()["git_sha"] == build_info.git_sha
    assert info.status_code == 200
    assert info.json()["version"] == build_info.version
    assert info.json()["git_sha"] == build_info.git_sha


@pytest.mark.asyncio
async def test_selection_endpoints_cover_crud_and_service_calls(client, current_user_override):
    condition = SimpleNamespace(
        id=1,
        user_id=7,
        name="低回撤",
        category="technical",
        description="desc",
        params={"rsi": 30},
        is_active=True,
    )
    list_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [condition]))
    missing_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    existing_result = SimpleNamespace(scalar_one_or_none=lambda: condition)

    async def refresh_condition(obj):
        if getattr(obj, "id", None) is None:
            obj.id = 1

    fake_db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[list_result, missing_result, existing_result, existing_result]
        ),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock(side_effect=refresh_condition),
        delete=AsyncMock(),
    )

    async def override_router_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_router_db

    try:
        with (
            patch(
                "app.api.routers.selection_router.SelectionService.get_conditions",
                return_value={
                    "markets": ["沪市", "深市", "创业板", "科创板"],
                    "indicators": ["macd", "kdj", "boll", "rsi"],
                    "strategies": ["放量上涨", "均线多头", "停机坪"],
                },
            ),
            patch(
                "app.api.routers.selection_router.SelectionService.run_selection",
                new=AsyncMock(
                    return_value=[
                        {
                            "ts_code": "000001.SZ",
                            "code": "000001",
                            "stock_name": "平安银行",
                            "trade_date": "20240102",
                            "date": "20240102",
                            "close": 10.6,
                            "change_rate": 2.5,
                            "amount": 300000000.0,
                            "score": 15.5,
                            "signal": "buy",
                            "reason_summary": "Change >= 1.50%; Market = sz",
                            "evidence": [
                                {
                                    "key": "change_rate",
                                    "label": "Daily change",
                                    "value": 2.5,
                                    "operator": ">=",
                                    "condition": 1.5,
                                    "matched": True,
                                },
                                {
                                    "key": "market",
                                    "label": "Market",
                                    "value": "sz",
                                    "operator": "=",
                                    "condition": "sz",
                                    "matched": True,
                                },
                            ],
                            "reason": {
                                "summary": "Change >= 1.50%; Market = sz",
                                "evidence": [
                                    {
                                        "key": "change_rate",
                                        "label": "Daily change",
                                        "value": 2.5,
                                        "operator": ">=",
                                        "condition": 1.5,
                                        "matched": True,
                                    },
                                    {
                                        "key": "market",
                                        "label": "Market",
                                        "value": "sz",
                                        "operator": "=",
                                        "condition": "sz",
                                        "matched": True,
                                    },
                                ],
                            },
                        }
                    ]
                ),
            ),
            patch(
                "app.api.routers.selection_router.SelectionService.get_history",
                new=AsyncMock(
                    return_value=[
                        {
                            "selection_id": "sel-1",
                            "ts_code": "000001.SZ",
                            "code": "000001",
                            "stock_name": "平安银行",
                            "trade_date": "20240102",
                            "date": "20240102",
                            "score": 15.5,
                            "signal": "hold",
                            "reason_summary": "Historical screening record sel-1",
                        }
                    ]
                ),
            ),
        ):
            conditions = await client.get("/api/v1/selection/conditions")
            screening_metadata = await client.get("/api/v1/screening/metadata")
            my_conditions = await client.get("/api/v1/selection/my-conditions")
            create_response = await client.post(
                "/api/v1/selection/my-conditions",
                json={"name": "低回撤", "category": "technical", "description": "desc"},
            )
            update_response = await client.put(
                "/api/v1/selection/my-conditions/1",
                json={"name": "低回撤2", "category": "technical", "description": "desc"},
            )
            delete_response = await client.delete("/api/v1/selection/my-conditions/1")
            run_response = await client.post(
                "/api/v1/selection", json={"conditions": {"changeMin": 1.5, "market": "sz"}}
            )
            screening_run_response = await client.post(
                "/api/v1/screening/run",
                json={"filters": {"changeMin": 1.5}, "scope": {"market": "sz", "limit": 50}},
            )
            history_response = await client.get("/api/v1/selection/history")
            screening_history_response = await client.get("/api/v1/screening/history")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert conditions.json()["markets"] == ["沪市", "深市", "创业板", "科创板"]
    assert screening_metadata.json()["data"]["filter_fields"][0]["key"] == "priceMin"
    assert my_conditions.json()[0]["name"] == "低回撤"
    assert create_response.status_code == 200
    assert update_response.json()["name"] == "低回撤2"
    assert delete_response.json()["status"] == "success"
    assert run_response.json()["success"] is True
    assert run_response.json()["data"][0]["code"] == "000001"
    assert run_response.json()["data"][0]["signal"] == "buy"
    assert run_response.json()["data"][0]["reason_summary"] == "Change >= 1.50%; Market = sz"
    assert screening_run_response.json()["success"] is True
    assert screening_run_response.json()["data"]["total"] == 1
    assert screening_run_response.json()["data"]["query"]["scope"]["limit"] == 50
    assert screening_run_response.json()["data"]["items"][0]["evidence"][0]["key"] == "change_rate"
    assert (
        screening_run_response.json()["data"]["items"][0]["reason"]["evidence"][1]["condition"]
        == "sz"
    )
    assert history_response.json()["success"] is True
    assert history_response.json()["data"][0]["code"] == "000001"
    assert history_response.json()["data"][0]["signal"] == "hold"
    assert history_response.json()["data"][0]["reason_summary"] == "Historical screening record sel-1"
    assert screening_history_response.json()["data"]["total"] == 1
    assert screening_history_response.json()["data"]["items"][0]["code"] == "000001"


@pytest.mark.asyncio
async def test_strategy_endpoints_cover_crud_and_service_calls(client, current_user_override):
    strategy = SimpleNamespace(
        id=1,
        user_id=7,
        name="enter",
        description="desc",
        params={"rsi": 30},
        is_active=True,
    )
    list_result = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [strategy]))
    missing_result = SimpleNamespace(scalar_one_or_none=lambda: None)
    existing_result = SimpleNamespace(scalar_one_or_none=lambda: strategy)

    async def refresh_strategy(obj):
        if getattr(obj, "id", None) is None:
            obj.id = 1

    fake_db = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[list_result, missing_result, existing_result, existing_result]
        ),
        add=Mock(),
        commit=AsyncMock(),
        refresh=AsyncMock(side_effect=refresh_strategy),
        delete=AsyncMock(),
    )

    async def override_router_db():
        yield fake_db

    app.dependency_overrides[get_db] = override_router_db

    try:
        with (
            patch(
                "app.api.routers.strategy_router.StrategyService.get_strategy_list",
                return_value=[{"name": "enter", "display_name": "放量上涨"}],
            ),
            patch(
                "app.api.routers.strategy_router.StrategyService.run_strategy",
                new=AsyncMock(return_value={"status": "success", "strategy": "enter"}),
            ),
            patch(
                "app.api.routers.strategy_router.StrategyService.get_results",
                new=AsyncMock(return_value=[{"id": 1, "strategy_name": "enter"}]),
            ),
        ):
            strategy_list = await client.get("/api/v1/strategies")
            my_strategies = await client.get("/api/v1/strategies/my")
            create_response = await client.post(
                "/api/v1/strategies/my",
                json={"name": "enter", "description": "desc"},
            )
            update_response = await client.put(
                "/api/v1/strategies/my/1",
                json={"name": "enter-2"},
            )
            delete_response = await client.delete("/api/v1/strategies/my/1")
            run_response = await client.post("/api/v1/strategies/run", json={"strategy": "enter"})
            results_response = await client.get(
                "/api/v1/strategies/results", params={"strategy": "enter"}
            )
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert strategy_list.json()[0]["name"] == "enter"
    assert my_strategies.json()[0]["name"] == "enter"
    assert create_response.status_code == 200
    assert update_response.json()["name"] == "enter-2"
    assert delete_response.json()["status"] == "success"
    assert run_response.json()["strategy"] == "enter"
    assert results_response.json()[0]["strategy_name"] == "enter"
