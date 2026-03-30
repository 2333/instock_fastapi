from types import SimpleNamespace
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
async def test_run_backtest_returns_missing_required_params_error():
    service = BacktestService(db=Mock())

    result = await service.run_backtest({"stock_code": "000001"}, user_id=7)

    assert result["status"] == "failed"
    assert result["error"] == "missing_required_params"
    assert result["debug_user_id"] == 7


@pytest.mark.asyncio
async def test_run_backtest_includes_strategy_params_in_result_meta():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(row={"ts_code": "000001.SZ", "symbol": "000001", "name": "平安银行"}),
            make_result(
                rows=[
                    make_mapping_row(trade_date="20240102", close=10.0),
                    make_mapping_row(trade_date="20240103", close=12.0),
                ]
            ),
        ]
    )
    service = BacktestService(db=db)

    result = await service.run_backtest(
        {
            "stock_code": "000001",
            "start_date": "20240102",
            "end_date": "20240103",
            "initial_capital": 100000,
            "strategy": "ma_crossover",
            "strategy_params": {"fast_ma": 5, "slow_ma": 20},
        },
        user_id=None,
    )

    assert result["status"] == "completed"
    assert result["meta"]["strategy"] == "ma_crossover"
    assert result["meta"]["strategy_params"] == {"fast_ma": 5, "slow_ma": 20}
    assert result["summary"]["total_trades"] == 1
    assert len(result["equity_curve"]) == 2


@pytest.mark.asyncio
async def test_run_backtest_returns_minimal_report_structure():
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
            "strategy_params": {},
        },
        user_id=None,
    )

    assert result["status"] == "completed"
    assert set(result["summary"].keys()) == {
        "initial_capital",
        "final_capital",
        "total_return",
        "annual_return",
        "max_drawdown",
        "sharpe_ratio",
        "win_rate",
        "total_trades",
        "winning_trades",
        "profit_factor",
        "avg_win",
        "avg_loss",
    }
    assert set(result["equity_curve"][0].keys()) == {"date", "equity", "benchmark"}
    assert set(result["trades"][0].keys()) == {
        "id",
        "date",
        "type",
        "price",
        "quantity",
        "profit",
        "return_pct",
        "hold_days",
    }
    assert result["meta"]["code"] == "000001"
    assert result["meta"]["name"] == "平安银行"


@pytest.mark.asyncio
async def test_list_results_returns_recent_history_summary():
    query_result = Mock()
    row = MagicMock()
    row._mapping = {
        "id": 12,
        "name": "ma_crossover-000001",
        "created_at": "2024-01-03T10:00:00",
        "result_data": {
            "summary": {"total_return": 12.3, "max_drawdown": -4.5},
            "meta": {"strategy": "ma_crossover", "code": "000001"},
        },
    }
    query_result.fetchall.return_value = [row]
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)
    service = BacktestService(db=db)

    result = await service.list_results(user_id=7, limit=5)

    assert result == [
        {
            "backtest_id": "12",
            "name": "ma_crossover-000001",
            "created_at": "2024-01-03T10:00:00",
            "strategy": "ma_crossover",
            "code": "000001",
            "total_return": 12.3,
            "max_drawdown": -4.5,
        }
    ]


@pytest.mark.asyncio
async def test_get_result_returns_completed_payload_for_owner():
    query_result = Mock()
    row = MagicMock()
    row.__getitem__.side_effect = lambda idx: [12, 7, "demo", {"external_backtest_id": "bt_1"}][idx]
    row._mapping = {"id": 12, "user_id": 7, "name": "demo", "result_data": {"external_backtest_id": "bt_1"}}
    query_result.fetchone.return_value = row
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)
    service = BacktestService(db=db)

    result = await service.get_result("bt_1", user_id=7)

    assert result["status"] == "completed"
    assert result["backtest_id"] == "12"
    assert result["data"]["id"] == 12


@pytest.mark.asyncio
async def test_get_result_returns_not_found_when_missing():
    query_result = Mock()
    query_result.fetchone.return_value = None
    db = Mock()
    db.execute = AsyncMock(return_value=query_result)
    service = BacktestService(db=db)

    result = await service.get_result("bt_missing", user_id=7)

    assert result == {"backtest_id": "bt_missing", "status": "not_found"}
