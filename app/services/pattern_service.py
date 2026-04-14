import math

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.date_utils import trade_date_dt_param


class PatternService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_trade_date(self) -> str | None:
        query = text("""
            SELECT trade_date as latest_date
            FROM daily_bars
            ORDER BY
                CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                trade_date_dt DESC,
                trade_date DESC
            LIMIT 1
            """)
        result = await self.db.execute(query)
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def get_patterns(
        self, code: str, start_date: str | None, end_date: str | None, limit: int
    ) -> list[dict]:
        conditions = ["s.symbol = :code"]
        params: dict = {"code": code, "limit": limit}

        if start_date:
            conditions.append("(p.trade_date_dt >= :start_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date >= :start_date))")
            params["start_date"] = start_date
            params["start_date_dt"] = trade_date_dt_param(start_date)
        if end_date:
            conditions.append("(p.trade_date_dt <= :end_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date <= :end_date))")
            params["end_date"] = end_date
            params["end_date_dt"] = trade_date_dt_param(end_date)

        query = text(f"""
            SELECT p.*, s.name as stock_name, s.symbol as code
            FROM patterns p
            LEFT JOIN stocks s ON p.ts_code = s.ts_code
            WHERE {" AND ".join(conditions)}
            ORDER BY
                CASE WHEN p.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                p.trade_date_dt DESC,
                p.trade_date DESC,
                p.confidence DESC
            LIMIT :limit
        """)
        result = await self.db.execute(query, params)
        return [row._mapping for row in result.fetchall()]

    async def get_today_patterns(self, signal: str | None, limit: int) -> list[dict]:
        query = text("""
            SELECT p.*, s.name as stock_name, s.symbol as code
            FROM patterns p
            LEFT JOIN stocks s ON p.ts_code = s.ts_code
            ORDER BY
                CASE WHEN p.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                p.trade_date_dt DESC,
                p.trade_date DESC,
                p.confidence DESC
            LIMIT :limit
            """)
        result = await self.db.execute(query, {"limit": limit})
        return [row._mapping for row in result.fetchall()]

    async def get_composite_patterns(
        self,
        signal: str | None,
        limit: int,
        start_date: str | None,
        end_date: str | None,
        min_confidence: float,
        pattern_names: list[str] | None,
        ema_fast: int,
        ema_slow: int,
        boll_period: int,
        boll_std: float,
        ema_signal: str | None,
        boll_signal: str | None,
        indicator_mode: str,
    ) -> list[dict]:
        conditions = ["1=1"]
        params: dict = {"limit": limit, "min_confidence": min_confidence}

        if start_date:
            conditions.append("(p.trade_date_dt >= :start_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date >= :start_date))")
            params["start_date"] = start_date
            params["start_date_dt"] = trade_date_dt_param(start_date)
        if end_date:
            conditions.append("(p.trade_date_dt <= :end_date_dt OR (p.trade_date_dt IS NULL AND p.trade_date <= :end_date))")
            params["end_date"] = end_date
            params["end_date_dt"] = trade_date_dt_param(end_date)
        conditions.append("COALESCE(p.confidence, 0) >= :min_confidence")

        if pattern_names:
            placeholders = []
            for idx, name in enumerate(pattern_names):
                key = f"pattern_name_{idx}"
                placeholders.append(f":{key}")
                params[key] = name
            conditions.append(f"p.pattern_name IN ({', '.join(placeholders)})")

        query = text(f"""
            SELECT p.*, s.name as stock_name, s.symbol as code
            FROM patterns p
            LEFT JOIN stocks s ON p.ts_code = s.ts_code
            WHERE {" AND ".join(conditions)}
            ORDER BY
                CASE WHEN p.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                p.trade_date_dt DESC,
                p.trade_date DESC,
                p.confidence DESC
            LIMIT :limit
            """)
        result = await self.db.execute(query, params)
        rows = [dict(row._mapping) for row in result.fetchall()]

        enriched: list[dict] = []
        for row in rows:
            if signal:
                if self._pattern_signal(row.get("pattern_type")) != signal.upper():
                    continue

            indicator = await self._build_indicator_snapshot(
                ts_code=row.get("ts_code"),
                trade_date=row.get("trade_date"),
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                boll_period=boll_period,
                boll_std=boll_std,
            )
            row.update(indicator)

            ema_pass = True
            boll_pass = True
            if ema_signal:
                ema_pass = row.get("ema_signal") == ema_signal.lower()
            if boll_signal:
                boll_pass = row.get("boll_signal") == boll_signal.lower()

            if ema_signal and boll_signal:
                if indicator_mode == "any" and not (ema_pass or boll_pass):
                    continue
                if indicator_mode != "any" and not (ema_pass and boll_pass):
                    continue
            elif ema_signal and not ema_pass:
                continue
            elif boll_signal and not boll_pass:
                continue

            enriched.append(row)

        return enriched

    async def _build_indicator_snapshot(
        self,
        ts_code: str,
        trade_date: str,
        ema_fast: int,
        ema_slow: int,
        boll_period: int,
        boll_std: float,
    ) -> dict:
        max_period = max(ema_fast, ema_slow, boll_period)
        bars_query = text("""
            SELECT trade_date, close
            FROM daily_bars
            WHERE ts_code = :ts_code
              AND (trade_date_dt <= :trade_date_dt OR (trade_date_dt IS NULL AND trade_date <= :trade_date))
            ORDER BY
                CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END ASC,
                trade_date_dt DESC,
                trade_date DESC
            LIMIT :limit
            """)
        bars_result = await self.db.execute(
            bars_query,
            {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "trade_date_dt": trade_date_dt_param(trade_date),
                "limit": max_period + 30,
            },
        )
        bars = [dict(row._mapping) for row in bars_result.fetchall()]
        bars.reverse()

        closes = [float(item["close"]) for item in bars if item.get("close") is not None]
        if not closes:
            return {
                "ema_fast_value": None,
                "ema_slow_value": None,
                "ema_signal": "nodata",
                "boll_upper": None,
                "boll_mid": None,
                "boll_lower": None,
                "boll_signal": "nodata",
            }

        ema_fast_value = self._calc_ema(closes, ema_fast)
        ema_slow_value = self._calc_ema(closes, ema_slow)
        last_close = closes[-1]

        if ema_fast_value is None or ema_slow_value is None:
            ema_state = "nodata"
        elif last_close > ema_fast_value > ema_slow_value:
            ema_state = "bullish"
        elif last_close < ema_fast_value < ema_slow_value:
            ema_state = "bearish"
        else:
            ema_state = "neutral"

        boll_upper, boll_mid, boll_lower = self._calc_boll(closes, boll_period, boll_std)
        if boll_upper is None or boll_lower is None:
            boll_state = "nodata"
        elif last_close > boll_upper:
            boll_state = "breakout"
        elif last_close < boll_lower:
            boll_state = "breakdown"
        else:
            boll_state = "inside"

        return {
            "ema_fast_value": round(ema_fast_value, 4) if ema_fast_value is not None else None,
            "ema_slow_value": round(ema_slow_value, 4) if ema_slow_value is not None else None,
            "ema_signal": ema_state,
            "boll_upper": round(boll_upper, 4) if boll_upper is not None else None,
            "boll_mid": round(boll_mid, 4) if boll_mid is not None else None,
            "boll_lower": round(boll_lower, 4) if boll_lower is not None else None,
            "boll_signal": boll_state,
        }

    def _pattern_signal(self, pattern_type: str | None) -> str:
        t = (pattern_type or "").lower()
        if t in {"reversal", "breakout"}:
            return "BULLISH"
        if t in {"breakdown"}:
            return "BEARISH"
        return "NEUTRAL"

    def _calc_ema(self, values: list[float], period: int) -> float | None:
        if period <= 1 or len(values) < period:
            return None
        multiplier = 2 / (period + 1)
        seed = sum(values[:period]) / period
        ema = seed
        for value in values[period:]:
            ema = (value - ema) * multiplier + ema
        return ema

    def _calc_boll(
        self, values: list[float], period: int, std_mult: float
    ) -> tuple[float | None, float | None, float | None]:
        if period <= 1 or len(values) < period:
            return (None, None, None)
        window = values[-period:]
        mid = sum(window) / period
        variance = sum((x - mid) ** 2 for x in window) / period
        std = math.sqrt(variance)
        return (mid + std * std_mult, mid, mid - std * std_mult)
