from unittest.mock import AsyncMock, Mock

import pytest

from app.services import screener_runtime as runtime_module
from app.services.market_data_service import MarketDataService
from app.services.selection_service import SelectionService


def make_result(*, row=None, rows=None):
    result = Mock()
    result.fetchone.return_value = row
    mappings = Mock()
    mappings.all.return_value = rows or []
    result.mappings.return_value = mappings
    result.fetchall.return_value = [Mock(_mapping=item) for item in (rows or [])]
    return result


def make_history_rows() -> list[dict]:
    rows: list[dict] = []
    stock_specs = {
        "000001.SZ": {"open": 10.0, "high": 10.8, "low": 9.8, "close": 10.6},
        "000002.SZ": {"open": 9.0, "high": 9.5, "low": 8.8, "close": 9.1},
    }
    for ts_code, values in stock_specs.items():
        for day in range(1, 41):
            trade_date = f"202401{day:02d}" if day <= 31 else f"202402{day - 31:02d}"
            rows.append(
                {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
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
        value = 25.0 if latest_close > 10 and timeperiod == 5 else 55.0
        if latest_close <= 10:
            value = 45.0
        return runtime_module.np.asarray([runtime_module.np.nan] * (len(close) - 1) + [value])

    @staticmethod
    def MACD(close, fastperiod, slowperiod, signalperiod):
        latest_close = float(close[-1])
        if latest_close > 10 and (fastperiod, slowperiod, signalperiod) == (12, 26, 9):
            macd_value, signal_value = 0.5, 0.3
        else:
            macd_value, signal_value = 0.1, 0.2
        macd = runtime_module.np.asarray([runtime_module.np.nan] * (len(close) - 1) + [macd_value])
        signal = runtime_module.np.asarray(
            [runtime_module.np.nan] * (len(close) - 1) + [signal_value]
        )
        hist = macd - signal
        return macd, signal, hist

    @staticmethod
    def BBANDS(close, timeperiod, nbdevup, nbdevdn, matype):
        latest_close = float(close[-1])
        if latest_close > 10:
            upper = 10.2 if timeperiod == 20 else 10.8
            lower = 9.8 if timeperiod == 20 else 9.9
        else:
            upper = 9.5
            lower = 8.8
        upper_arr = runtime_module.np.asarray([runtime_module.np.nan] * (len(close) - 1) + [upper])
        middle_arr = runtime_module.np.asarray(
            [runtime_module.np.nan] * (len(close) - 1) + [latest_close]
        )
        lower_arr = runtime_module.np.asarray([runtime_module.np.nan] * (len(close) - 1) + [lower])
        return upper_arr, middle_arr, lower_arr


def make_bar_history(ts_code: str, closes: list[float]) -> list[dict[str, object]]:
    return [
        {
            "ts_code": ts_code,
            "trade_date": f"202401{index + 1:02d}",
            "trade_date_dt": None,
            "close": close,
            "high": close + 0.5,
            "low": close - 0.5,
        }
        for index, close in enumerate(closes)
    ]


@pytest.mark.asyncio
async def test_selection_service_get_conditions_returns_static_payload():
    payload = SelectionService.get_conditions()
    metadata = SelectionService.get_screening_metadata()

    assert "markets" in payload
    assert "indicators" in payload
    assert "strategies" in payload
    assert metadata["filter_fields"][0]["key"] == "priceMin"

    # Check new indicator filter fields exist
    field_keys = [f["key"] for f in metadata["filter_fields"]]
    assert "rsiMin" in field_keys
    assert "rsiMax" in field_keys
    assert "macdBullish" in field_keys
    assert "macdBearish" in field_keys
    assert metadata["registry_version"] == 1


@pytest.mark.asyncio
async def test_selection_service_returns_empty_when_db_or_trade_date_missing():
    service_without_db = SelectionService()
    assert await service_without_db.run_selection({}, None) == []
    assert await service_without_db.get_history(None, 10) == []

    db = Mock()
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value=None)
    assert await service.run_selection({}, None) == []


@pytest.mark.asyncio
async def test_selection_service_run_selection_scores_and_labels_rows():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                {
                    "ts_code": "000001.SZ",
                    "code": "000001",
                    "stock_name": "平安银行",
                    "trade_date": "20240102",
                    "close": 10.6,
                    "pct_chg": 2.5,
                    "vol": 5000,
                    "amount": 300000000,
                    "macd": 0.5,
                    "macd_signal": 0.3,
                },
                {
                    "ts_code": "000002.SZ",
                    "code": "000002",
                    "stock_name": "万科A",
                    "trade_date": "20240102",
                    "close": 9.1,
                    "pct_chg": -2.4,
                    "vol": 4000,
                    "amount": 100000000,
                    "macd": 0.2,
                    "macd_signal": 0.4,
                },
            ]
        )
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    results = await service.run_selection(
        {"priceMin": 5, "priceMax": 20, "changeMin": -5, "changeMax": 5, "market": "sz"},
        None,
    )

    assert results[0]["signal"] == "buy"
    assert results[1]["signal"] == "sell"


@pytest.mark.asyncio
async def test_selection_service_filters_by_rsi(monkeypatch):
    monkeypatch.setattr(runtime_module, "tl", TalibStub)
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240102",
                        "close": 10.6,
                        "pct_chg": 2.5,
                        "vol": 5000,
                        "amount": 300000000,
                        "macd": 0.5,
                        "macd_signal": 0.3,
                    },
                    {
                        "ts_code": "000002.SZ",
                        "code": "000002",
                        "stock_name": "万科A",
                        "trade_date": "20240102",
                        "close": 9.1,
                        "pct_chg": -2.4,
                        "vol": 4000,
                        "amount": 100000000,
                        "macd": 0.2,
                        "macd_signal": 0.4,
                    },
                ]
            ),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    results = await service.run_selection(
        None,
        None,
        definition={
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
                        "params": {"value": 30, "period": 5},
                    }
                ],
            },
        },
    )

    assert len(results) == 1
    assert results[0]["code"] == "000001"
    rsi_evidence = next((e for e in results[0]["evidence"] if e["key"] == "rsi"), None)
    assert rsi_evidence is not None
    assert rsi_evidence["condition"] == 30
    assert rsi_evidence["matched"] is True


@pytest.mark.asyncio
async def test_selection_service_filters_by_macd_bullish(monkeypatch):
    monkeypatch.setattr(runtime_module, "tl", TalibStub)
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240102",
                        "close": 10.6,
                        "pct_chg": 2.5,
                        "vol": 5000,
                        "amount": 300000000,
                        "macd": 0.5,
                        "macd_signal": 0.3,
                    },
                    {
                        "ts_code": "000002.SZ",
                        "code": "000002",
                        "stock_name": "万科A",
                        "trade_date": "20240102",
                        "close": 9.1,
                        "pct_chg": -2.4,
                        "vol": 4000,
                        "amount": 100000000,
                        "macd": 0.2,
                        "macd_signal": 0.4,
                    },
                ]
            ),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    results = await service.run_selection(
        None,
        None,
        definition={
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
                        "params": {"value": True},
                    }
                ],
            },
        },
    )

    assert len(results) == 1
    assert results[0]["code"] == "000001"
    assert "MACD" in results[0]["reason_summary"]
    macd_evidence = next((e for e in results[0]["evidence"] if e["key"] == "macd"), None)
    assert macd_evidence is not None
    assert macd_evidence["matched"] is True
    assert results[0]["date"] == "20240102"


@pytest.mark.asyncio
async def test_selection_service_non_default_boll_params_change_results(monkeypatch):
    monkeypatch.setattr(runtime_module, "tl", TalibStub)
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240102",
                        "close": 10.6,
                        "pct_chg": 2.5,
                        "vol": 5000,
                        "amount": 300000000,
                    }
                ]
            ),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    default_results = await service.run_selection(
        None,
        None,
        definition={
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
                        "rule_key": "bollCloseAboveUpper",
                        "params": {"value": True},
                    }
                ],
            },
        },
    )

    db.execute = AsyncMock(
        side_effect=[
            make_result(
                rows=[
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240102",
                        "close": 10.6,
                        "pct_chg": 2.5,
                        "vol": 5000,
                        "amount": 300000000,
                    }
                ]
            ),
            make_result(rows=make_history_rows()),
            make_result(rows=[]),
        ]
    )
    parameterized_results = await service.run_selection(
        None,
        None,
        definition={
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
                        "rule_key": "bollCloseAboveUpper",
                        "params": {"value": True, "period": 10, "stddev": 2.0},
                    }
                ],
            },
        },
    )

    assert len(default_results) == 1
    assert parameterized_results == []


@pytest.mark.asyncio
async def test_selection_service_get_history_formats_rows():

    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[
                {
                    "selection_id": "sel-1",
                    "ts_code": "000001.SZ",
                    "code": "000001",
                    "stock_name": "平安银行",
                    "trade_date": "20240102",
                    "score": 12.34,
                }
            ]
        )
    )
    service = SelectionService(db)

    rows = await service.get_history("20240102", 20)

    assert rows == [
        {
            "selection_id": "sel-1",
            "ts_code": "000001.SZ",
            "code": "000001",
            "stock_name": "平安银行",
            "trade_date": "20240102",
            "date": "20240102",
            "score": 12.34,
            "signal": "hold",
            "reason_summary": "Historical screening record sel-1",
        }
    ]


@pytest.mark.asyncio
async def test_market_data_service_returns_empty_when_trade_date_unavailable():
    service = MarketDataService(Mock())
    service._resolve_trade_date = AsyncMock(return_value=None)

    assert await service.get_fund_flow_rank(None) == []
    assert await service.get_block_trades(None) == []
    assert await service.get_lhb(None) == []
    assert await service.get_north_bound_funds(None) == []


@pytest.mark.asyncio
async def test_market_data_service_returns_rows_for_all_rankings():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(rows=[{"code": "000001"}]),
            make_result(rows=[{"code": "000002"}]),
            make_result(rows=[{"code": "000003"}]),
            make_result(rows=[{"code": "000004"}]),
        ]
    )
    service = MarketDataService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    fund_flow = await service.get_fund_flow_rank(None, 10)
    block_trades = await service.get_block_trades(None, 10)
    lhb = await service.get_lhb(None, 10)
    north_bound = await service.get_north_bound_funds(None, 10)

    assert fund_flow == [{"code": "000001"}]
    assert block_trades == [{"code": "000002"}]
    assert lhb == [{"code": "000003"}]
    assert north_bound == [{"code": "000004"}]


@pytest.mark.asyncio
async def test_market_data_service_resolves_trade_date_from_target_table():
    db = Mock()
    db.execute = AsyncMock(return_value=make_result(row=("20240102",)))
    service = MarketDataService(db)

    resolved = await service._resolve_trade_date(None, "stock_tops")

    assert resolved == "20240102"
    query = db.execute.await_args.args[0]
    assert "FROM stock_tops" in str(query)


@pytest.mark.asyncio
async def test_market_data_service_rejects_unsupported_trade_date_table():
    service = MarketDataService(Mock())

    with pytest.raises(ValueError):
        await service._resolve_trade_date(None, "invalid_table")
