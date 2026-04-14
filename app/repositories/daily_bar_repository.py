from datetime import date, datetime

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import DailyBar as DailyBarModel
from app.schemas.stock_schema import DailyBarListResponse, DailyBarResponse


class DailyBarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _parse_trade_date(value: str | None) -> date | None:
        if not value:
            return None
        normalized = value.strip().replace("-", "")
        if len(normalized) != 8 or not normalized.isdigit():
            return None
        return datetime.strptime(normalized, "%Y%m%d").date()

    @staticmethod
    def _normalize_trade_date(value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().replace("-", "")
        if len(normalized) != 8 or not normalized.isdigit():
            return None
        return normalized

    async def get_daily_bars(
        self,
        ts_code: str,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 100,
        order: str = "desc",
    ) -> DailyBarListResponse:
        query = select(DailyBarModel).where(DailyBarModel.ts_code == ts_code)

        start_date_dt = self._parse_trade_date(start_date)
        end_date_dt = self._parse_trade_date(end_date)
        start_date_text = self._normalize_trade_date(start_date)
        end_date_text = self._normalize_trade_date(end_date)

        if start_date_dt and start_date_text:
            query = query.where(
                or_(
                    DailyBarModel.trade_date_dt >= start_date_dt,
                    and_(
                        DailyBarModel.trade_date_dt.is_(None),
                        DailyBarModel.trade_date >= start_date_text,
                    ),
                )
            )
        if end_date_dt and end_date_text:
            query = query.where(
                or_(
                    DailyBarModel.trade_date_dt <= end_date_dt,
                    and_(
                        DailyBarModel.trade_date_dt.is_(None),
                        DailyBarModel.trade_date <= end_date_text,
                    ),
                )
            )

        if order == "desc":
            query = query.order_by(
                DailyBarModel.trade_date_dt.is_(None),
                desc(DailyBarModel.trade_date_dt),
                desc(DailyBarModel.trade_date),
            )
        else:
            query = query.order_by(
                DailyBarModel.trade_date_dt.is_(None),
                DailyBarModel.trade_date_dt,
                DailyBarModel.trade_date,
            )

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(total_query)
        total = total_result.scalar()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        bars = result.scalars().all()

        return DailyBarListResponse(
            data=[DailyBarResponse.model_validate(bar) for bar in bars],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_latest_bar(self, ts_code: str) -> DailyBarModel | None:
        result = await self.session.execute(
            select(DailyBarModel)
            .where(DailyBarModel.ts_code == ts_code)
            .order_by(
                DailyBarModel.trade_date_dt.is_(None),
                desc(DailyBarModel.trade_date_dt),
                desc(DailyBarModel.trade_date),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_bar_by_date(self, ts_code: str, trade_date: str) -> DailyBarModel | None:
        trade_date_dt = self._parse_trade_date(trade_date)
        trade_date_text = self._normalize_trade_date(trade_date)
        result = await self.session.execute(
            select(DailyBarModel).where(
                and_(
                    DailyBarModel.ts_code == ts_code,
                    or_(
                        DailyBarModel.trade_date_dt == trade_date_dt,
                        and_(
                            DailyBarModel.trade_date_dt.is_(None),
                            DailyBarModel.trade_date == trade_date_text,
                        ),
                    ),
                )
            )
        )
        return result.scalar_one_or_none()

    async def create(self, bar: DailyBarModel) -> DailyBarModel:
        self.session.add(bar)
        await self.session.flush()
        await self.session.refresh(bar)
        return bar

    async def bulk_create(self, bars: list[DailyBarModel]) -> list[DailyBarModel]:
        self.session.add_all(bars)
        await self.session.flush()
        return bars

    async def get_top_gainers(
        self,
        trade_date: str,
        limit: int = 20,
    ) -> list[DailyBarModel]:
        trade_date_dt = self._parse_trade_date(trade_date)
        trade_date_text = self._normalize_trade_date(trade_date)
        result = await self.session.execute(
            select(DailyBarModel)
            .where(
                or_(
                    DailyBarModel.trade_date_dt == trade_date_dt,
                    and_(
                        DailyBarModel.trade_date_dt.is_(None),
                        DailyBarModel.trade_date == trade_date_text,
                    ),
                )
            )
            .order_by(desc(DailyBarModel.pct_chg))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_top_losers(
        self,
        trade_date: str,
        limit: int = 20,
    ) -> list[DailyBarModel]:
        trade_date_dt = self._parse_trade_date(trade_date)
        trade_date_text = self._normalize_trade_date(trade_date)
        result = await self.session.execute(
            select(DailyBarModel)
            .where(
                or_(
                    DailyBarModel.trade_date_dt == trade_date_dt,
                    and_(
                        DailyBarModel.trade_date_dt.is_(None),
                        DailyBarModel.trade_date == trade_date_text,
                    ),
                )
            )
            .order_by(DailyBarModel.pct_chg)
            .limit(limit)
        )
        return list(result.scalars().all())
