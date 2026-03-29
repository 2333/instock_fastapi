from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SelectionService:
    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    @staticmethod
    def get_conditions() -> dict[str, Any]:
        return {
            "markets": ["沪市", "深市", "创业板", "科创板"],
            "indicators": ["macd", "kdj", "boll", "rsi"],
            "strategies": ["放量上涨", "均线多头", "停机坪"],
        }

    @classmethod
    def get_screening_metadata(cls) -> dict[str, Any]:
        payload = cls.get_conditions()
        payload["filter_fields"] = [
            {
                "key": "priceMin",
                "label": "最低价格",
                "value_type": "number",
                "operators": [">="],
            },
            {
                "key": "priceMax",
                "label": "最高价格",
                "value_type": "number",
                "operators": ["<="],
            },
            {
                "key": "changeMin",
                "label": "最小涨跌幅",
                "value_type": "number",
                "operators": [">="],
            },
            {
                "key": "changeMax",
                "label": "最大涨跌幅",
                "value_type": "number",
                "operators": ["<="],
            },
            {
                "key": "market",
                "label": "市场范围",
                "value_type": "enum",
                "operators": ["="],
            },
        ]
        return payload

    async def _resolve_trade_date(self, date: str | None) -> str | None:
        if not self.db:
            return None
        if date:
            result = await self.db.execute(
                text("""
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date <= :target_date
                    """),
                {"target_date": date},
            )
        else:
            result = await self.db.execute(
                text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars")
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    @staticmethod
    def _format_condition_value(key: str, value: Any) -> str | int | float | bool:
        if key in {"priceMin", "priceMax", "changeMin", "changeMax"}:
            return round(float(value), 4)
        return value

    @staticmethod
    def _build_condition_evidence(
        *,
        key: str,
        label: str,
        operator: str,
        condition: Any,
        actual_value: Any,
    ) -> dict[str, Any]:
        return {
            "key": key,
            "label": label,
            "value": round(float(actual_value), 4)
            if isinstance(actual_value, (int, float))
            else actual_value,
            "operator": operator,
            "condition": SelectionService._format_condition_value(key, condition),
            "matched": True,
        }

    def _build_reason(self, conditions: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
        pct = float(row["pct_chg"] or 0)
        amount = float(row["amount"] or 0)
        close = float(row["close"] or 0)
        market_value = "sh" if str(row["ts_code"]).endswith(".SH") else "sz"
        evidence: list[dict[str, Any]] = []
        summary_parts: list[str] = []

        if conditions.get("priceMin") is not None:
            value = float(conditions["priceMin"])
            summary_parts.append(f"Close >= {value:.2f}")
            evidence.append(
                self._build_condition_evidence(
                    key="close",
                    label="Close",
                    operator=">=",
                    condition=value,
                    actual_value=close,
                )
            )
        if conditions.get("priceMax") is not None:
            value = float(conditions["priceMax"])
            summary_parts.append(f"Close <= {value:.2f}")
            evidence.append(
                self._build_condition_evidence(
                    key="close",
                    label="Close",
                    operator="<=",
                    condition=value,
                    actual_value=close,
                )
            )
        if conditions.get("changeMin") is not None:
            value = float(conditions["changeMin"])
            summary_parts.append(f"Change >= {value:.2f}%")
            evidence.append(
                self._build_condition_evidence(
                    key="change_rate",
                    label="Daily change",
                    operator=">=",
                    condition=value,
                    actual_value=pct,
                )
            )
        if conditions.get("changeMax") is not None:
            value = float(conditions["changeMax"])
            summary_parts.append(f"Change <= {value:.2f}%")
            evidence.append(
                self._build_condition_evidence(
                    key="change_rate",
                    label="Daily change",
                    operator="<=",
                    condition=value,
                    actual_value=pct,
                )
            )
        if conditions.get("market"):
            summary_parts.append(f"Market = {conditions['market']}")
            evidence.append(
                {
                    "key": "market",
                    "label": "Market",
                    "value": market_value,
                    "operator": "=",
                    "condition": str(conditions["market"]),
                    "matched": market_value == str(conditions["market"]),
                }
            )

        if summary_parts:
            summary = "; ".join(summary_parts[:3])
        else:
            summary = f"Included in latest screening universe with daily change {pct:.2f}%"
            evidence = [
                {
                    "key": "close",
                    "label": "Close",
                    "value": round(close, 4),
                    "matched": True,
                },
                {
                    "key": "change_rate",
                    "label": "Daily change",
                    "value": round(pct, 4),
                    "matched": True,
                },
                {
                    "key": "amount",
                    "label": "Turnover",
                    "value": round(amount, 4),
                    "matched": True,
                },
            ]

        return {"summary": summary, "evidence": evidence}

    async def run_selection(
        self, conditions: dict[str, Any], date: str | None, limit: int = 300
    ) -> list[dict]:
        if not self.db:
            return []

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

        sql = text(f"""
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
            WHERE {" AND ".join(where_sql)}
            ORDER BY db.pct_chg DESC NULLS LAST
            LIMIT :limit
            """)
        params["limit"] = limit
        rows = (await self.db.execute(sql, params)).mappings().all()

        results: list[dict] = []
        for row in rows:
            pct = float(row["pct_chg"] or 0)
            amt = float(row["amount"] or 0)
            score = pct * 5 + min(amt / 1e8, 20)
            signal = "hold"
            if pct >= 2:
                signal = "buy"
            elif pct <= -2:
                signal = "sell"
            reason = self._build_reason(conditions, row)
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
                    "reason_summary": reason["summary"],
                    "evidence": reason["evidence"],
                    "reason": reason,
                }
            )
        return results

    async def get_history(self, date: str | None, limit: int) -> list[dict]:
        if not self.db:
            return []
        where = []
        params: dict[str, Any] = {"limit": limit}
        if date:
            where.append("sr.trade_date = :trade_date")
            params["trade_date"] = date
        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = text(f"""
            SELECT
                sr.selection_id,
                sr.ts_code,
                split_part(sr.ts_code, '.', 1) AS code,
                s.name AS stock_name,
                sr.trade_date,
                sr.score
            FROM selection_results sr
            LEFT JOIN stocks s ON s.ts_code = sr.ts_code
            {where_sql}
            ORDER BY sr.trade_date DESC
            LIMIT :limit
            """)
        rows = (await self.db.execute(sql, params)).mappings().all()
        return [
            {
                "selection_id": row["selection_id"],
                "ts_code": row["ts_code"],
                "code": row["code"],
                "stock_name": row["stock_name"],
                "trade_date": row["trade_date"],
                "date": row["trade_date"],
                "score": float(row["score"] or 0),
                "signal": "hold",
                "reason_summary": f"Historical screening record {row['selection_id']}",
            }
            for row in rows
        ]
