#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据爬取模块

统一的数据源访问接口
"""

from .base import (
    BaseCrawler,
    DataSource,
    Market,
    AdjustType,
    CrawlConfig,
    RateLimiter,
    ProxyPool,
    DataProvider,
    create_crawler,
)

from .eastmoney import (
    EastMoneyCrawler,
)

__all__ = [
    "BaseCrawler",
    "DataSource",
    "Market",
    "AdjustType",
    "CrawlConfig",
    "RateLimiter",
    "ProxyPool",
    "DataProvider",
    "create_crawler",
    "EastMoneyCrawler",
]
