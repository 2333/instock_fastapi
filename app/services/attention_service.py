from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class AttentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(self, user_id: int | None = None) -> list[dict]:
        if user_id is None:
            query = text("""
                SELECT a.*, s.name as stock_name, s.symbol as code
                FROM attention a
                LEFT JOIN stocks s ON a.ts_code = s.ts_code
                ORDER BY a.created_at DESC
            """)
            result = await self.db.execute(query)
        else:
            query = text("""
                SELECT a.*, s.name as stock_name, s.symbol as code
                FROM attention a
                LEFT JOIN stocks s ON a.ts_code = s.ts_code
                WHERE a.user_id = :user_id
                ORDER BY a.created_at DESC
            """)
            result = await self.db.execute(query, {"user_id": user_id})
        return [row._mapping for row in result.fetchall()]

    async def add(self, code: str, user_id: int) -> dict[str, Any]:
        ts_query = text("SELECT ts_code FROM stocks WHERE symbol = :code")
        result = await self.db.execute(ts_query, {"code": code})
        row = result.fetchone()

        if not row:
            return {"status": "error", "message": "Stock not found"}

        ts_code = row[0]

    query = text("""
    INSERT INTO attention (ts_code, user_id, created_at)
    VALUES (:ts_code, :user_id, NOW())
    ON CONFLICT (user_id, ts_code) DO NOTHING
    """)
        await self.db.execute(query, {"ts_code": ts_code, "user_id": user_id})
        await self.db.commit()
        return {"status": "success", "code": code}

    async def remove(self, code: str, user_id: int) -> dict[str, Any]:
        ts_query = text("SELECT ts_code FROM stocks WHERE symbol = :code")
        result = await self.db.execute(ts_query, {"code": code})
        row = result.fetchone()

        if not row:
            return {"status": "error", "message": "Stock not found"}

        ts_code = row[0]

        query = text("DELETE FROM attention WHERE ts_code = :ts_code AND user_id = :user_id")
        await self.db.execute(query, {"ts_code": ts_code, "user_id": user_id})
        await self.db.commit()
        return {"status": "success", "code": code}
