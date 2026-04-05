from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stock_schema import EtfSpotResponse
from app.services.stock_service import StockService

router = APIRouter()


@router.get("/etf", response_model=list[EtfSpotResponse])
async def get_etf_list(
    date: str | None = Query(None, description="交易日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = StockService(db)
    return await service.get_etf_list(date, page, page_size)


@router.get("/etf/{code}")
async def get_etf_detail(code: str, db: AsyncSession = Depends(get_db)):
    service = StockService(db)
    return await service.get_etf_detail(code)
