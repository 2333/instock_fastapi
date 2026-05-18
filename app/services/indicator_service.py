from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.date_utils import parse_trade_date, trade_date_dt_param

INDICATOR_FIELD_MAP = {
    "MACD": "macd",
    "MACD_SIGNAL": "macds",
    "MACD_HIST": "macdh",
    "K": "kdjk",
    "D": "kdjd",
    "BOLL_UPPER": "boll_ub",
    "BOLL_MIDDLE": "boll",
    "BOLL_LOWER": "boll_lb",
    "RSI6": "rsi_6",
    "RSI12": "rsi_12",
    "RSI24": "rsi_24",
    "CR": "cr",
    "ATR": "atr",
    "SAR": "sar",
}


class IndicatorService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_trade_date_filter(value: str | None) -> str | None:
        parsed = parse_trade_date(value)
        if parsed is not None:
            return parsed.strftime("%Y%m%d")
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

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

    @staticmethod
    def _normalize_trade_date(value: str | None, value_dt: date | None) -> date | None:
        if value_dt is not None:
            return value_dt
        return parse_trade_date(value)

    @classmethod
    def _pivot_indicator_rows(cls, code: str, rows: list) -> list[dict]:
        grouped: dict[str, dict] = {}
        for row in rows:
            payload = dict(row._mapping)
            trade_date = payload.get("trade_date")
            if not trade_date:
                continue
            bucket = grouped.setdefault(
                trade_date,
                {
                    "time": cls._normalize_trade_date(
                        trade_date,
                        payload.get("trade_date_dt"),
                    ),
                    "code": code,
                },
            )
            field_name = INDICATOR_FIELD_MAP.get(str(payload.get("indicator_name") or "").upper())
            if field_name:
                bucket[field_name] = cls._to_float(payload.get("indicator_value"))

        for bucket in grouped.values():
            k_value = bucket.get("kdjk")
            d_value = bucket.get("kdjd")
            if k_value is not None and d_value is not None:
                bucket["kdjj"] = round((3 * k_value) - (2 * d_value), 4)

        return list(grouped.values())

    async def get_indicators(
        self, code: str, start_date: str | None, end_date: str | None, limit: int
    ) -> list[dict]:
        conditions = ["s.symbol = :code"]
        params: dict[str, object] = {"code": code, "limit": limit}
        normalized_start_date = self._normalize_trade_date_filter(start_date)
        normalized_end_date = self._normalize_trade_date_filter(end_date)

        if normalized_start_date:
            conditions.append(
                "(i.trade_date_dt >= :start_date_dt OR (i.trade_date_dt IS NULL AND i.trade_date >= :start_date))"
            )
            params["start_date"] = normalized_start_date
            params["start_date_dt"] = trade_date_dt_param(start_date)
        if normalized_end_date:
            conditions.append(
                "(i.trade_date_dt <= :end_date_dt OR (i.trade_date_dt IS NULL AND i.trade_date <= :end_date))"
            )
            params["end_date"] = normalized_end_date
            params["end_date_dt"] = trade_date_dt_param(end_date)

        query = text(f"""
            WITH target_trade_dates AS (
                SELECT
                    i.trade_date,
                    MAX(i.trade_date_dt) AS trade_date_dt
                FROM indicators i
                INNER JOIN stocks s ON i.ts_code = s.ts_code
                WHERE {" AND ".join(conditions)}
                GROUP BY i.trade_date
                ORDER BY
                    CASE WHEN MAX(i.trade_date_dt) IS NULL THEN 1 ELSE 0 END,
                    MAX(i.trade_date_dt) DESC,
                    i.trade_date DESC
                LIMIT :limit
            )
            SELECT
                i.trade_date,
                i.trade_date_dt,
                i.indicator_name,
                i.indicator_value
            FROM indicators i
            INNER JOIN stocks s ON i.ts_code = s.ts_code
            INNER JOIN target_trade_dates td ON i.trade_date = td.trade_date
            WHERE s.symbol = :code
            ORDER BY
                CASE WHEN td.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                td.trade_date_dt DESC,
                td.trade_date DESC,
                i.indicator_name ASC
        """)
        result = await self.db.execute(query, params)
        return self._pivot_indicator_rows(code, result.fetchall())

    async def get_latest_indicator(self, code: str) -> dict | None:
        rows = await self.get_indicators(code, start_date=None, end_date=None, limit=1)
        return rows[0] if rows else None
