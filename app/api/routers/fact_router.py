from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.fact_schema import (
    DailyBasicResponse,
    StockSTResponse,
    TechnicalFactorResponse,
)
from app.services.fact_service import FactService

router = APIRouter()


@router.get("/facts/daily-basic", response_model=list[DailyBasicResponse])
async def get_daily_basic(
    code: str | None = Query(None, description="股票代码"),
    date: str | None = Query(None, description="交易日期"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = FactService(db)
    return await service.get_daily_basic(code, date, start_date, end_date, limit)


@router.get("/facts/stock-st", response_model=list[StockSTResponse])
async def get_stock_st(
    code: str | None = Query(None, description="股票代码"),
    date: str | None = Query(None, description="交易日期"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = FactService(db)
    return await service.get_stock_st(code, date, start_date, end_date, limit)


@router.get("/facts/technical-factors", response_model=list[TechnicalFactorResponse])
async def get_technical_factors(
    code: str | None = Query(None, description="股票代码"),
    date: str | None = Query(None, description="交易日期"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = FactService(db)
    return await service.get_technical_factors(code, date, start_date, end_date, limit)
