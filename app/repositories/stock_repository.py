from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import Stock as StockModel
from app.schemas.stock_schema import StockListResponse, StockResponse
from app.utils.stock_codes import normalize_exchange_name


class StockRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        exchange: str | None = None,
        market: str | None = None,
        industry: str | None = None,
        is_etf: bool | None = None,
    ) -> StockListResponse:
        query = select(StockModel)

        if exchange:
            query = query.where(StockModel.exchange == normalize_exchange_name(exchange))
        if market:
            query = query.where(StockModel.market == market)
        if industry:
            query = query.where(StockModel.industry == industry)
        if is_etf is not None:
            query = query.where(StockModel.is_etf == is_etf)

        total_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(total_query)
        total = total_result.scalar()

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(query)
        stocks = result.scalars().all()

        return StockListResponse(
            data=[StockResponse.model_validate(stock) for stock in stocks],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_by_ts_code(self, ts_code: str) -> StockModel | None:
        result = await self.session.execute(select(StockModel).where(StockModel.ts_code == ts_code))
        return result.scalar_one_or_none()

    async def get_by_symbol(self, symbol: str) -> StockModel | None:
        result = await self.session.execute(select(StockModel).where(StockModel.symbol == symbol))
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str, limit: int = 20) -> list[StockModel]:
        result = await self.session.execute(
            select(StockModel).where(StockModel.name.like(f"%{name}%")).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, stock: StockModel) -> StockModel:
        self.session.add(stock)
        await self.session.flush()
        await self.session.refresh(stock)
        return stock

    async def bulk_create(self, stocks: list[StockModel]) -> list[StockModel]:
        self.session.add_all(stocks)
        await self.session.flush()
        return stocks

    async def update(self, stock: StockModel) -> StockModel:
        await self.session.flush()
        await self.session.refresh(stock)
        return stock

    async def delete(self, ts_code: str) -> bool:
        stock = await self.get_by_ts_code(ts_code)
        if stock:
            await self.session.delete(stock)
            await self.session.flush()
            return True
        return False
