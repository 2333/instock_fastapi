from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime

from sqlalchemy import and_, case, desc, false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import DailyBasic, StockST, TechnicalFactor
from app.utils.stock_codes import build_code_variants


class FactRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _parse_trade_date(value: str | None) -> date | None:
        if not value:
            return None
        normalized = value.strip().replace("-", "")
        if len(normalized) != 8 or not normalized.isdigit():
            return None
        try:
            return datetime.strptime(normalized, "%Y%m%d").date()
        except ValueError:
            return None

    @staticmethod
    def _normalize_trade_date(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().replace("-", "")
        if len(normalized) != 8 or not normalized.isdigit():
            return None
        return normalized

    @staticmethod
    def _serialize(model: object) -> dict:
        table = getattr(model, "__table__", None)
        if table is None:
            return {}
        return {column.name: getattr(model, column.name) for column in table.columns}

    @staticmethod
    def _apply_code_filter(query, model, code: str | None):
        if not code:
            return query
        variants = build_code_variants(code)
        if not variants:
            return query
        return query.where(model.ts_code.in_(variants))

    def _apply_date_filter(
        self,
        query,
        model,
        date_value: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ):
        if date_value:
            trade_date_dt = self._parse_trade_date(date_value)
            trade_date_text = self._normalize_trade_date(date_value)
            if trade_date_dt is None or trade_date_text is None:
                return query.where(false())
            query = query.where(
                or_(
                    model.trade_date_dt == trade_date_dt,
                    and_(
                        model.trade_date_dt.is_(None),
                        model.trade_date == trade_date_text,
                    ),
                )
            )

        if start_date:
            start_date_dt = self._parse_trade_date(start_date)
            start_date_text = self._normalize_trade_date(start_date)
            if start_date_dt is None or start_date_text is None:
                return query.where(false())
            query = query.where(
                or_(
                    model.trade_date_dt >= start_date_dt,
                    and_(
                        model.trade_date_dt.is_(None),
                        model.trade_date >= start_date_text,
                    ),
                )
            )

        if end_date:
            end_date_dt = self._parse_trade_date(end_date)
            end_date_text = self._normalize_trade_date(end_date)
            if end_date_dt is None or end_date_text is None:
                return query.where(false())
            query = query.where(
                or_(
                    model.trade_date_dt <= end_date_dt,
                    and_(
                        model.trade_date_dt.is_(None),
                        model.trade_date <= end_date_text,
                    ),
                )
            )

        return query

    @staticmethod
    def _order_by_latest(model):
        return (
            case((model.trade_date_dt.is_(None), 1), else_=0),
            desc(model.trade_date_dt),
            desc(model.trade_date),
        )

    async def _fetch_rows(self, query, limit: int) -> list[dict]:
        result = await self.session.execute(query.limit(limit))
        return [self._serialize(item) for item in result.scalars().all()]

    async def get_daily_basic(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        query = select(DailyBasic)
        query = self._apply_code_filter(query, DailyBasic, code)
        query = self._apply_date_filter(query, DailyBasic, date, start_date, end_date)
        query = query.order_by(*self._order_by_latest(DailyBasic))
        return await self._fetch_rows(query, limit)

    async def get_stock_st(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        query = select(StockST)
        query = self._apply_code_filter(query, StockST, code)
        query = self._apply_date_filter(query, StockST, date, start_date, end_date)
        query = query.order_by(*self._order_by_latest(StockST))
        return await self._fetch_rows(query, limit)

    async def get_technical_factors(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        query = select(TechnicalFactor)
        query = self._apply_code_filter(query, TechnicalFactor, code)
        query = self._apply_date_filter(query, TechnicalFactor, date, start_date, end_date)
        query = query.order_by(*self._order_by_latest(TechnicalFactor))
        return await self._fetch_rows(query, limit)
