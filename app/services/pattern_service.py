from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional


class PatternService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_patterns(
        self, code: str, start_date: Optional[str], end_date: Optional[str], limit: int
    ) -> List[dict]:
        query = text("""
            SELECT p.*, s.name as stock_name
            FROM patterns p
            LEFT JOIN stocks s ON p.ts_code = s.ts_code
            WHERE s.symbol = :code
            ORDER BY p.trade_date DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"code": code, "limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_today_patterns(self, signal: Optional[str], limit: int) -> List[dict]:
        query = text("""
            SELECT p.*, s.name as stock_name, s.symbol as code
            FROM patterns p
            LEFT JOIN stocks s ON p.ts_code = s.ts_code
            ORDER BY p.trade_date DESC, p.confidence DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"limit": limit})
        return [row._mapping for row in result.fetchall()]
