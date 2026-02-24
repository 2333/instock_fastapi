#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心模块

提供股票分析的核心功能
"""

from .crawling import (
    BaseCrawler,
    DataSource,
    Market,
    AdjustType,
    CrawlConfig,
    EastMoneyCrawler,
    create_crawler,
)

from .storage import (
    TimescaleDB,
    RedisClient,
    get_timescaledb,
    get_redis,
)

from .kline import (
    KlineData,
    KlineProcessor,
    Trend,
    CandleType,
)

from .indicator import (
    IndicatorType,
    IndicatorConfig,
    IndicatorResult,
    IndicatorSet,
    IndicatorCalculator,
)

from .pattern import (
    PatternType,
    PatternSignal,
    PatternConfig,
    DetectedPattern,
    PatternRecognizer,
    recognize_patterns,
)

__all__ = [
    # Crawling
    "BaseCrawler",
    "DataSource",
    "Market",
    "AdjustType",
    "CrawlConfig",
    "EastMoneyCrawler",
    "create_crawler",
    # Storage
    "TimescaleDB",
    "RedisClient",
    "get_timescaledb",
    "get_redis",
    # Kline
    "KlineData",
    "KlineProcessor",
    "Trend",
    "CandleType",
    # Indicator
    "IndicatorType",
    "IndicatorConfig",
    "IndicatorResult",
    "IndicatorSet",
    "IndicatorCalculator",
    # Pattern
    "PatternType",
    "PatternSignal",
    "PatternConfig",
    "DetectedPattern",
    "PatternRecognizer",
    "recognize_patterns",
    # Strategy
    "TradeConfig",
    "Order",
    "Trade",
    "Position",
    "BacktestResult",
    "BacktestEngine",
]
