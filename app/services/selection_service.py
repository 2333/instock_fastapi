from typing import Dict, Any, Optional, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class SelectionService:
    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    @staticmethod
    def get_conditions() -> Dict[str, Any]:
        return {
            "markets": ["沪市", "深市", "创业板", "科创板"],
            "indicators": ["macd", "kdj", "boll", "rsi"],
            "strategies": ["放量上涨", "均线多头", "停机坪"],
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
            result = await self.db.execute(
                text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars")
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def run_selection(self, conditions: Dict[str, Any], date: Optional[str]) -> List[dict]:
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
        params: Dict[str, Any] = {"trade_date": trade_date}

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

        results: List[dict] = []
        for row in rows:
            pct = float(row["pct_chg"] or 0)
            amt = float(row["amount"] or 0)
            score = pct * 5 + min(amt / 1e8, 20)  # 简单综合评分
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

    async def get_history(self, date: Optional[str], limit: int) -> List[dict]:
        if not self.db:
            return []
        where = []
        params: Dict[str, Any] = {"limit": limit}
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
              sr.score
            FROM selection_results sr
            LEFT JOIN stocks s ON s.ts_code = sr.ts_code
            {where_sql}
            ORDER BY sr.trade_date DESC
            LIMIT :limit
            """
        )
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
            }
            for row in rows
        ]
