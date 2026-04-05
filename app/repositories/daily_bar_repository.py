from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import DailyBar as DailyBarModel
from app.schemas.stock_schema import DailyBarListResponse, DailyBarResponse


class DailyBarRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

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

        if start_date:
            query = query.where(DailyBarModel.trade_date >= start_date)
        if end_date:
            query = query.where(DailyBarModel.trade_date <= end_date)

        if order == "desc":
            query = query.order_by(desc(DailyBarModel.trade_date))
        else:
            query = query.order_by(DailyBarModel.trade_date)

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
            .order_by(desc(DailyBarModel.trade_date))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_bar_by_date(self, ts_code: str, trade_date: str) -> DailyBarModel | None:
        result = await self.session.execute(
            select(DailyBarModel).where(
                and_(
                    DailyBarModel.ts_code == ts_code,
                    DailyBarModel.trade_date == trade_date,
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
        result = await self.session.execute(
            select(DailyBarModel)
            .where(DailyBarModel.trade_date == trade_date)
            .order_by(desc(DailyBarModel.pct_chg))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_top_losers(
        self,
        trade_date: str,
        limit: int = 20,
    ) -> list[DailyBarModel]:
        result = await self.session.execute(
            select(DailyBarModel)
            .where(DailyBarModel.trade_date == trade_date)
            .order_by(DailyBarModel.pct_chg)
            .limit(limit)
        )
        return list(result.scalars().all())
