#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TimescaleDB 存储层

提供时序数据的存取接口
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple
from contextlib import asynccontextmanager
from decimal import Decimal

import pandas as pd
from sqlalchemy import (
    text,
    MetaData,
    Table,
    Column,
    String,
    Date,
    DateTime,
    Integer,
    BigInteger,
    Float,
    Boolean,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.pool import NullPool

from app.config import get_settings

logger = logging.getLogger(__name__)


class TimescaleDB:
    """TimescaleDB 存储类"""

    def __init__(self):
        self.settings = get_settings()
        self.engine = create_async_engine(
            self.settings.DATABASE_URL,
            poolclass=NullPool,
            echo=False,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        self.metadata = MetaData()

    @asynccontextmanager
    async def get_session(self):
        """获取数据库会话"""
        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def close(self):
        """关闭连接"""
        await self.engine.dispose()

    async def execute(self, query: str, params: Optional[Dict] = None):
        """执行SQL"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return result

    async def fetch_one(self, query: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """获取单条记录"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            row = result.fetchone()
            if row:
                return row._mapping
            return None

    async def fetch_all(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """获取所有记录"""
        async with self.get_session() as session:
            result = await session.execute(text(query), params or {})
            return [row._mapping for row in result.fetchall()]

    async def bulk_insert(self, table_name: str, records: List[Dict]):
        """批量插入"""
        if not records:
            return

        async with self.get_session() as session:
            await session.execute(
                text(f"""
                    INSERT INTO {table_name}
                    ({", ".join(records[0].keys())})
                    VALUES ({", ".join([":" + k for k in records[0].keys()])})
                    ON CONFLICT DO NOTHING
                """),
                records,
            )

    async def upsert(self, table_name: str, record: Dict, conflict_columns: List[str]):
        """插入或更新"""
        async with self.get_session() as session:
            columns = list(record.keys())
            values = {k: v for k, v in record.items() if v is not None}
            stmt = insert(text(table_name)).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=conflict_columns,
                set_={k: stmt.excluded[k] for k in columns if k not in conflict_columns},
            )
            await session.execute(stmt)

    # ==================== 股票相关操作 ====================

    async def save_daily_bars(self, bars: List[Dict]):
        """保存日线数据"""
        if not bars:
            return
        await self.bulk_insert("cn_stock_daily", bars)

    async def get_daily_bars(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict]:
        """获取日线数据"""
        query = """
            SELECT * FROM cn_stock_daily
            WHERE ts_code = :code
            ORDER BY trade_date DESC
        """
        params = {"code": code}

        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query += " LIMIT :limit"
        params["limit"] = limit

        return await self.fetch_all(query, params)

    async def save_stock_spot(self, stocks: List[Dict]):
        """保存股票实时行情"""
        await self.bulk_insert("cn_stock_spot", stocks)

    async def get_stock_spot(
        self,
        date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[Dict]:
        """获取股票行情"""
        query = """
            SELECT * FROM cn_stock_spot
            WHERE (:date IS NULL OR date = :date)
            ORDER BY change_rate DESC
            OFFSET :offset LIMIT :limit
        """
        return await self.fetch_all(
            query,
            {
                "date": date,
                "offset": (page - 1) * page_size,
                "limit": page_size,
            },
        )

    # ==================== ETF相关操作 ====================

    async def save_etf_spot(self, etfs: List[Dict]):
        """保存ETF行情"""
        await self.bulk_insert("cn_etf_spot", etfs)

    async def get_etf_spot(
        self,
        date: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> List[Dict]:
        """获取ETF行情"""
        query = """
            SELECT * FROM cn_etf_spot
            WHERE (:date IS NULL OR date = :date)
            ORDER BY change_rate DESC
            OFFSET :offset LIMIT :limit
        """
        return await self.fetch_all(
            query,
            {
                "date": date,
                "offset": (page - 1) * page_size,
                "limit": page_size,
            },
        )

    # ==================== 指标相关操作 ====================

    async def save_indicators(self, indicators: List[Dict]):
        """保存技术指标"""
        await self.bulk_insert("cn_stock_indicators", indicators)

    async def get_indicators(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取技术指标"""
        query = """
            SELECT * FROM cn_stock_indicators
            WHERE ts_code = :code
            ORDER BY trade_date DESC
        """
        params = {"code": code}

        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query += " LIMIT :limit"
        params["limit"] = limit

        return await self.fetch_all(query, params)

    async def get_latest_indicator(self, code: str) -> Optional[Dict]:
        """获取最新指标"""
        return await self.fetch_one(
            """
            SELECT * FROM cn_stock_indicators
            WHERE ts_code = :code
            ORDER BY trade_date DESC
            LIMIT 1
        """,
            {"code": code},
        )

    # ==================== 形态相关操作 ====================

    async def save_patterns(self, patterns: List[Dict]):
        """保存形态识别结果"""
        await self.bulk_insert("cn_stock_pattern", patterns)

    async def get_patterns(
        self,
        code: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取形态识别结果"""
        query = """
            SELECT * FROM cn_stock_pattern
            WHERE 1=1
        """
        params = {}

        if code:
            query += " AND ts_code = :code"
            params["code"] = code
        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        return await self.fetch_all(query, params)

    async def get_today_patterns(
        self,
        signal: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取今日形态信号"""
        query = """
            SELECT * FROM cn_stock_pattern
            WHERE trade_date = CURRENT_DATE
        """
        params = {}

        if signal:
            query += " AND signal = :signal"
            params["signal"] = signal

        query += " ORDER BY confidence DESC LIMIT :limit"
        params["limit"] = limit

        return await self.fetch_all(query, params)

    # ==================== 资金流向 ====================

    async def save_fund_flows(self, flows: List[Dict]):
        """保存资金流向"""
        await self.bulk_insert("cn_stock_fund_flow", flows)

    async def get_fund_flows(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取资金流向"""
        query = """
            SELECT * FROM cn_stock_fund_flow
            WHERE ts_code = :code
        """
        params = {"code": code}

        if start_date:
            query += " AND trade_date >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND trade_date <= :end_date"
            params["end_date"] = end_date

        query += " ORDER BY trade_date DESC LIMIT :limit"
        params["limit"] = limit

        return await self.fetch_all(query, params)

    # ==================== 选股相关 ====================

    async def save_selection_result(self, selections: List[Dict]):
        """保存选股结果"""
        await self.bulk_insert("cn_stock_selection", selections)

    async def get_selection_history(
        self,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """获取选股历史"""
        query = """
            SELECT * FROM cn_stock_selection
            WHERE (:date IS NULL OR date = :date)
            ORDER BY date DESC, score DESC
            LIMIT :limit
        """
        return await self.fetch_all(
            query,
            {
                "date": date,
                "limit": limit,
            },
        )

    # ==================== 自选股 ====================

    async def add_attention(self, user_id: int, code: str, name: str):
        """添加自选股"""
        await self.upsert(
            "cn_stock_attention",
            {
                "user_id": user_id,
                "ts_code": code,
                "name": name,
                "created_at": date.today().isoformat(),
            },
            conflict_columns=["user_id", "ts_code"],
        )

    async def get_attention(self, user_id: int) -> List[Dict]:
        """获取自选股"""
        return await self.fetch_all(
            """
            SELECT * FROM cn_stock_attention
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """,
            {"user_id": user_id},
        )

    async def remove_attention(self, user_id: int, code: str):
        """移除自选股"""
        await self.execute(
            """
            DELETE FROM cn_stock_attention
            WHERE user_id = :user_id AND ts_code = :code
        """,
            {"user_id": user_id, "code": code},
        )


# 单例实例
_db: Optional[TimescaleDB] = None


def get_timescaledb() -> TimescaleDB:
    """获取TimescaleDB实例"""
    global _db
    if _db is None:
        _db = TimescaleDB()
    return _db


async def close_timescaledb():
    """关闭TimescaleDB连接"""
    global _db
    if _db:
        await _db.close()
        _db = None
