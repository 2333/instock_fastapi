#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
市场数据提供者抽象接口

定义统一的数据访问接口，使核心引擎与具体存储解耦。
遵循 PRD 8.3 节：必须预留数据访问层抽象。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd


@dataclass
class DailyBar:
    """日线数据"""
    code: str
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: Optional[float] = None
    adj_factor: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "trade_date": self.trade_date.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "amount": self.amount,
            "adj_factor": self.adj_factor,
        }


@dataclass
class TechnicalIndicator:
    """技术指标"""
    code: str
    trade_date: date
    indicator_name: str
    indicator_value: Any  # 可能是 float, dict, or list

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "trade_date": self.trade_date.isoformat(),
            "indicator_name": self.indicator_name,
            "indicator_value": self.indicator_value,
        }


@dataclass
class Pattern:
    """K线形态"""
    code: str
    pattern_name: str
    pattern_date: date
    confidence: float  # 0-1
    direction: int  # 1=看涨, -1=看跌, 0=中性

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "pattern_name": self.pattern_name,
            "pattern_date": self.pattern_date.isoformat(),
            "confidence": self.confidence,
            "direction": self.direction,
        }


class MarketDataProviderError(Exception):
    """市场数据提供者异常基类"""
    pass


class MarketDataProvider(ABC):
    """
    市场数据提供者抽象接口

    所有数据源（PostgreSQL、DuckDB、Parquet、API）都必须实现此接口。
    核心引擎通过此接口访问数据，不关心底层存储细节。
    """

    @abstractmethod
    async def get_daily_bars(
        self,
        codes: List[str],
        start_date: date,
        end_date: date,
        adjusted: bool = True
    ) -> pd.DataFrame:
        """
        获取日线数据

        Args:
            codes: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否复权

        Returns:
            pandas DataFrame，列：code, trade_date, open, high, low, close, volume, amount
        """
        pass

    @abstractmethod
    async def get_technicals(
        self,
        code: str,
        indicators: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, pd.Series]:
        """
        获取技术指标

        Args:
            code: 股票代码
            indicators: 指标名称列表（如 ["macd", "rsi", "boll"]）
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            dict: {indicator_name: pd.Series(index=date, values)}
        """
        pass

    @abstractmethod
    async def get_patterns(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> List[Pattern]:
        """
        获取K线形态识别结果

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            List[Pattern] 形态列表
        """
        pass

    @abstractmethod
    async def get_fund_flow(
        self,
        codes: List[str],
        trade_date: date
    ) -> pd.DataFrame:
        """
        获取资金流向数据

        Args:
            codes: 股票代码列表
            trade_date: 交易日期

        Returns:
            DataFrame: code, main_net, hot_money, retail, total
        """
        pass

    @abstractmethod
    async def get_stock_list(
        self,
        markets: Optional[List[str]] = None,
        active_only: bool = True
    ) -> pd.DataFrame:
        """
        获取股票列表

        Args:
            markets: 市场筛选（["沪市", "深市", "创业板", "科创板"]）
            active_only: 只获取上市状态正常的股票

        Returns:
            DataFrame: code, name, market, industry, list_date, status
        """
        pass

    @abstractmethod
    async def get_latest_trade_date(
        self,
        reference_date: Optional[date] = None
    ) -> date:
        """
        获取最新交易日

        Args:
            reference_date: 参考日期（默认为今天）

        Returns:
            最新交易日日期
        """
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        数据源健康检查

        Returns:
            dict: {"status": "ok", "latency_ms": 123, "details": {...}}
        """
        pass
