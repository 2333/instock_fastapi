from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class BacktestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_backtest(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "backtest_id": "bt_001",
            "status": "running",
            "total_trades": 0,
            "win_rate": 0.0,
            "profit": 0.0,
        }

    async def get_result(self, backtest_id: str) -> dict[str, Any]:
        return {"backtest_id": backtest_id, "status": "completed"}


class SelectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_conditions() -> dict[str, Any]:
        return {
            "markets": ["沪市", "深市", "创业板", "科创板"],
            "indicators": ["macd", "kdj", "boll", "rsi"],
            "strategies": ["放量上涨", "均线多头", "停机坪"],
        }

    async def run_selection(self, conditions: dict[str, Any], date: str | None) -> list[dict]:
        return []

    async def get_history(self, date: str | None, limit: int) -> list[dict]:
        return []


class FundFlowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_fund_flow(self, code: str, days: int) -> list[dict]:
        query = text("""
            SELECT * FROM cn_stock_fund_flow
            WHERE code = :code
            ORDER BY time DESC
            LIMIT :days
            """)
        result = await self.db.execute(query, {"code": code, "days": days})
        return [row._mapping for row in result.fetchall()]

    async def get_industry_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []

    async def get_concept_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []


class AttentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(self) -> list[dict]:
        query = text("SELECT * FROM cn_stock_attention ORDER BY created_at DESC")
        result = await self.db.execute(query)
        return [row._mapping for row in result.fetchall()]

    async def add(self, code: str) -> dict[str, Any]:
        query = text("""
            INSERT INTO cn_stock_attention (code)
            VALUES (:code)
            ON CONFLICT (code) DO NOTHING
            RETURNING id, code
            """)
        await self.db.execute(query, {"code": code})
        return {"status": "success", "code": code}

    async def remove(self, code: str) -> dict[str, Any]:
        query = text("DELETE FROM cn_stock_attention WHERE code = :code")
        await self.db.execute(query, {"code": code})
        return {"status": "success", "code": code}
