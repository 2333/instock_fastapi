from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class IndicatorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_indicators(
        self, code: str, start_date: str | None, end_date: str | None, limit: int
    ) -> list[dict]:
        query = text("""
            SELECT i.*, s.name as stock_name
            FROM indicators i
            LEFT JOIN stocks s ON i.ts_code = s.ts_code
            WHERE s.symbol = :code
            ORDER BY i.trade_date DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"code": code, "limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_latest_indicator(self, code: str) -> dict | None:
        query = text("""
            SELECT i.*, s.name as stock_name
            FROM indicators i
            LEFT JOIN stocks s ON i.ts_code = s.ts_code
            WHERE s.symbol = :code
            ORDER BY i.trade_date DESC
            LIMIT 1
        """)
        result = await self.db.execute(query, {"code": code})
        row = result.fetchone()
        return dict(row._mapping) if row else None
