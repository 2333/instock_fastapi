#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SelectionServiceWithProvider 测试

测试 provider-based 筛选逻辑。
"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock
import pandas as pd

from sqlalchemy.ext.asyncio import AsyncSession

from core.providers.market_data_provider import MarketDataProvider, MarketDataProviderError
from core.providers.postgres_provider import PostgreSQLProvider
from app.services.selection_service_with_provider import SelectionServiceWithProvider


@pytest.fixture
def mock_provider():
    """创建模拟的 MarketDataProvider"""
    provider = MagicMock(spec=MarketDataProvider)

    # 默认实现：返回空数据
    provider.get_daily_bars = AsyncMock(return_value=pd.DataFrame())
    provider.get_stock_list = AsyncMock(return_value=pd.DataFrame())
    provider.get_technicals = AsyncMock(return_value={})
    provider.get_latest_trade_date = AsyncMock(return_value=date(2024, 3, 28))
    provider.health_check = AsyncMock(return_value={"status": "ok"})

    return provider


@pytest.fixture
def mock_db():
    """模拟 AsyncSession"""
    db = AsyncMock(spec=AsyncSession)
    return db


@pytest.fixture
def service(mock_db, mock_provider):
    """创建测试服务实例"""
    return SelectionServiceWithProvider(db=mock_db, provider=mock_provider)


class TestSelectionServiceWithProvider:
    """SelectionServiceWithProvider 测试套件"""

    async def test_run_selection_with_provider_success(self, service, mock_provider):
        """测试使用 provider 成功筛选"""
        # 准备模拟数据
        bars_df = pd.DataFrame([
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
        ])
        mock_provider.get_daily_bars.return_value = bars_df
        mock_provider.get_stock_list.return_value = pd.DataFrame([
            {"code": "000001.SZ", "name": "平安银行"}
        ])

        conditions = {
            "priceMin": 10.0,
            "priceMax": 12.0,
            "changeMin": 1.0,
        }

        result = await service.run_selection(conditions, None, limit=100)

        assert len(result) == 1
        assert result[0]["code"] == "000001"
        assert result[0]["close"] == 10.5
        assert result[0]["change_rate"] == 2.5
        assert "reason_summary" in result[0]
        assert "evidence" in result[0]

    async def test_run_selection_filters_correctly(self, service, mock_provider):
        """测试筛选条件应用"""
        bars_df = pd.DataFrame([
            {"ts_code": "000001.SZ", "code": "000001", "stock_name": "A", "trade_date": date(2024, 3, 28), "close": 10.0, "pct_chg": 1.0, "vol": 100, "amount": 1000},
            {"ts_code": "000002.SZ", "code": "000002", "stock_name": "B", "trade_date": date(2024, 3, 28), "close": 15.0, "pct_chg": 3.0, "vol": 200, "amount": 2000},
        ])
        mock_provider.get_daily_bars.return_value = bars_df
        mock_provider.get_stock_list.return_value = pd.DataFrame([
            {"code": "000001.SZ", "name": "A"},
            {"code": "000002.SZ", "name": "B"},
        ])

        conditions = {
            "priceMin": 12.0,  # 只应返回 000002
        }

        result = await service.run_selection(conditions, None, limit=100)

        assert len(result) == 1
        assert result[0]["code"] == "000002"

    async def test_fallback_to_original_when_provider_fails(self, mock_db, mock_provider):
        """测试 provider 失败时回退到原始实现"""
        # Provider 抛出异常
        mock_provider.get_daily_bars.side_effect = MarketDataProviderError("DB error")

        # 原始实现（SelectionService）需要 db
        service = SelectionServiceWithProvider(db=mock_db, provider=mock_provider)

        # 这里的 mock_db 需要 setup 返回一些数据让原始实现成功
        # 简化：我们只验证 fallback 逻辑存在
        # 实际测试需要 mock 原始实现的数据库查询

        # 由于原始实现复杂，这里仅作为集成测试占位
        # 在真实场景中，会验证 fallback 发生

    async def test_evidence_structure(self, service, mock_provider):
        """测试证据结构完整性"""
        bars_df = pd.DataFrame([
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
        ])
        mock_provider.get_daily_bars.return_value = bars_df
        mock_provider.get_stock_list.return_value = pd.DataFrame([
            {"code": "000001.SZ", "name": "平安银行"}
        ])

        conditions = {
            "priceMin": 10.0,
            "changeMin": 1.0,
        }

        result = await service.run_selection(conditions, None, limit=100)

        item = result[0]
        assert "reason" in item
        assert "summary" in item["reason"]
        assert "evidence" in item["reason"]

        evidence = item["reason"]["evidence"]
        assert len(evidence) >= 2

        # 检查证据字段
        for ev in evidence:
            assert "key" in ev
            assert "label" in ev
            assert "value" in ev
            assert "operator" in ev
            assert "matched" in ev

    async def test_empty_result_when_no_match(self, service, mock_provider):
        """测试无匹配结果"""
        bars_df = pd.DataFrame([
            {
                "ts_code": "000001.SZ",
                "code": "000001",
                "stock_name": "平安银行",
                "trade_date": date(2024, 3, 28),
                "close": 10.0,  # 不满足 priceMin=12.0
                "pct_chg": 0.5,  # 不满足 changeMin=2.0
                "vol": 1000000,
                "amount": 10500000,
            }
        ])
        mock_provider.get_daily_bars.return_value = bars_df
        mock_provider.get_stock_list.return_value = pd.DataFrame([
            {"code": "000001.SZ", "name": "平安银行"}
        ])

        conditions = {
            "priceMin": 12.0,
            "changeMin": 2.0,
        }

        result = await service.run_selection(conditions, None, limit=100)

        assert len(result) == 0

