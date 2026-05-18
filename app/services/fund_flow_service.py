from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class FundFlowService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _to_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(round(value))
        if isinstance(value, Decimal):
            return int(round(float(value)))
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_float(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, float):
            return value
        if isinstance(value, int):
            return float(value)
        if isinstance(value, Decimal):
            return float(value)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def get_fund_flow(self, code: str, days: int) -> list[dict]:
        query = text("""
            SELECT
                f.trade_date as time,
                s.symbol as code,
                s.name as name,
                f.net_amount_main as fund_amount,
                null as fund_rate
            FROM fund_flows f
            LEFT JOIN stocks s ON f.ts_code = s.ts_code
            WHERE s.symbol = :code
            ORDER BY
                CASE WHEN f.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                f.trade_date_dt DESC,
                f.trade_date DESC
            LIMIT :days
        """)
        result = await self.db.execute(query, {"code": code, "days": days})
        rows = []
        for row in result.fetchall():
            payload = dict(row._mapping)
            rows.append(
                {
                    "time": payload.get("time"),
                    "code": payload.get("code"),
                    "name": payload.get("name"),
                    "fund_amount": self._to_int(payload.get("fund_amount")),
                    "fund_rate": self._to_float(payload.get("fund_rate")),
                }
            )
        return rows

    async def get_industry_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []

    async def get_concept_fund_flow(self, date: str | None, limit: int) -> list[dict]:
        return []
