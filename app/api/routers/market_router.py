from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.database import get_db
from app.services.market_data_service import MarketDataService

router = APIRouter()


@router.get("/market/fund-flow")
async def get_fund_flow_rank(
    date: Optional[str] = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_fund_flow_rank(date, limit)


@router.get("/market/block-trades")
async def get_block_trades(
    date: Optional[str] = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_block_trades(date, limit)


@router.get("/market/lhb")
async def get_lhb(
    date: Optional[str] = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_lhb(date, limit)


@router.get("/market/north-bound")
async def get_north_bound_funds(
    date: Optional[str] = Query(None, description="交易日期"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = MarketDataService(db)
    return await service.get_north_bound_funds(date, limit)
