from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stock_schema import StockDetailResponse
from app.services.stock_service import StockService

router = APIRouter()


@router.get("/stocks")
async def get_stocks(
    date: str | None = Query(None, description="交易日期"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    service = StockService(db)
    data, total = await service.get_stocks_with_total(date, page, page_size)
    return {"items": data, "total": total, "page": page, "page_size": page_size}


@router.get("/stocks/{code}", response_model=StockDetailResponse)
async def get_stock_detail(
    code: str,
    start_date: str | None = None,
    end_date: str | None = None,
    adjust: str = Query("bfq", description="复权类型: bfq/qfq/hfq"),
    db: AsyncSession = Depends(get_db),
):
    service = StockService(db)
    return await service.get_stock_detail(code, start_date, end_date, adjust)
