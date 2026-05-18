from unittest.mock import AsyncMock, Mock

import numpy as np
import pytest

from app.services import screener_runtime as runtime_module
from app.services.screener_runtime import BaselineSQLScreenerRuntime


def make_result(*, rows=None):
    result = Mock()
    mappings = Mock()
    mappings.all.return_value = rows or []
    result.mappings.return_value = mappings
    return result


def make_history_rows() -> list[dict]:
    rows: list[dict] = []
    stock_specs = {
        "000001.SZ": {"open": 10.0, "high": 10.8, "low": 9.8, "close": 10.6},
        "000002.SZ": {"open": 9.0, "high": 9.5, "low": 8.8, "close": 9.1},
    }
    for ts_code, values in stock_specs.items():
        for day in range(1, 41):
            rows.append(
                {
                    "ts_code": ts_code,
                    "trade_date": f"202401{day:02d}",
                    "open": values["open"],
                    "high": values["high"],
                    "low": values["low"],
                    "close": values["close"],
                }
            )
    return rows


class TalibStub:
    @staticmethod
    def RSI(close, timeperiod):
        latest_close = float(close[-1])
        if latest_close > 10:
            value = 55.0 if timeperiod == 14 else 25.0
        else:
            value = 65.0 if timeperiod == 14 else 45.0
        return np.asarray([np.nan] * (len(close) - 1) + [value], dtype=float)

    @staticmethod
    def MACD(close, fastperiod, slowperiod, signalperiod):
        latest_close = float(close[-1])
        if latest_close > 10 and (fastperiod, slowperiod, signalperiod) == (12, 26, 9):
            macd_value, signal_value = 0.5, 0.3
        else:
            macd_value, signal_value = 0.1, 0.2
        macd = np.asarray([np.nan] * (len(close) - 1) + [macd_value], dtype=float)
        signal = np.asarray([np.nan] * (len(close) - 1) + [signal_value], dtype=float)
        hist = macd - signal
        return macd, signal, hist

    @staticmethod
    def BBANDS(close, timeperiod, nbdevup, nbdevdn, matype):
        latest_close = float(close[-1])
        if latest_close > 10:
            upper = 10.2 if timeperiod == 20 else 10.8
            lower = 9.8 if timeperiod == 20 else 9.9
        else:
            upper = 9.5 if timeperiod == 20 else 9.0
            lower = 8.8 if timeperiod == 20 else 8.5
        upper_arr = np.asarray([np.nan] * (len(close) - 1) + [upper], dtype=float)
        middle_arr = np.asarray([np.nan] * (len(close) - 1) + [latest_close], dtype=float)
        lower_arr = np.asarray([np.nan] * (len(close) - 1) + [lower], dtype=float)
        return upper_arr, middle_arr, lower_arr


@pytest.mark.asyncio
async def test_runtime_non_default_rsi_period_changes_match_result(monkeypatch):
    monkeypatch.setattr(runtime_module, "tl", TalibStub)

    current_rows = [
        {
            "ts_code": "000001.SZ",
            "code": "000001",
            "stock_name": "平安银行",
            "trade_date": "20240131",
            "close": 10.6,
            "pct_chg": 2.5,
            "vol": 5000,
            "amount": 300000000,
        }
    ]
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(rows=current_rows),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    runtime = BaselineSQLScreenerRuntime(db)

    default_definition = {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": 1,
        "scope": {},
        "root": {
            "type": "group",
            "op": "all",
            "children": [{"type": "predicate", "rule_key": "rsiMax", "params": {"value": 40}}],
        },
    }
    parameterized_definition = {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": 1,
        "scope": {},
        "root": {
            "type": "group",
            "op": "all",
            "children": [
                {
                    "type": "predicate",
                    "rule_key": "rsiMax",
                    "params": {"value": 40, "period": 5},
                }
            ],
        },
    }

    default_results = await runtime.run(
        definition=default_definition,
        trade_date="20240131",
        limit=20,
        reason_builder=lambda *_args: {"summary": "default", "evidence": []},
    )

    db.execute = AsyncMock(
        side_effect=[
            make_result(rows=current_rows),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    parameterized_results = await runtime.run(
        definition=parameterized_definition,
        trade_date="20240131",
        limit=20,
        reason_builder=lambda *_args: {"summary": "parameterized", "evidence": []},
    )

    assert default_results == []
    assert len(parameterized_results) == 1
    assert parameterized_results[0]["code"] == "000001"


@pytest.mark.asyncio
async def test_runtime_non_default_macd_and_boll_params_can_change_matches(monkeypatch):
    monkeypatch.setattr(runtime_module, "tl", TalibStub)

    current_rows = [
        {
            "ts_code": "000001.SZ",
            "code": "000001",
            "stock_name": "平安银行",
            "trade_date": "20240131",
            "close": 10.6,
            "pct_chg": 2.5,
            "vol": 5000,
            "amount": 300000000,
        }
    ]
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(rows=current_rows),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    runtime = BaselineSQLScreenerRuntime(db)

    default_definition = {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": 1,
        "scope": {},
        "root": {
            "type": "group",
            "op": "all",
            "children": [
                {"type": "predicate", "rule_key": "macdBullish", "params": {"value": True}},
                {
                    "type": "predicate",
                    "rule_key": "bollCloseAboveUpper",
                    "params": {"value": True},
                },
            ],
        },
    }
    parameterized_definition = {
        "kind": "saved_screener",
        "ast_version": 1,
        "registry_version": 1,
        "scope": {},
        "root": {
            "type": "group",
            "op": "all",
            "children": [
                {
                    "type": "predicate",
                    "rule_key": "macdBullish",
                    "params": {
                        "value": True,
                        "fast_period": 6,
                        "slow_period": 13,
                        "signal_period": 5,
                    },
                },
                {
                    "type": "predicate",
                    "rule_key": "bollCloseAboveUpper",
                    "params": {"value": True, "period": 10, "stddev": 2.0},
                },
            ],
        },
    }

    default_results = await runtime.run(
        definition=default_definition,
        trade_date="20240131",
        limit=20,
        reason_builder=lambda *_args: {"summary": "default", "evidence": []},
    )

    db.execute = AsyncMock(
        side_effect=[
            make_result(rows=current_rows),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    parameterized_results = await runtime.run(
        definition=parameterized_definition,
        trade_date="20240131",
        limit=20,
        reason_builder=lambda *_args: {"summary": "parameterized", "evidence": []},
    )

    assert len(default_results) == 1
    assert parameterized_results == []
