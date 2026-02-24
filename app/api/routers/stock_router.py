from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.schemas.stock_schema import StockSpotResponse, StockDetailResponse
from app.services.stock_service import StockService

router = APIRouter()


@router.get("/stocks", response_model=List[StockSpotResponse])
async def get_stocks(
    date: Optional[str] = Query(None, description="交易日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = StockService(db)
    return await service.get_stocks(date, page, page_size)


@router.get("/stocks/{code}", response_model=StockDetailResponse)
async def get_stock_detail(
    code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    service = StockService(db)
    return await service.get_stock_detail(code, start_date, end_date)
