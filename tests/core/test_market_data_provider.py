#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MarketDataProvider 接口测试（简化版）

重点测试 provider 的核心逻辑，使用简单 mock。
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from core.providers.market_data_provider import MarketDataProviderError
from core.providers.postgres_provider import PostgreSQLProvider


class MockResult:
    """模拟 SQLAlchemy Result"""
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def all(self):
        return self._rows

    def scalar_one_or_none(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._rows[0] if self._rows else None


@pytest.fixture
def mock_db():
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def provider(mock_db):
    return PostgreSQLProvider(mock_db)


class TestPostgreSQLProvider:
    """测试套件"""

    async def test_get_daily_bars_empty(self, provider, mock_db):
        mock_db.execute.return_value = MockResult([])
        result = await provider.get_daily_bars(
            codes=["000001"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    async def test_get_daily_bars_success(self, provider, mock_db):
        mock_stock = MagicMock(ts_code="000001.SZ", symbol="000001")
        mock_bar = MagicMock(
            ts_code="000001.SZ",
            trade_date="2024-01-02",
            trade_date_dt=date(2024, 1, 2),
            open=10.0,
            high=10.5,
            low=9.8,
            close=10.2,
            vol=1000000,
            amount=10200000,
        )
        mock_db.execute.side_effect = [
            MockResult([mock_stock]),
            MockResult([mock_bar])
        ]
        result = await provider.get_daily_bars(
            codes=["000001"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["code"] == "000001"
        assert result.iloc[0]["close"] == 10.2

    async def test_get_stock_list(self, provider, mock_db):
        mock_row = MagicMock()
        mock_row.ts_code = "000001.SZ"
        mock_row.symbol = "000001"
        mock_row.name = "平安银行"
        mock_row.market = "深市"
        mock_row.industry = "银行"
        mock_row.list_date = "1991-04-03"
        mock_row.list_status = "L"

        mock_db.execute.return_value = MockResult([mock_row])
        result = await provider.get_stock_list(markets=["深市"], active_only=True)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["code"] == "000001"
        assert result.iloc[0]["name"] == "平安银行"

    async def test_get_latest_trade_date(self, provider, mock_db):
        mock_db.execute.return_value = MockResult([date(2024, 3, 28)])
        result = await provider.get_latest_trade_date()
        assert result == date(2024, 3, 28)

    async def test_health_check_ok(self, provider, mock_db):
        mock_db.execute.return_value = MockResult([5000])
        result = await provider.health_check()
        assert result["status"] == "ok"
        assert "latency_ms" in result
        assert result["details"]["total_stocks"] == 5000

    async def test_health_check_error(self, provider, mock_db):
        mock_db.execute.side_effect = Exception("DB down")
        result = await provider.health_check()
        assert result["status"] == "error"
        assert "error" in result

    async def test_get_technicals_empty(self, provider, mock_db):
        mock_stock = MagicMock(ts_code="000001.SZ", symbol="000001")
        mock_db.execute.side_effect = [
            MockResult([mock_stock]),
            MockResult([])
        ]
        result = await provider.get_technicals(
            code="000001",
            indicators=["rsi"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        assert isinstance(result, dict)
        assert len(result) == 0

    async def test_get_patterns_empty(self, provider):
        result = await provider.get_patterns(
            code="000001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 10)
        )
        assert isinstance(result, list)
        assert len(result) == 0

    async def test_get_fund_flow_empty(self, provider, mock_db):
        mock_db.execute.return_value = MockResult([])
        result = await provider.get_fund_flow(
            codes=["000001"],
            trade_date=date(2024, 1, 2)
        )
        assert isinstance(result, pd.DataFrame)
        assert result.empty
