from datetime import date
from unittest.mock import AsyncMock, MagicMock, Mock

import pandas as pd
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.selection_service import SelectionService
from core.providers.market_data_provider import MarketDataProvider


def make_result(*, row=None, rows=None):
    result = Mock()
    result.fetchone.return_value = row
    result.fetchall.return_value = [Mock(_mapping=item) for item in (rows or [])]
    mappings = Mock()
    mappings.all.return_value = rows or []
    result.mappings.return_value = mappings
    return result


@pytest.fixture
def mock_provider():
    provider = MagicMock(spec=MarketDataProvider)
    provider.get_daily_bars = AsyncMock(return_value=pd.DataFrame())
    provider.get_stock_list = AsyncMock(return_value=pd.DataFrame())
    provider.get_technicals = AsyncMock(return_value=pd.DataFrame())
    provider.get_latest_trade_date = AsyncMock(return_value=date(2024, 3, 28))
    provider.health_check = AsyncMock(return_value={"status": "ok"})
    return provider


@pytest.fixture
def mock_db():
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def service(mock_db, mock_provider):
    return SelectionService(db=mock_db, provider=mock_provider)


class TestSelectionServiceProvider:
    async def test_run_selection_uses_provider_data(self, service, mock_provider):
        mock_provider.get_stock_list.return_value = pd.DataFrame(
            [{"code": "000001", "name": "平安银行"}]
        )
        mock_provider.get_daily_bars.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "code": "000001",
                    "stock_name": "平安银行",
                    "trade_date": date(2024, 3, 28),
                    "close": 10.5,
                    "pct_chg": 2.5,
                    "vol": 1000000,
                    "amount": 10500000,
                }
            ]
        )

        results = await service.run_selection({"priceMin": 10.0, "changeMin": 1.0}, None)

        assert len(results) == 1
        assert results[0]["code"] == "000001"
        assert results[0]["trade_date"] == "20240328"
        assert results[0]["reason_summary"] == "Close >= 10.0; Daily change >= 1.0"
        assert results[0]["evidence"][0]["matched"] is True
        assert results[0]["reason"]["summary"] == results[0]["reason_summary"]

    async def test_run_selection_applies_provider_indicator_filters(self, service, mock_provider):
        mock_provider.get_stock_list.return_value = pd.DataFrame(
            [
                {"code": "000001", "name": "平安银行"},
                {"code": "000002", "name": "万科A"},
            ]
        )
        mock_provider.get_daily_bars.return_value = pd.DataFrame(
            [
                {
                    "ts_code": "000001.SZ",
                    "code": "000001",
                    "stock_name": "平安银行",
                    "trade_date": date(2024, 3, 28),
                    "close": 10.5,
                    "pct_chg": 2.5,
                    "vol": 1000000,
                    "amount": 10500000,
                },
                {
                    "ts_code": "000002.SZ",
                    "code": "000002",
                    "stock_name": "万科A",
                    "trade_date": date(2024, 3, 28),
                    "close": 9.8,
                    "pct_chg": 1.5,
                    "vol": 900000,
                    "amount": 9800000,
                },
            ]
        )
        mock_provider.get_technicals.side_effect = [
            {
                "RSI14": pd.Series([25.0]),
                "MACD": pd.Series([0.5]),
                "MACD_SIGNAL": pd.Series([0.3]),
            },
            {
                "RSI14": pd.Series([35.0]),
                "MACD": pd.Series([0.2]),
                "MACD_SIGNAL": pd.Series([0.4]),
            },
        ]

        results = await service.run_selection({"rsiMax": 30, "macdBullish": True}, None)

        assert len(results) == 1
        assert results[0]["code"] == "000001"
        assert mock_provider.get_technicals.await_count == 2
        mock_provider.get_technicals.assert_any_await(
            code="000001",
            indicators=["RSI14", "RSI", "MACD", "MACD_SIGNAL"],
            start_date=date(2024, 3, 28),
            end_date=date(2024, 3, 28),
        )
        mock_provider.get_technicals.assert_any_await(
            code="000002",
            indicators=["RSI14", "RSI", "MACD", "MACD_SIGNAL"],
            start_date=date(2024, 3, 28),
            end_date=date(2024, 3, 28),
        )

    async def test_run_selection_falls_back_to_sql_when_provider_fails(
        self, mock_db, mock_provider
    ):
        mock_provider.get_stock_list.side_effect = RuntimeError("provider unavailable")
        mock_db.execute = AsyncMock(
            return_value=make_result(
                rows=[
                    {
                        "ts_code": "000001.SZ",
                        "code": "000001",
                        "stock_name": "平安银行",
                        "trade_date": "20240328",
                        "close": 10.6,
                        "pct_chg": 2.5,
                        "vol": 5000,
                        "amount": 300000000,
                    }
                ]
            )
        )
        service = SelectionService(db=mock_db, provider=mock_provider)
        service._resolve_trade_date = AsyncMock(return_value="20240328")

        results = await service.run_selection({"priceMin": 5}, None)

        assert len(results) == 1
        assert results[0]["code"] == "000001"
        assert results[0]["signal"] == "buy"
        assert results[0]["reason_summary"].startswith("Close >= 5.00")
