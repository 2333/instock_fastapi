from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.schemas.pattern_schema import PatternResponse
from app.services.pattern_service import PatternService

router = APIRouter()


@router.get("/patterns", response_model=List[PatternResponse])
async def get_patterns(
    code: str = Query(..., description="股票代码"),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    service = PatternService(db)
    return await service.get_patterns(code, start_date, end_date, limit)


@router.get("/patterns/today")
async def get_today_patterns(
    signal: Optional[str] = Query(None, description="信号类型: buy/sell/hold"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    service = PatternService(db)
    return await service.get_today_patterns(signal, limit)
