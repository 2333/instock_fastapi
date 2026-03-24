from __future__ import annotations

import uuid
from typing import Any, Optional

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import SelectionResult
from app.selection import SelectionExecutionEngine, build_selection_catalog, build_selection_registry
from app.selection.dsl import validate_selection_template


class SelectionService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    @staticmethod
    def get_conditions() -> dict[str, Any]:
        catalog = build_selection_catalog()
        technical_metrics = [
            item["key"]
            for group in catalog["groups"]
            if group["key"] == "technical"
            for item in group["items"]
        ]
        return {
            **catalog,
            "markets": ["沪市", "深市", "创业板", "科创板"],
            "indicators": technical_metrics,
            "strategies": ["自定义规则树"],
        }

    async def _resolve_trade_date(self, date: Optional[str]) -> Optional[str]:
        if not self.db:
            return None
        if date:
            result = await self.db.execute(
                text(
                    """
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date <= :target_date
                    """
                ),
                {"target_date": date},
            )
        else:
            result = await self.db.execute(text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars"))
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def run_selection(
        self,
        conditions: dict[str, Any],
        date: Optional[str],
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if not self.db:
            return []

        template_payload: dict[str, Any] | None = None
        if isinstance(conditions, dict):
            if isinstance(conditions.get("template"), dict):
                template_payload = conditions["template"]
            elif isinstance(conditions.get("root"), dict):
                template_payload = conditions

        if not template_payload:
            return await self._run_legacy_selection(conditions, date)

        try:
            template = validate_selection_template(template_payload)
        except ValidationError as exc:
            raise ValueError(exc.errors()) from exc

        engine = SelectionExecutionEngine(self.db, build_selection_registry())
        result = await engine.execute(
            template,
            trade_date=date or conditions.get("date"),
            limit=int(conditions.get("limit", 200) or 200),
        )
        selection_id = str(uuid.uuid4())
        result["selection_id"] = selection_id
        if conditions.get("persist_result", True):
            await self._persist_selection_results(selection_id, result, template.name)
        return result

    async def _persist_selection_results(
        self,
        selection_id: str,
        result: dict[str, Any],
        template_name: str | None,
    ) -> None:
        if not self.db:
            return
        trade_date = result.get("trade_date")
        for item in result.get("items", []):
            self.db.add(
                SelectionResult(
                    selection_id=selection_id,
                    ts_code=item["ts_code"],
                    trade_date=trade_date,
                    score=item.get("score"),
                    conditions={
                        "template_name": template_name,
                        "period": result.get("period"),
                        "matched_conditions": item.get("matched_conditions"),
                        "total_conditions": item.get("total_conditions"),
                        "signal": item.get("signal"),
                        "snapshot": item.get("snapshot"),
                        "explanations": item.get("explanations", []),
                    },
                )
            )
        await self.db.commit()

    async def _run_legacy_selection(
        self, conditions: dict[str, Any], date: Optional[str]
    ) -> list[dict[str, Any]]:
        trade_date = await self._resolve_trade_date(date)
        if not trade_date:
            return []

        price_min = conditions.get("priceMin")
        price_max = conditions.get("priceMax")
        change_min = conditions.get("changeMin")
        change_max = conditions.get("changeMax")
        market = conditions.get("market")

        where_sql = [
            "s.list_status = 'L'",
            "s.is_etf = false",
            "db.trade_date = :trade_date",
        ]
        params: dict[str, Any] = {"trade_date": trade_date}

        if price_min is not None:
            where_sql.append("db.close >= :price_min")
            params["price_min"] = price_min
        if price_max is not None:
            where_sql.append("db.close <= :price_max")
            params["price_max"] = price_max
        if change_min is not None:
            where_sql.append("db.pct_chg >= :change_min")
            params["change_min"] = change_min
        if change_max is not None:
            where_sql.append("db.pct_chg <= :change_max")
            params["change_max"] = change_max
        if market == "sh":
            where_sql.append("s.symbol LIKE '6%'")
        elif market == "sz":
            where_sql.append("(s.symbol LIKE '0%' OR s.symbol LIKE '3%')")

        sql = text(
            f"""
            SELECT
                s.ts_code,
                s.symbol AS code,
                s.name AS stock_name,
                db.trade_date,
                db.close,
                db.pct_chg,
                db.vol,
                db.amount
            FROM stocks s
            JOIN daily_bars db ON s.ts_code = db.ts_code
            WHERE {' AND '.join(where_sql)}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT 300
            """
        )
        rows = (await self.db.execute(sql, params)).mappings().all()

        results: list[dict[str, Any]] = []
        for row in rows:
            pct = float(row["pct_chg"] or 0)
            amt = float(row["amount"] or 0)
            score = pct * 5 + min(amt / 1e8, 20)
            signal = "hold"
            if pct >= 2:
                signal = "buy"
            elif pct <= -2:
                signal = "sell"
            results.append(
                {
                    "ts_code": row["ts_code"],
                    "code": row["code"],
                    "stock_name": row["stock_name"],
                    "score": round(score, 4),
                    "signal": signal,
                    "trade_date": row["trade_date"],
                    "date": row["trade_date"],
                    "close": float(row["close"] or 0),
                    "change_rate": pct,
                    "amount": amt,
                }
            )
        return results

    async def get_history(self, date: Optional[str], limit: int) -> list[dict]:
        if not self.db:
            return []
        where = []
        params: dict[str, Any] = {"limit": limit}
        if date:
            where.append("sr.trade_date = :trade_date")
            params["trade_date"] = date
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = text(
            f"""
            SELECT
                sr.selection_id,
                sr.ts_code,
                split_part(sr.ts_code, '.', 1) AS code,
                s.name AS stock_name,
                sr.trade_date,
                sr.score,
                sr.conditions
            FROM selection_results sr
            LEFT JOIN stocks s ON s.ts_code = sr.ts_code
            {where_sql}
            ORDER BY sr.created_at DESC, sr.trade_date DESC
            LIMIT :limit
            """
        )
        rows = (await self.db.execute(sql, params)).mappings().all()
        payload = []
        for row in rows:
            item = {
                "selection_id": row["selection_id"],
                "ts_code": row["ts_code"],
                "code": row["code"],
                "stock_name": row["stock_name"],
                "trade_date": row["trade_date"],
                "date": row["trade_date"],
                "score": float(row["score"] or 0),
                "signal": (row.get("conditions") or {}).get("signal", "hold"),
            }
            if row.get("conditions") is not None:
                item["conditions"] = row.get("conditions")
            payload.append(item)
        return payload
