#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 数据提供者实现

基于现有 repositories 实现 MarketDataProvider 接口。
使用 TimescaleDB 作为主存储。
"""

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import (
    DailyBar as OrmDailyBar,
    Stock as OrmStock,
    Indicator as OrmIndicator,
    FundFlow as OrmFundFlow,
)
from .market_data_provider import (
    MarketDataProvider,
    MarketDataProviderError,
    Pattern as DtoPattern,
)

logger = logging.getLogger(__name__)


class PostgreSQLProvider(MarketDataProvider):
    """PostgreSQL/TimescaleDB 数据提供者"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_daily_bars(
        self,
        codes: List[str],
        start_date: date,
        end_date: date,
        adjusted: bool = True
    ) -> pd.DataFrame:
        """获取日线数据"""
        try:
            # 获取股票代码映射（symbol -> ts_code）
            stmt_stocks = select(OrmStock.ts_code, OrmStock.symbol).where(OrmStock.symbol.in_(codes))
            result_stocks = await self.db.execute(stmt_stocks)
            stock_map = {row.ts_code: row.symbol for row in result_stocks.all()}
            ts_codes = list(stock_map.keys())

            if not ts_codes:
                return pd.DataFrame(columns=[
                    "code", "trade_date", "open", "high", "low", "close", "volume", "amount", "pct_chg"
                ])

            stmt = select(OrmDailyBar).where(
                OrmDailyBar.ts_code.in_(ts_codes),
                OrmDailyBar.trade_date_dt >= start_date,
                OrmDailyBar.trade_date_dt <= end_date
            ).order_by(OrmDailyBar.ts_code, OrmDailyBar.trade_date_dt)

            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            data = []
            for row in rows:
                data.append({
                    "ts_code": row.ts_code,
                    "code": stock_map.get(row.ts_code, ""),
                    "trade_date": row.trade_date_dt or row.trade_date,
                    "open": float(row.open) if row.open else None,
                    "high": float(row.high) if row.high else None,
                    "low": float(row.low) if row.low else None,
                    "close": float(row.close) if row.close else None,
                    "volume": float(row.vol) if row.vol else None,
                    "amount": float(row.amount) if row.amount else None,
                    "pct_chg": float(row.pct_chg) if row.pct_chg else None,
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to fetch daily bars: {e}")
            raise MarketDataProviderError(f"Database error: {e}") from e

    async def get_technicals(
        self,
        code: str,
        indicators: List[str],
        start_date: date,
        end_date: date
    ) -> Dict[str, pd.Series]:
        """获取技术指标"""
        try:
            stmt = select(OrmStock.ts_code).where(OrmStock.symbol == code)
            result = await self.db.execute(stmt)
            ts_code = result.scalar_one_or_none()

            if not ts_code:
                return {}

            stmt = select(OrmIndicator).where(
                OrmIndicator.ts_code == ts_code,
                OrmIndicator.indicator_name.in_(indicators),
                OrmIndicator.trade_date_dt >= start_date,
                OrmIndicator.trade_date_dt <= end_date
            ).order_by(OrmIndicator.indicator_name, OrmIndicator.trade_date_dt)

            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            result_dict: Dict[str, List[Tuple[date, Any]]] = {}
            for row in rows:
                if row.indicator_name not in result_dict:
                    result_dict[row.indicator_name] = []
                result_dict[row.indicator_name].append((
                    row.trade_date_dt or row.trade_date,
                    row.indicator_value
                ))

            output = {}
            for indicator_name, values in result_dict.items():
                dates, vals = zip(*values) if values else ([], [])
                output[indicator_name] = pd.Series(
                    data=vals,
                    index=pd.DatetimeIndex(dates),
                    name=indicator_name
                )

            return output

        except Exception as e:
            logger.error(f"Failed to fetch technicals for {code}: {e}")
            raise MarketDataProviderError(f"Database error: {e}") from e

    async def get_patterns(
        self,
        code: str,
        start_date: date,
        end_date: date
    ) -> List[DtoPattern]:
        """获取K线形态（未实现）"""
        return []

    async def get_fund_flow(
        self,
        codes: List[str],
        trade_date: date
    ) -> pd.DataFrame:
        """获取资金流向"""
        try:
            stmt = select(OrmStock.ts_code, OrmStock.symbol).where(OrmStock.symbol.in_(codes))
            result = await self.db.execute(stmt)
            stock_map = {row.symbol: row.ts_code for row in result.all()}
            ts_codes = list(stock_map.values())

            stmt = select(OrmFundFlow).where(
                OrmFundFlow.ts_code.in_(ts_codes),
                OrmFundFlow.trade_date_dt == trade_date
            )

            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            data = []
            for row in rows:
                data.append({
                    "ts_code": row.ts_code,
                    "code": next((sym for sym, tsc in stock_map.items() if tsc == row.ts_code), ""),
                    "main_net": float(row.net_amount_main) if row.net_amount_main else 0.0,
                    "hot_money": float(row.net_amount_hf) if row.net_amount_hf else 0.0,
                    "retail": float(row.net_amount_zz) if row.net_amount_zz else 0.0,
                    "total": float(row.net_amount_main or 0) + float(row.net_amount_hf or 0) + float(row.net_amount_zz or 0),
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to fetch fund flow: {e}")
            raise MarketDataProviderError(f"Database error: {e}") from e

    async def get_stock_list(
        self,
        markets: Optional[List[str]] = None,
        active_only: bool = True
    ) -> pd.DataFrame:
        """获取股票列表"""
        try:
            stmt = select(OrmStock)

            if active_only:
                stmt = stmt.where(OrmStock.list_status == "L")

            if markets:
                stmt = stmt.where(OrmStock.market.in_(markets))

            result = await self.db.execute(stmt)
            rows = result.scalars().all()

            data = []
            for row in rows:
                data.append({
                    "ts_code": row.ts_code,
                    "code": row.symbol,
                    "name": row.name,
                    "market": row.market,
                    "industry": row.industry,
                    "list_date": row.list_date,
                    "status": row.list_status,
                })

            return pd.DataFrame(data)

        except Exception as e:
            logger.error(f"Failed to fetch stock list: {e}")
            raise MarketDataProviderError(f"Database error: {e}") from e

    async def get_latest_trade_date(
        self,
        reference_date: Optional[date] = None
    ) -> date:
        """获取最新交易日"""
        try:
            ref_date = reference_date or date.today()

            stmt = select(func.max(OrmDailyBar.trade_date_dt)).where(
                OrmDailyBar.trade_date_dt <= ref_date
            )
            result = await self.db.execute(stmt)
            latest = result.scalar_one_or_none()

            if latest is None:
                raise MarketDataProviderError("No trade date found")

            return latest

        except Exception as e:
            logger.error(f"Failed to get latest trade date: {e}")
            raise MarketDataProviderError(f"Database error: {e}") from e

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            import time
            start = time.time()

            stmt = select(func.count(OrmStock.ts_code))
            result = await self.db.execute(stmt)
            count = result.scalar_one()

            latency = (time.time() - start) * 1000

            return {
                "status": "ok",
                "latency_ms": round(latency, 2),
                "details": {
                    "total_stocks": count,
                    "database": "PostgreSQL/TimescaleDB"
                }
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "error", "error": str(e)}
