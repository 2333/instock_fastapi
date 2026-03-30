from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

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
