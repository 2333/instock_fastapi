#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
存储模块

提供数据持久化接口
"""

from .timescaledb import (
    TimescaleDB,
    get_timescaledb,
    close_timescaledb,
)

from .redis import (
    RedisClient,
    get_redis,
    close_redis,
)

__all__ = [
    "TimescaleDB",
    "get_timescaledb",
    "close_timescaledb",
    "RedisClient",
    "get_redis",
    "close_redis",
]
