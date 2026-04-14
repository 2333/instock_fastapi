import logging
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.services.date_utils import trade_date_dt_param
from app.utils.stock_codes import build_code_variants, extract_symbol, normalize_stock_payload
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.base import AdjustType
from core.crawling.eastmoney import EastMoneyCrawler

settings = get_settings()
logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_row_mapping(row: dict) -> dict:
        return normalize_stock_payload(dict(row))

    async def _resolve_trade_date(self, target_date: str | None) -> str | None:
        if target_date:
            target_date_dt = trade_date_dt_param(target_date)
            result = await self.db.execute(
                text("""
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date_dt <= :target_date_dt
                       OR (trade_date_dt IS NULL AND trade_date <= :target_date)
                """),
                {"target_date": target_date, "target_date_dt": target_date_dt},
            )
        else:
            result = await self.db.execute(
                text("""
                    SELECT trade_date AS resolved_date
                    FROM daily_bars
                    ORDER BY
                        CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                        trade_date_dt DESC,
                        trade_date DESC
                    LIMIT 1
                """)
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def get_stocks(self, date: str | None, page: int, page_size: int) -> list[dict]:
        offset = (page - 1) * page_size
        date = await self._resolve_trade_date(date)
        date_dt = trade_date_dt_param(date)

        if date:
            query = text("""
                SELECT
                    s.symbol as code,
                    s.ts_code,
                    s.symbol,
                    s.exchange,
                    s.name,
                    s.industry,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                INNER JOIN daily_bars db
                    ON s.ts_code = db.ts_code
                    AND (db.trade_date_dt = :date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :date))
                WHERE s.is_etf = false AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)
        else:
            query = text("""
                SELECT
                    s.symbol as code,
                    s.ts_code,
                    s.symbol,
                    s.exchange,
                    s.name,
                    s.industry,
                    null as date,
                    null as open,
                    null as high,
                    null as low,
                    null as close,
                    null as pre_close,
                    null as change_rate,
                    null as vol,
                    null as amount
                FROM stocks s
                WHERE s.is_etf = false AND s.list_status = 'L'
                LIMIT :limit OFFSET :offset
            """)

        result = await self.db.execute(
            query, {"date": date, "date_dt": date_dt, "limit": page_size, "offset": offset}
        )
        return [self._normalize_row_mapping(row._mapping) for row in result.fetchall()]

    async def get_stocks_with_total(
        self, date: str | None, page: int, page_size: int
    ) -> tuple[list[dict], int]:
        """获取股票列表和总数"""
        date = await self._resolve_trade_date(date)
        date_dt = trade_date_dt_param(date)

        # 获取总数
        if date:
            count_query = text("""
                SELECT COUNT(*) as total
                FROM stocks s
                INNER JOIN daily_bars db
                    ON s.ts_code = db.ts_code
                    AND (db.trade_date_dt = :date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :date))
                WHERE s.is_etf = false AND s.list_status = 'L'
            """)
        else:
            count_query = text("""
                SELECT COUNT(*) as total
                FROM stocks s
                WHERE s.is_etf = false AND s.list_status = 'L'
            """)

        count_result = await self.db.execute(count_query, {"date": date, "date_dt": date_dt})
        count_row = count_result.fetchone()
        total = count_row[0] if count_row else 0

        # 获取分页数据
        data = await self.get_stocks(date, page, page_size)
        return data, total

    @staticmethod
    def _normalize_date(value: str | None) -> str | None:
        if not value:
            return None
        v = value.strip()
        if len(v) == 8 and v.isdigit():
            return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
        return v.replace("/", "-")

    @staticmethod
    def _parse_adjust(value: str | None) -> AdjustType:
        mapping = {
            "bfq": AdjustType.NO_ADJUST,
            "qfq": AdjustType.FORWARD,
            "hfq": AdjustType.BACKWARD,
        }
        return mapping.get((value or "bfq").lower(), AdjustType.NO_ADJUST)

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
    def _normalize_indicator_key(name: str | None) -> str:
        return str(name or "").strip().lower()

    @staticmethod
    def _pattern_signal(pattern_type: str | None) -> str:
        pattern = str(pattern_type or "").strip().lower()
        if pattern in {"reversal", "breakout", "trend"}:
            return "bullish"
        if pattern == "breakdown":
            return "bearish"
        return "neutral"

    async def _get_latest_bar_snapshot(self, ts_code: str) -> dict | None:
        query = text("""
            SELECT
                trade_date,
                open,
                high,
                low,
                close,
                pre_close,
                change,
                pct_chg,
                vol,
                amount
            FROM daily_bars
            WHERE ts_code = :ts_code
            ORDER BY
                CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                trade_date_dt DESC,
                trade_date DESC
            LIMIT 1
        """)
        result = await self.db.execute(query, {"ts_code": ts_code})
        row = result.fetchone()
        if not row:
            return None

        latest_bar = dict(row._mapping)
        return {
            "trade_date": latest_bar.get("trade_date"),
            "open": self._to_float(latest_bar.get("open")),
            "high": self._to_float(latest_bar.get("high")),
            "low": self._to_float(latest_bar.get("low")),
            "close": self._to_float(latest_bar.get("close")),
            "pre_close": self._to_float(latest_bar.get("pre_close")),
            "change": self._to_float(latest_bar.get("change")),
            "change_rate": self._to_float(latest_bar.get("pct_chg")),
            "vol": self._to_float(latest_bar.get("vol")),
            "amount": self._to_float(latest_bar.get("amount")),
        }

    async def _get_latest_indicator_snapshot(self, ts_code: str) -> dict | None:
        latest_trade_date_query = text("""
            SELECT trade_date
            FROM indicators
            WHERE ts_code = :ts_code
            ORDER BY
                CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                trade_date_dt DESC,
                trade_date DESC
            LIMIT 1
        """)
        latest_trade_date_result = await self.db.execute(
            latest_trade_date_query, {"ts_code": ts_code}
        )
        latest_trade_date_row = latest_trade_date_result.fetchone()
        trade_date = latest_trade_date_row[0] if latest_trade_date_row else None
        if not trade_date:
            return None

        indicator_query = text("""
            SELECT indicator_name, indicator_value
            FROM indicators
            WHERE ts_code = :ts_code
              AND (trade_date_dt = :trade_date_dt OR (trade_date_dt IS NULL AND trade_date = :trade_date))
            ORDER BY indicator_name ASC
        """)
        indicator_result = await self.db.execute(
            indicator_query,
            {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "trade_date_dt": trade_date_dt_param(trade_date),
            },
        )
        rows = indicator_result.fetchall()

        values: dict[str, float | None] = {}
        highlights: list[str] = []
        for row in rows:
            indicator_name = self._normalize_indicator_key(row._mapping.get("indicator_name"))
            indicator_value = self._to_float(row._mapping.get("indicator_value"))
            if not indicator_name:
                continue
            values[indicator_name] = indicator_value
            if indicator_value is not None:
                highlights.append(f"{indicator_name.upper()} {indicator_value:.2f}")

        return {
            "trade_date": trade_date,
            "values": values,
            "highlights": highlights[:5],
        }

    async def _get_recent_patterns(self, ts_code: str, limit: int = 5) -> dict | None:
        query = text("""
            SELECT trade_date, pattern_name, pattern_type, confidence
            FROM patterns
            WHERE ts_code = :ts_code
            ORDER BY
                CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END,
                trade_date_dt DESC,
                trade_date DESC,
                confidence DESC NULLS LAST,
                pattern_name ASC
            LIMIT :limit
        """)
        result = await self.db.execute(query, {"ts_code": ts_code, "limit": limit})
        rows = [dict(row._mapping) for row in result.fetchall()]
        if not rows:
            return None

        bullish_count = 0
        bearish_count = 0
        neutral_count = 0
        latest_hits: list[dict] = []
        for row in rows:
            signal = self._pattern_signal(row.get("pattern_type"))
            if signal == "bullish":
                bullish_count += 1
            elif signal == "bearish":
                bearish_count += 1
            else:
                neutral_count += 1

            confidence = self._to_float(row.get("confidence"))
            latest_hits.append(
                {
                    "trade_date": row.get("trade_date"),
                    "pattern_name": row.get("pattern_name"),
                    "pattern_type": row.get("pattern_type"),
                    "confidence": confidence,
                    "signal": signal,
                    "summary": (
                        f"{row.get('pattern_name')} on {row.get('trade_date')}"
                        if confidence is None
                        else f"{row.get('pattern_name')} on {row.get('trade_date')} "
                        f"(confidence {confidence:.2f})"
                    ),
                }
            )

        return {
            "latest_trade_date": rows[0].get("trade_date"),
            "hit_count": len(rows),
            "bullish_count": bullish_count,
            "bearish_count": bearish_count,
            "neutral_count": neutral_count,
            "latest_hits": latest_hits,
        }

    def _build_data_freshness(
        self,
        latest_trade_date: str | None,
        indicator_trade_date: str | None,
        pattern_trade_date: str | None,
    ) -> dict:
        return {
            "price_trade_date": latest_trade_date,
            "indicator_trade_date": indicator_trade_date,
            "pattern_trade_date": pattern_trade_date,
            "latest_trade_date": latest_trade_date,
            "price_current": latest_trade_date is not None,
            "indicator_current": bool(
                latest_trade_date and indicator_trade_date == latest_trade_date
            ),
            "pattern_current": bool(latest_trade_date and pattern_trade_date == latest_trade_date),
        }

    def _build_validation_context(
        self,
        latest_bar: dict | None,
        latest_indicator_snapshot: dict | None,
        recent_patterns: dict | None,
    ) -> dict:
        screening_metrics: list[dict] = []
        pattern_annotations: list[dict] = []

        if latest_bar:
            trade_date = latest_bar.get("trade_date")
            close = latest_bar.get("close")
            change_rate = latest_bar.get("change_rate")
            amount = latest_bar.get("amount")

            if close is not None:
                screening_metrics.append(
                    {
                        "metric": "close",
                        "trade_date": trade_date,
                        "value": close,
                        "summary": f"Latest close {close:.2f}",
                        "source": "daily_bars",
                        "context": {"field": "close"},
                    }
                )
            if change_rate is not None:
                screening_metrics.append(
                    {
                        "metric": "change_rate",
                        "trade_date": trade_date,
                        "value": change_rate,
                        "summary": f"Daily change {change_rate:.2f}%",
                        "source": "daily_bars",
                        "context": {"field": "pct_chg"},
                    }
                )
            if amount is not None:
                screening_metrics.append(
                    {
                        "metric": "amount",
                        "trade_date": trade_date,
                        "value": amount,
                        "summary": f"Turnover {amount:.0f}",
                        "source": "daily_bars",
                        "context": {"field": "amount"},
                    }
                )

        if latest_indicator_snapshot:
            trade_date = latest_indicator_snapshot.get("trade_date")
            for key, value in latest_indicator_snapshot.get("values", {}).items():
                if value is None:
                    continue
                screening_metrics.append(
                    {
                        "metric": key,
                        "trade_date": trade_date,
                        "value": value,
                        "summary": f"{key.upper()} {value:.2f}",
                        "source": "indicators",
                        "context": {"field": key},
                    }
                )

        if recent_patterns:
            for hit in recent_patterns.get("latest_hits", []):
                pattern_annotations.append(
                    {
                        "metric": hit.get("pattern_name", ""),
                        "trade_date": hit.get("trade_date"),
                        "value": hit.get("confidence"),
                        "summary": hit.get("summary"),
                        "source": "patterns",
                        "context": {
                            "pattern_type": hit.get("pattern_type"),
                            "signal": hit.get("signal"),
                        },
                    }
                )

        return {
            "as_of_trade_date": (latest_bar or {}).get("trade_date"),
            "screening_metrics": screening_metrics,
            "pattern_annotations": pattern_annotations,
        }

    async def _fetch_adjusted_bars(
        self,
        symbol: str,
        start_date: str | None,
        end_date: str | None,
        adjust: AdjustType,
    ) -> list[dict]:
        baostock_provider = BaoStockProvider()
        eastmoney_crawler = EastMoneyCrawler()
        bars: list[dict] = []

        start = self._normalize_date(start_date)
        end = self._normalize_date(end_date)

        try:
            bars = await baostock_provider.fetch_kline(
                code=symbol,
                start_date=start,
                end_date=end,
                adjust=adjust,
                period="daily",
            )
        except Exception as exc:
            logger.warning("%s BaoStock 拉取失败，降级 EastMoney: %s", symbol, exc)

        if not bars:
            bars = await eastmoney_crawler.fetch(
                data_type="kline",
                code=symbol,
                start_date=start,
                end_date=end,
                adjust=adjust,
                period="daily",
            )
        await eastmoney_crawler.close()

        normalized: list[dict] = []
        for row in bars or []:
            date_raw = str(row.get("date", "")).strip()
            trade_date = date_raw.replace("-", "")
            normalized.append(
                {
                    "trade_date": trade_date,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),
                    "pre_close": row.get("pre_close"),
                    "change": row.get("change"),
                    "pct_chg": row.get("change_pct"),
                    "vol": row.get("volume"),
                    "amount": row.get("amount"),
                }
            )
        return normalized

    async def _query_bars_from_db(
        self, ts_code: str, start_date: str | None, end_date: str | None
    ) -> list[dict]:
        if not (start_date and end_date):
            return []
        bars_query = text("""
            SELECT * FROM daily_bars
            WHERE ts_code = :ts_code
              AND (
                trade_date_dt BETWEEN :start_date_dt AND :end_date_dt
                OR (trade_date_dt IS NULL AND trade_date BETWEEN :start_date AND :end_date)
              )
            ORDER BY
              CASE WHEN trade_date_dt IS NULL THEN 1 ELSE 0 END ASC,
              trade_date_dt ASC,
              trade_date ASC
        """)
        bars_result = await self.db.execute(
            bars_query,
            {
                "ts_code": ts_code,
                "start_date": start_date,
                "end_date": end_date,
                "start_date_dt": trade_date_dt_param(start_date),
                "end_date_dt": trade_date_dt_param(end_date),
            },
        )
        return [dict(row._mapping) for row in bars_result.fetchall()]

    async def get_stock_detail(
        self, code: str, start_date: str | None, end_date: str | None, adjust: str = "bfq"
    ) -> dict | None:
        candidates = build_code_variants(code)
        symbol = extract_symbol(code)
        stock_query = text("""
            SELECT *
            FROM stocks
            WHERE symbol = :symbol
               OR ts_code = :code
               OR ts_code = :code_sh
               OR ts_code = :code_sz
               OR ts_code = :code_bj
               OR ts_code = :code_sse
               OR ts_code = :code_szse
               OR ts_code = :code_bse
            LIMIT 1
        """)
        result = await self.db.execute(
            stock_query,
            {
                "symbol": symbol,
                "code": code,
                "code_sh": next((item for item in candidates if item.endswith(".SH")), ""),
                "code_sz": next((item for item in candidates if item.endswith(".SZ")), ""),
                "code_bj": next((item for item in candidates if item.endswith(".BJ")), ""),
                "code_sse": next((item for item in candidates if item.endswith(".SSE")), ""),
                "code_szse": next((item for item in candidates if item.endswith(".SZSE")), ""),
                "code_bse": next((item for item in candidates if item.endswith(".BSE")), ""),
            },
        )
        row = result.fetchone()
        if not row:
            return {"error": "Stock not found", "code": code}

        stock = dict(row._mapping)
        internal_ts_code = stock["ts_code"]
        latest_bar = await self._get_latest_bar_snapshot(internal_ts_code)
        latest_indicator_snapshot = await self._get_latest_indicator_snapshot(internal_ts_code)
        recent_patterns = await self._get_recent_patterns(internal_ts_code)

        latest_trade_date = latest_bar["trade_date"] if latest_bar else None
        stock["latest_trade_date"] = latest_trade_date
        stock["latest_bar"] = latest_bar
        stock["latest_indicator_snapshot"] = latest_indicator_snapshot
        stock["recent_patterns"] = recent_patterns
        stock["data_freshness"] = self._build_data_freshness(
            latest_trade_date=latest_trade_date,
            indicator_trade_date=(latest_indicator_snapshot or {}).get("trade_date"),
            pattern_trade_date=(recent_patterns or {}).get("latest_trade_date"),
        )
        stock["validation_context"] = self._build_validation_context(
            latest_bar=latest_bar,
            latest_indicator_snapshot=latest_indicator_snapshot,
            recent_patterns=recent_patterns,
        )

        requested_adjust = adjust.lower()
        stock["adjust_requested"] = requested_adjust
        stock["adjust_applied"] = requested_adjust
        stock["adjust_note"] = None

        if start_date and end_date:
            adjust_type = self._parse_adjust(adjust)
            if adjust_type == AdjustType.NO_ADJUST:
                stock["bars"] = await self._query_bars_from_db(
                    ts_code=internal_ts_code,
                    start_date=start_date,
                    end_date=end_date,
                )
            else:
                adjusted_bars = await self._fetch_adjusted_bars(
                    symbol=stock["symbol"],
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust_type,
                )
                if adjusted_bars:
                    stock["bars"] = adjusted_bars
                else:
                    stock["bars"] = await self._query_bars_from_db(
                        ts_code=internal_ts_code,
                        start_date=start_date,
                        end_date=end_date,
                    )
                    stock["adjust_applied"] = "bfq"
                    stock["adjust_note"] = "requested_adjust_data_unavailable_fallback_to_bfq"

        return normalize_stock_payload(stock)

    async def get_etf_list(self, date: str | None, page: int, page_size: int) -> list[dict]:
        offset = (page - 1) * page_size
        date_dt = trade_date_dt_param(date)

        if date:
            query = text("""
                SELECT
                    s.symbol as code,
                    s.ts_code,
                    s.symbol,
                    s.exchange,
                    s.name,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                LEFT JOIN daily_bars db
                    ON s.ts_code = db.ts_code
                    AND (db.trade_date_dt = :date_dt OR (db.trade_date_dt IS NULL AND db.trade_date = :date))
                WHERE s.is_etf = true AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
        else:
            query = text("""
                SELECT
                    s.symbol as code,
                    s.ts_code,
                    s.symbol,
                    s.exchange,
                    s.name,
                    db.trade_date as date,
                    db.open,
                    db.high,
                    db.low,
                    db.close,
                    db.pre_close,
                    db.pct_chg as change_rate,
                    db.vol,
                    db.amount
                FROM stocks s
                LEFT JOIN daily_bars db ON s.ts_code = db.ts_code
                WHERE s.is_etf = true AND s.list_status = 'L'
                ORDER BY
                    CASE WHEN db.trade_date_dt IS NULL THEN 1 ELSE 0 END,
                    db.trade_date_dt DESC,
                    db.trade_date DESC,
                    db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)

        result = await self.db.execute(
            query, {"date": date, "date_dt": date_dt, "limit": page_size, "offset": offset}
        )
        return [self._normalize_row_mapping(row._mapping) for row in result.fetchall()]

    async def get_etf_detail(self, code: str) -> dict | None:
        candidates = build_code_variants(code)
        symbol = extract_symbol(code)
        query = text("""
            SELECT *
            FROM stocks
            WHERE is_etf = true
              AND (
                symbol = :symbol
                OR ts_code = :code
                OR ts_code = :code_sh
                OR ts_code = :code_sz
                OR ts_code = :code_bj
                OR ts_code = :code_sse
                OR ts_code = :code_szse
                OR ts_code = :code_bse
              )
        """)
        result = await self.db.execute(
            query,
            {
                "symbol": symbol,
                "code": code,
                "code_sh": next((item for item in candidates if item.endswith(".SH")), ""),
                "code_sz": next((item for item in candidates if item.endswith(".SZ")), ""),
                "code_bj": next((item for item in candidates if item.endswith(".BJ")), ""),
                "code_sse": next((item for item in candidates if item.endswith(".SSE")), ""),
                "code_szse": next((item for item in candidates if item.endswith(".SZSE")), ""),
                "code_bse": next((item for item in candidates if item.endswith(".BSE")), ""),
            },
        )
        row = result.fetchone()
        return normalize_stock_payload(dict(row._mapping)) if row else None

    async def get_stock_count(self, is_etf: bool = False) -> int:
        query = text(
            "SELECT COUNT(*) as count FROM stocks WHERE is_etf = :is_etf AND list_status = 'L'"
        )
        result = await self.db.execute(query, {"is_etf": is_etf})
        row = result.fetchone()
        return row[0] if row else 0
