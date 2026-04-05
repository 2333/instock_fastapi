from unittest.mock import AsyncMock, Mock

import pytest

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
async def test_selection_service_filters_by_rsi():
    """Test that RSI filtering works correctly."""
    db = Mock()
    # First row: RSI=25 (passes rsiMax=30), second row: RSI=35 (fails rsiMax=30)
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
                    "rsi": 25.0,
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
                    "rsi": 35.0,
                },
            ]
        )
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    results = await service.run_selection(
        {"rsiMax": 30},  # Only RSI <= 30
        None,
    )

    # Only first stock with RSI=25 should pass
    assert len(results) == 1
    assert results[0]["code"] == "000001"
    # Check evidence includes RSI
    rsi_evidence = next((e for e in results[0]["evidence"] if e["key"] == "rsi"), None)
    assert rsi_evidence is not None
    assert rsi_evidence["condition"] == 30
    assert rsi_evidence["matched"] is True


@pytest.mark.asyncio
async def test_selection_service_filters_by_macd_bullish():
    """Test that MACD bullish filter works correctly."""
    db = Mock()
    # macd > signal = bullish
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
                    "macd_signal": 0.4,  # macd < signal = bearish
                },
            ]
        )
    )
    service = SelectionService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")

    results = await service.run_selection(
        {"macdBullish": True},
        None,
    )

    # Only first stock with macd > signal should pass
    assert len(results) == 1
    assert results[0]["code"] == "000001"
    # Check summary mentions MACD bullish
    assert "MACD bullish" in results[0]["reason_summary"]
    # Check evidence includes MACD
    macd_evidence = next((e for e in results[0]["evidence"] if e["key"] == "macd"), None)
    assert macd_evidence is not None
    assert macd_evidence["matched"] is True
    assert results[0]["date"] == "20240102"


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
