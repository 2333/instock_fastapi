from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, and_
from typing import List, Optional, Any
import logging
from app.config import get_settings
from core.crawling.base import AdjustType
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.eastmoney import EastMoneyCrawler

settings = get_settings()
logger = logging.getLogger(__name__)


class StockService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_trade_date(self, target_date: Optional[str]) -> Optional[str]:
        if target_date:
            result = await self.db.execute(
                text(
                    """
                    SELECT MAX(trade_date) AS resolved_date
                    FROM daily_bars
                    WHERE trade_date <= :target_date
                    """
                ),
                {"target_date": target_date},
            )
        else:
            result = await self.db.execute(
                text("SELECT MAX(trade_date) AS resolved_date FROM daily_bars")
            )
        row = result.fetchone()
        return row[0] if row and row[0] else None

    async def get_stocks(self, date: Optional[str], page: int, page_size: int) -> List[dict]:
        offset = (page - 1) * page_size

        # 指定日期若无数据则自动回退到最近一个交易日
        date = await self._resolve_trade_date(date)

        if date:
            query = text("""
                SELECT 
                    s.ts_code as code,
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
                INNER JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = :date
                WHERE s.is_etf = false AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)
        else:
            # 如果没有找到任何交易日的数据，返回股票基本信息
            query = text("""
                SELECT 
                    s.ts_code as code,
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

        result = await self.db.execute(query, {"date": date, "limit": page_size, "offset": offset})
        return [row._mapping for row in result.fetchall()]

    @staticmethod
    def _normalize_date(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        v = value.strip()
        if len(v) == 8 and v.isdigit():
            return f"{v[0:4]}-{v[4:6]}-{v[6:8]}"
        return v.replace("/", "-")

    @staticmethod
    def _parse_adjust(value: Optional[str]) -> AdjustType:
        mapping = {
            "bfq": AdjustType.NO_ADJUST,
            "qfq": AdjustType.FORWARD,
            "hfq": AdjustType.BACKWARD,
        }
        return mapping.get((value or "bfq").lower(), AdjustType.NO_ADJUST)

    async def _fetch_adjusted_bars(
        self,
        symbol: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: AdjustType,
    ) -> List[dict]:
        baostock_provider = BaoStockProvider()
        eastmoney_crawler = EastMoneyCrawler()
        bars: List[dict] = []

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

        normalized: List[dict] = []
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
        self, ts_code: str, start_date: Optional[str], end_date: Optional[str]
    ) -> List[dict]:
        if not (start_date and end_date):
            return []
        bars_query = text("""
            SELECT * FROM daily_bars 
            WHERE ts_code = :ts_code AND trade_date BETWEEN :start_date AND :end_date
            ORDER BY trade_date ASC
        """)
        bars_result = await self.db.execute(
            bars_query,
            {"ts_code": ts_code, "start_date": start_date, "end_date": end_date},
        )
        return [dict(row._mapping) for row in bars_result.fetchall()]

    async def get_stock_detail(
        self, code: str, start_date: Optional[str], end_date: Optional[str], adjust: str = "bfq"
    ) -> Optional[dict]:
        stock_query = text("""
            SELECT * FROM stocks WHERE symbol = :code OR ts_code = :code LIMIT 1
        """)
        result = await self.db.execute(stock_query, {"code": code})
        row = result.fetchone()
        if not row:
            return {"error": "Stock not found", "code": code}

        stock = dict(row._mapping)

        requested_adjust = adjust.lower()
        stock["adjust_requested"] = requested_adjust
        stock["adjust_applied"] = requested_adjust
        stock["adjust_note"] = None

        if start_date and end_date:
            adjust_type = self._parse_adjust(adjust)
            if adjust_type == AdjustType.NO_ADJUST:
                stock["bars"] = await self._query_bars_from_db(
                    ts_code=stock["ts_code"],
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
                        ts_code=stock["ts_code"],
                        start_date=start_date,
                        end_date=end_date,
                    )
                    stock["adjust_applied"] = "bfq"
                    stock["adjust_note"] = "requested_adjust_data_unavailable_fallback_to_bfq"

        return stock

    async def get_etf_list(self, date: Optional[str], page: int, page_size: int) -> List[dict]:
        offset = (page - 1) * page_size

        if date:
            query = text("""
                SELECT 
                    s.ts_code as code,
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
                LEFT JOIN daily_bars db ON s.ts_code = db.ts_code AND db.trade_date = :date
                WHERE s.is_etf = true AND s.list_status = 'L'
                ORDER BY db.pct_chg DESC NULLS LAST
                LIMIT :limit OFFSET :offset
            """)
        else:
            query = text("""
                SELECT 
                    s.ts_code as code,
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
                ORDER BY db.trade_date DESC, db.pct_chg DESC
                LIMIT :limit OFFSET :offset
            """)

        result = await self.db.execute(query, {"date": date, "limit": page_size, "offset": offset})
        return [row._mapping for row in result.fetchall()]

    async def get_etf_detail(self, code: str) -> Optional[dict]:
        query = text("""
            SELECT * FROM stocks WHERE (ts_code = :code OR symbol = :code) AND is_etf = true
        """)
        result = await self.db.execute(query, {"code": code})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def get_stock_count(self, is_etf: bool = False) -> int:
        query = text(
            "SELECT COUNT(*) as count FROM stocks WHERE is_etf = :is_etf AND list_status = 'L'"
        )
        result = await self.db.execute(query, {"is_etf": is_etf})
        row = result.fetchone()
        return row[0] if row else 0
