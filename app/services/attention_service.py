from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any


class AttentionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(self) -> List[dict]:
        query = text("""
            SELECT a.*, s.name as stock_name, s.symbol as code
            FROM attention a
            LEFT JOIN stocks s ON a.ts_code = s.ts_code
            ORDER BY a.created_at DESC
        """)
        result = await self.db.execute(query)
        return [row._mapping for row in result.fetchall()]

    async def add(self, code: str) -> Dict[str, Any]:
        ts_query = text("SELECT ts_code FROM stocks WHERE symbol = :code")
        result = await self.db.execute(ts_query, {"code": code})
        row = result.fetchone()

        if not row:
            return {"status": "error", "message": "Stock not found"}

        ts_code = row[0]

        query = text("""
            INSERT INTO attention (ts_code, user_id)
            VALUES (:ts_code, 'default')
            ON CONFLICT DO NOTHING
        """)
        await self.db.execute(query, {"ts_code": ts_code})
        await self.db.commit()
        return {"status": "success", "code": code}

    async def remove(self, code: str) -> Dict[str, Any]:
        ts_query = text("SELECT ts_code FROM stocks WHERE symbol = :code")
        result = await self.db.execute(ts_query, {"code": code})
        row = result.fetchone()

        if not row:
            return {"status": "error", "message": "Stock not found"}

        ts_code = row[0]

        query = text("DELETE FROM attention WHERE ts_code = :ts_code")
        await self.db.execute(query, {"ts_code": ts_code})
        await self.db.commit()
        return {"status": "success", "code": code}
