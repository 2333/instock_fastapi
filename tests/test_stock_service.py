from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.services.stock_service import StockService
from core.crawling.base import AdjustType


def make_result(*, rows=None, row=None):
    result = Mock()
    result.fetchall.return_value = rows or []
    result.fetchone.return_value = row
    return result


def make_mapping_row(**kwargs):
    return SimpleNamespace(_mapping=kwargs)


@pytest.mark.asyncio
async def test_resolve_trade_date_handles_target_date_and_empty_result():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(row=("20240103",)),
            make_result(row=None),
        ]
    )
    service = StockService(db)

    resolved = await service._resolve_trade_date("20240105")
    latest = await service._resolve_trade_date(None)

    assert resolved == "20240103"
    assert latest is None


def test_normalize_date_and_parse_adjust():
    assert StockService._normalize_date("20240102") == "2024-01-02"
    assert StockService._normalize_date("2024/01/02") == "2024-01-02"
    assert StockService._normalize_date(None) is None

    assert StockService._parse_adjust("bfq") is AdjustType.NO_ADJUST
    assert StockService._parse_adjust("qfq") is AdjustType.FORWARD
    assert StockService._parse_adjust("hfq") is AdjustType.BACKWARD
    assert StockService._parse_adjust("unknown") is AdjustType.NO_ADJUST


@pytest.mark.asyncio
async def test_get_stocks_with_total_uses_resolved_date_and_returns_data():
    db = Mock()
    db.execute = AsyncMock(return_value=make_result(row=(2,)))
    service = StockService(db)
    service._resolve_trade_date = AsyncMock(return_value="20240102")
    service.get_stocks = AsyncMock(return_value=[{"code": "000001"}])

    rows, total = await service.get_stocks_with_total("20240105", 1, 20)

    assert rows == [{"code": "000001"}]
    assert total == 2
    service.get_stocks.assert_awaited_once_with("20240102", 1, 20)


@pytest.mark.asyncio
async def test_query_bars_from_db_returns_empty_without_range():
    service = StockService(Mock())

    bars = await service._query_bars_from_db("000001.SZ", None, "20240131")

    assert bars == []


@pytest.mark.asyncio
async def test_query_bars_from_db_normalizes_result_rows():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            rows=[make_mapping_row(ts_code="000001.SZ", trade_date="20240102", close=10.6)]
        )
    )
    service = StockService(db)

    bars = await service._query_bars_from_db("000001.SZ", "20240101", "20240131")

    assert bars == [{"ts_code": "000001.SZ", "trade_date": "20240102", "close": 10.6}]


@pytest.mark.asyncio
async def test_get_stock_detail_returns_not_found_payload():
    db = Mock()
    db.execute = AsyncMock(return_value=make_result(row=None))
    service = StockService(db)

    result = await service.get_stock_detail("000001", None, None)

    assert result == {"error": "Stock not found", "code": "000001"}


@pytest.mark.asyncio
async def test_get_stock_detail_uses_db_bars_for_bfq():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            row=make_mapping_row(ts_code="000001.SZ", symbol="000001", name="平安银行")
        )
    )
    service = StockService(db)
    service._query_bars_from_db = AsyncMock(return_value=[{"trade_date": "20240102"}])

    result = await service.get_stock_detail("000001", "20240101", "20240131", "bfq")

    assert result["adjust_requested"] == "bfq"
    assert result["adjust_applied"] == "bfq"
    assert result["bars"] == [{"trade_date": "20240102"}]


@pytest.mark.asyncio
async def test_get_stock_detail_falls_back_to_bfq_when_adjusted_bars_missing():
    db = Mock()
    db.execute = AsyncMock(
        return_value=make_result(
            row=make_mapping_row(ts_code="000001.SZ", symbol="000001", name="平安银行")
        )
    )
    service = StockService(db)
    service._fetch_adjusted_bars = AsyncMock(return_value=[])
    service._query_bars_from_db = AsyncMock(return_value=[{"trade_date": "20240102"}])

    result = await service.get_stock_detail("000001", "20240101", "20240131", "qfq")

    assert result["adjust_requested"] == "qfq"
    assert result["adjust_applied"] == "bfq"
    assert result["adjust_note"] == "requested_adjust_data_unavailable_fallback_to_bfq"
    assert result["bars"] == [{"trade_date": "20240102"}]


@pytest.mark.asyncio
async def test_get_etf_detail_and_stock_count():
    db = Mock()
    db.execute = AsyncMock(
        side_effect=[
            make_result(
                row=make_mapping_row(ts_code="510300.SH", symbol="510300", name="沪深300ETF")
            ),
            make_result(row=(18,)),
        ]
    )
    service = StockService(db)

    etf = await service.get_etf_detail("510300")
    count = await service.get_stock_count(is_etf=True)

    assert etf["symbol"] == "510300"
    assert count == 18


@pytest.mark.asyncio
async def test_fetch_adjusted_bars_uses_baostock_result_and_normalizes_dates():
    service = StockService(Mock())
    baostock_rows = [
        {
            "date": "2024-01-02",
            "open": 10.5,
            "high": 10.8,
            "low": 10.3,
            "close": 10.6,
            "pre_close": 10.4,
            "change": 0.2,
            "change_pct": 1.92,
            "volume": 5000,
            "amount": 52000,
        }
    ]

    with (
        patch("app.services.stock_service.BaoStockProvider") as baostock_cls,
        patch("app.services.stock_service.EastMoneyCrawler") as eastmoney_cls,
    ):
        baostock = baostock_cls.return_value
        baostock.fetch_kline = AsyncMock(return_value=baostock_rows)
        eastmoney = eastmoney_cls.return_value
        eastmoney.fetch = AsyncMock(return_value=[])
        eastmoney.close = AsyncMock()

        rows = await service._fetch_adjusted_bars(
            "000001", "20240101", "20240131", AdjustType.FORWARD
        )

    assert rows == [
        {
            "trade_date": "20240102",
            "open": 10.5,
            "high": 10.8,
            "low": 10.3,
            "close": 10.6,
            "pre_close": 10.4,
            "change": 0.2,
            "pct_chg": 1.92,
            "vol": 5000,
            "amount": 52000,
        }
    ]
    eastmoney.fetch.assert_not_awaited()
    eastmoney.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_adjusted_bars_falls_back_to_eastmoney_when_baostock_fails():
    service = StockService(Mock())

    with (
        patch("app.services.stock_service.BaoStockProvider") as baostock_cls,
        patch("app.services.stock_service.EastMoneyCrawler") as eastmoney_cls,
    ):
        baostock = baostock_cls.return_value
        baostock.fetch_kline = AsyncMock(side_effect=RuntimeError("boom"))
        eastmoney = eastmoney_cls.return_value
        eastmoney.fetch = AsyncMock(
            return_value=[
                {
                    "date": "2024-01-03",
                    "open": 11.0,
                    "high": 11.2,
                    "low": 10.8,
                    "close": 11.1,
                    "pre_close": 10.9,
                    "change": 0.2,
                    "change_pct": 1.83,
                    "volume": 7000,
                    "amount": 77000,
                }
            ]
        )
        eastmoney.close = AsyncMock()

        rows = await service._fetch_adjusted_bars(
            "000001", "20240101", "20240131", AdjustType.BACKWARD
        )

    assert rows[0]["trade_date"] == "20240103"
    eastmoney.fetch.assert_awaited_once()
    eastmoney.close.assert_awaited_once()
