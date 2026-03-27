from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.indicator_schema import IndicatorResponse
from app.services.indicator_service import IndicatorService

router = APIRouter()


@router.get("/indicators", response_model=list[IndicatorResponse])
async def get_indicators(
    code: str = Query(..., description="股票代码"),
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(100, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    service = IndicatorService(db)
    return await service.get_indicators(code, start_date, end_date, limit)


@router.get("/indicators/latest")
async def get_latest_indicator(
    code: str = Query(..., description="股票代码"), db: AsyncSession = Depends(get_db)
):
    service = IndicatorService(db)
    return await service.get_latest_indicator(code)
