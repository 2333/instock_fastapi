from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from app.services.backtest_service import BacktestService


def make_result(*, rows=None, row=None):
    result = Mock()
    result.mappings.return_value.first.return_value = row
    result.mappings.return_value.all.return_value = rows or []
    return result


def make_mapping_row(**kwargs):
    return kwargs


@pytest.mark.asyncio
async def test_run_backtest_returns_structured_report_with_proxy_benchmark_and_risk():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(row={"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行"}),
            make_result(
                rows=[
                    make_mapping_row(trade_date="20240102", close=10.0),
                    make_mapping_row(trade_date="20240103", close=12.0),
                    make_mapping_row(trade_date="20240104", close=11.0),
                ]
            ),
        ]
    )
    service = BacktestService(db=db)

    result = await service.run_backtest(
        {
            "stock_code": "000001",
            "start_date": "20240102",
            "end_date": "20240104",
            "initial_capital": 100000,
            "strategy": "buy_hold",
        },
        user_id=None,
    )

    assert result["status"] == "completed"
    assert result["summary"]["total_trades"] == 1
    assert result["report"]["benchmark"]["source"] == "proxy"
    assert result["report"]["benchmark"]["name"] == "同标的买入持有"
    assert result["report"]["benchmark"]["series"][0]["value"] == 100000.0
    assert result["report"]["risk"]["risk_level"] == "low"
    assert result["report"]["risk"]["max_consecutive_loss_days"] >= 1
    assert result["report"]["performance"]["max_drawdown"] == result["summary"]["max_drawdown"]
    assert len(result["report"]["equity_curve"]) == 3
    assert len(result["report"]["trades"]) == 2


@pytest.mark.asyncio
async def test_list_results_exposes_structured_fields_when_saved_payload_contains_report():
    query_result = Mock()
    query_result.mappings.return_value.all.return_value = [
        {
            "id": 12,
            "name": "ma_crossover-000001",
            "start_date": "20240101",
            "end_date": "20240131",
            "initial_capital": 100000,
            "final_capital": 112300,
            "total_return": 12.3,
            "annual_return": 18.5,
            "max_drawdown": -4.5,
            "sharpe_ratio": 1.31,
            "win_rate": 100.0,
            "total_trades": 1,
            "created_at": "2024-01-03T10:00:00",
            "result_data": {
                "summary": {"total_return": 12.3, "max_drawdown": -4.5},
                "meta": {"strategy": "ma_crossover", "code": "000001", "name": "平安银行"},
                "report": {
                    "benchmark": {"name": "同标的买入持有", "source": "proxy"},
                    "risk": {"risk_level": "medium"},
                    "performance": {"total_return": 12.3},
                },
            },
        }
    ]
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)
    service = BacktestService(db=db)

    result = await service.list_results(user_id=7, limit=5)

    assert result[0]["benchmark_name"] == "同标的买入持有"
    assert result[0]["risk_level"] == "medium"
    assert result[0]["report"]["risk"]["risk_level"] == "medium"
    assert result[0]["total_return"] == 12.3


@pytest.mark.asyncio
async def test_get_result_builds_structured_report_for_legacy_payload():
    query_result = Mock()
    row = MagicMock()
    row.__getitem__.side_effect = lambda idx: [12, 7, "demo", {"summary": {"total_return": 12.3}, "meta": {"strategy": "ma_crossover", "code": "000001", "name": "平安银行"}, "equity_curve": [{"date": "20240102", "equity": 100000, "benchmark": 100000}], "trades": [{"id": 1, "date": "20240104", "type": "SELL", "price": 11.0, "quantity": 1000, "profit": 1000.0, "return_pct": 10.0, "hold_days": 2}]}][idx]
    row._mapping = {
        "id": 12,
        "user_id": 7,
        "name": "demo",
        "start_date": "20240101",
        "end_date": "20240131",
        "initial_capital": 100000,
        "final_capital": 112300,
        "result_data": {
            "summary": {
                "initial_capital": 100000,
                "final_capital": 112300,
                "total_return": 12.3,
                "annual_return": 18.5,
                "max_drawdown": -4.5,
                "sharpe_ratio": 1.31,
                "win_rate": 100.0,
                "total_trades": 1,
                "winning_trades": 1,
                "profit_factor": 1.2,
                "avg_win": 12300,
                "avg_loss": 0,
            },
            "meta": {"strategy": "ma_crossover", "code": "000001", "name": "平安银行"},
            "equity_curve": [{"date": "20240102", "equity": 100000, "benchmark": 100000}],
            "trades": [
                {
                    "id": 1,
                    "date": "20240104",
                    "type": "SELL",
                    "price": 11.0,
                    "quantity": 1000,
                    "profit": 1000.0,
                    "return_pct": 10.0,
                    "hold_days": 2,
                }
            ],
        },
    }
    query_result.fetchone.return_value = row
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)
    service = BacktestService(db=db)

    result = await service.get_result("bt_1", user_id=7)

    assert result["status"] == "completed"
    assert result["backtest_id"] == "12"
    assert result["summary"]["total_trades"] == 1
    assert result["report"]["benchmark"]["source"] == "proxy"
    assert result["report"]["risk"]["risk_level"] in {"low", "medium", "high"}
    assert result["data"]["result_data"]["report"]["benchmark"]["name"] == "同标的买入持有"
