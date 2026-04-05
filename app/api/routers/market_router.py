from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.market_schema import MarketSummaryResponse, MarketTaskHealthResponse
from app.services.market_data_service import MarketDataService

router = APIRouter()


@router.get("/market/summary", response_model=MarketSummaryResponse)
async def get_market_summary(
    db: AsyncSession = Depends(get_db),
) -> MarketSummaryResponse:
    service = MarketDataService(db)
    return await service.get_summary()


@router.get("/market/fund-flow")
async def get_fund_flow_rank(
    date: str | None = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_fund_flow_rank(date, limit)


@router.get("/market/block-trades")
async def get_block_trades(
    date: str | None = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_block_trades(date, limit)


@router.get("/market/lhb")
async def get_lhb(
    date: str | None = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_lhb(date, limit)


@router.get("/market/north-bound")
async def get_north_bound_funds(
    date: str | None = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_north_bound_funds(date, limit)


@router.get("/market/task-health", response_model=MarketTaskHealthResponse)
async def get_task_health(
    alert_limit: int = Query(10, ge=1, le=50, description="返回的未恢复告警条数"),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_task_health(alert_limit)
