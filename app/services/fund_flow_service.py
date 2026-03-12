from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class FundFlowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_fund_flow(self, code: str, days: int) -> list[dict]:
        query = text("""
            SELECT f.*, s.name as stock_name
            FROM fund_flows f
            LEFT JOIN stocks s ON f.ts_code = s.ts_code
            WHERE s.symbol = :code
            ORDER BY f.trade_date DESC
            LIMIT :days
        """)
        result = await self.db.execute(query, {"code": code, "days": days})
        return [row._mapping for row in result.fetchall()]

    async def get_industry_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []

    async def get_concept_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []
