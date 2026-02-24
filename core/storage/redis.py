#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 存储层

提供实时数据缓存
"""

import json
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from app.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis 客户端"""

    def __init__(self):
        self.settings = get_settings()
        self.pool: Optional[ConnectionPool] = None
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """建立连接"""
        if self.client is None:
            self.pool = ConnectionPool.from_url(
                self.settings.REDIS_URL,
                max_connections=20,
                decode_responses=True,
            )
            self.client = redis.Redis(connection_pool=self.pool)

    async def close(self):
        """关闭连接"""
        if self.client:
            await self.client.close()
            self.pool.disconnect()
            self.client = None

    async def get(self, key: str) -> Optional[Any]:
        """获取值"""
        if self.client is None:
            await self.connect()
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
    ):
        """设置值"""
        if self.client is None:
            await self.connect()
        await self.client.set(key, value, ex=ex, px=px)

    async def delete(self, *keys: str):
        """删除键"""
        if self.client is None:
            await self.connect()
        await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if self.client is None:
            await self.connect()
        return await self.client.exists(key) > 0

    async def expire(self, key: str, seconds: int):
        """设置过期时间"""
        if self.client is None:
            await self.connect()
        await self.client.expire(key, seconds)

    async def incr(self, key: str) -> int:
        """递增"""
        if self.client is None:
            await self.connect()
        return await self.client.incr(key)

    # ==================== JSON 操作 ====================

    async def get_json(self, key: str) -> Optional[Any]:
        """获取JSON值"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return None

    async def set_json(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
    ):
        """设置JSON值"""
        await self.set(key, json.dumps(value, default=str), ex=ex)

    # ==================== Hash 操作 ====================

    async def hget(self, name: str, key: str) -> Optional[Any]:
        """获取Hash字段"""
        if self.client is None:
            await self.connect()
        return await self.client.hget(name, key)

    async def hset(self, name: str, key: str, value: Any):
        """设置Hash字段"""
        if self.client is None:
            await self.connect()
        await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> Dict[str, Any]:
        """获取整个Hash"""
        if self.client is None:
            await self.connect()
        return await self.client.hgetall(name)

    async def hdel(self, name: str, *keys: str):
        """删除Hash字段"""
        if self.client is None:
            await self.connect()
        await self.client.hdel(name, *keys)

    # ==================== 列表操作 ====================

    async def lpush(self, name: str, *values: Any):
        """从左侧插入"""
        if self.client is None:
            await self.connect()
        await self.client.lpush(name, *values)

    async def rpush(self, name: str, *values: Any):
        """从右侧插入"""
        if self.client is None:
            await self.connect()
        await self.client.rpush(name, *values)

    async def lrange(self, name: str, start: int = 0, end: int = -1) -> List[str]:
        """获取列表范围"""
        if self.client is None:
            await self.connect()
        return await self.client.lrange(name, start, end)

    # ==================== 股票专用方法 ====================

    async def cache_stock_spot(self, code: str, data: Any, ttl: int = 60):
        """缓存股票实时行情（60秒过期）"""
        key = f"stock:spot:{code}"
        await self.set_json(key, data, ex=ttl)

    async def get_cached_stock_spot(self, code: str) -> Optional[Any]:
        """获取缓存的股票行情"""
        key = f"stock:spot:{code}"
        return await self.get_json(key)

    async def cache_stock_list(self, market: str, data: Any, ttl: int = 300):
        """缓存股票列表（5分钟过期）"""
        key = f"stock:list:{market}"
        await self.set_json(key, data, ex=ttl)

    async def get_cached_stock_list(self, market: str) -> Optional[Any]:
        """获取缓存的股票列表"""
        key = f"stock:list:{market}"
        return await self.get_json(key)

    async def cache_kline(self, code: str, period: str, data: Any, ttl: int = 3600):
        """缓存K线数据（1小时过期）"""
        key = f"kline:{code}:{period}"
        await self.set_json(key, data, ex=ttl)

    async def get_cached_kline(self, code: str, period: str) -> Optional[Any]:
        """获取缓存的K线数据"""
        key = f"kline:{code}:{period}"
        return await self.get_json(key)

    async def cache_indicators(self, code: str, data: Any, ttl: int = 1800):
        """缓存技术指标（30分钟过期）"""
        key = f"indicators:{code}"
        await self.set_json(key, data, ex=ttl)

    async def get_cached_indicators(self, code: str) -> Optional[Any]:
        """获取缓存的技术指标"""
        key = f"indicators:{code}"
        return await self.get_json(key)

    async def cache_fund_flow(self, code: str, data: Any, ttl: int = 300):
        """缓存资金流向（5分钟过期）"""
        key = f"fund_flow:{code}"
        await self.set_json(key, data, ex=ttl)

    async def get_cached_fund_flow(self, code: str) -> Optional[Any]:
        """获取缓存的资金流向"""
        key = f"fund_flow:{code}"
        return await self.get_json(key)

    # ==================== 系统方法 ====================

    async def ping(self) -> bool:
        """测试连接"""
        if self.client is None:
            await self.connect()
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def flush_pattern_keys(self, pattern: str = "pattern:*"):
        """清除模式匹配的键（用于测试）"""
        if self.client is None:
            await self.connect()
        cursor = 0
        while True:
            cursor, keys = await self.client.scan(cursor, match=pattern, count=100)
            if keys:
                await self.client.delete(*keys)
            if cursor == 0:
                break


# 单例实例
_redis: Optional[RedisClient] = None


def get_redis() -> RedisClient:
    """获取Redis实例"""
    global _redis
    if _redis is None:
        _redis = RedisClient()
    return _redis


async def close_redis():
    """关闭Redis连接"""
    global _redis
    if _redis:
        await _redis.close()
        _redis = None
