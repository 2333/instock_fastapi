from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_repository import FactRepository


class FactService:
    def __init__(self, db: AsyncSession):
        self.repo = FactRepository(db)

    async def get_daily_basic(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self.repo.get_daily_basic(code, date, start_date, end_date, limit)

    async def get_stock_st(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self.repo.get_stock_st(code, date, start_date, end_date, limit)

    async def get_technical_factors(
        self,
        code: str | None = None,
        date: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        return await self.repo.get_technical_factors(code, date, start_date, end_date, limit)
