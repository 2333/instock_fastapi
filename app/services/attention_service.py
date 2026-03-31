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

    async def add(self, code: str, user_id: int, group: str = "watch", notes: str | None = None, alert_conditions: dict | None = None) -> dict[str, Any]:
        ts_query = text("SELECT ts_code FROM stocks WHERE symbol = :code")
        result = await self.db.execute(ts_query, {"code": code})
        row = result.fetchone()

        if not row:
            return {"status": "error", "message": "Stock not found"}

        ts_code = row[0]

        # Check if exists, then update; else insert
        check_query = text("SELECT id FROM attention WHERE user_id = :user_id AND ts_code = :ts_code")
        check_result = await self.db.execute(check_query, {"user_id": user_id, "ts_code": ts_code})
        existing = check_result.fetchone()

        if existing:
            # Update existing
            update_query = text("""
                UPDATE attention
                SET group = :group, notes = :notes, alert_conditions = :alert_conditions
                WHERE id = :id
            """)
            await self.db.execute(update_query, {
                "id": existing[0],
                "group": group,
                "notes": notes,
                "alert_conditions": alert_conditions,
            })
            await self.db.commit()
            return {"status": "success", "code": code}
        else:
            # Insert new
            insert_query = text("""
                INSERT INTO attention (ts_code, user_id, group, notes, alert_conditions, created_at)
                VALUES (:ts_code, :user_id, :group, :notes, :alert_conditions, NOW())
            """)
            await self.db.execute(insert_query, {
                "ts_code": ts_code,
                "user_id": user_id,
                "group": group,
                "notes": notes,
                "alert_conditions": alert_conditions,
            })
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

    async def update(self, attention_id: int, user_id: int, updates: dict[str, Any]) -> dict[str, Any]:
        """Update attention item fields (group, notes, alert_conditions)."""
        fields: list[str] = []
        params: dict[str, Any] = {"id": attention_id, "user_id": user_id}

        if "group" in updates:
            fields.append("group = :group")
            params["group"] = updates["group"]
        if "notes" in updates:
            fields.append("notes = :notes")
            params["notes"] = updates["notes"]
        if "alert_conditions" in updates:
            fields.append("alert_conditions = :alert_conditions")
            params["alert_conditions"] = updates["alert_conditions"]

        if not fields:
            return {"status": "error", "message": "No fields to update"}

        query = text(f"UPDATE attention SET {', '.join(fields)} WHERE id = :id AND user_id = :user_id")
        await self.db.execute(query, params)
        await self.db.commit()
        return {"status": "success", "id": attention_id}
