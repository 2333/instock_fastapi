from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
from typing import List, Optional, Any
from app.config import get_settings

settings = get_settings()


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_stocks(self, date: Optional[str], page: int, page_size: int) -> List[dict]:
        offset = (page - 1) * page_size

        # 如果没有提供日期，获取最新交易日
        if not date:
            result = await self.db.execute(
                text("SELECT MAX(trade_date) as latest_date FROM daily_bars")
            )
            row = result.fetchone()
            date = row[0] if row and row[0] else None

        if date:
            query = text("""
                SELECT 
                    s.ts_code as code,
                    s.name,
                    s.industry,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                INNER JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = :date
                WHERE s.is_etf = false AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)
        else:
            # 如果没有找到任何交易日的数据，返回股票基本信息
            query = text("""
                SELECT 
                    s.ts_code as code,
                    s.name,
                    s.industry,
                    null as date,
                    null as open,
                    null as high,
                    null as low,
                    null as close,
                    null as pre_close,
                    null as change_rate,
                    null as vol,
                    null as amount
                FROM stocks s
                WHERE s.is_etf = false AND s.list_status = 'L'
                LIMIT :limit OFFSET :offset
            """)

        result = await self.db.execute(query, {"date": date, "limit": page_size, "offset": offset})
        return [row._mapping for row in result.fetchall()]

    async def get_stock_detail(
        self, code: str, start_date: Optional[str], end_date: Optional[str]
    ) -> Optional[dict]:
        stock_query = text("""
            SELECT * FROM stocks WHERE symbol = :code OR ts_code = :code LIMIT 1
        """)
        result = await self.db.execute(stock_query, {"code": code})
        row = result.fetchone()
        if not row:
            return {"error": "Stock not found", "code": code}

        stock = dict(row._mapping)

        if start_date and end_date:
            bars_query = text("""
                SELECT * FROM daily_bars 
                WHERE ts_code = :ts_code AND trade_date BETWEEN :start_date AND :end_date
                ORDER BY trade_date ASC
            """)
            bars_result = await self.db.execute(
                bars_query,
                {"ts_code": stock["ts_code"], "start_date": start_date, "end_date": end_date},
            )
            stock["bars"] = [dict(row._mapping) for row in bars_result.fetchall()]

        return stock

    async def get_etf_list(self, date: Optional[str], page: int, page_size: int) -> List[dict]:
        offset = (page - 1) * page_size

        if date:
            query = text("""
                SELECT 
                    s.ts_code as code,
                    s.name,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                LEFT JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = :date
                WHERE s.is_etf = true AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
        else:
            query = text("""
                SELECT 
                    s.ts_code as code,
                    s.name,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                LEFT JOIN daily_bars db ON s.ts_code = db.ts_code
                WHERE s.is_etf = true AND s.list_status = 'L'
                ORDER BY db.trade_date DESC, db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)

        result = await self.db.execute(query, {"date": date, "limit": page_size, "offset": offset})
        return [row._mapping for row in result.fetchall()]

    async def get_etf_detail(self, code: str) -> Optional[dict]:
        query = text("""
            SELECT * FROM stocks WHERE (ts_code = :code OR symbol = :code) AND is_etf = true
        """)
        result = await self.db.execute(query, {"code": code})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def get_stock_count(self, is_etf: bool = False) -> int:
        query = text(
            "SELECT COUNT(*) as count FROM stocks WHERE is_etf = :is_etf AND list_status = 'L'"
        )
        result = await self.db.execute(query, {"is_etf": is_etf})
        row = result.fetchone()
        return row[0] if row else 0
