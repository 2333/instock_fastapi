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
    start_date: Optional[str] = Query(None, description="开始日期 YYYYMMDD"),
    end_date: Optional[str] = Query(None, description="结束日期 YYYYMMDD"),
    min_confidence: float = Query(0, ge=0, le=100),
    pattern_names: Optional[str] = Query(None, description="形态名，逗号分隔"),
    ema_fast: int = Query(12, ge=2, le=120),
    ema_slow: int = Query(26, ge=3, le=250),
    boll_period: int = Query(20, ge=5, le=120),
    boll_std: float = Query(2.0, ge=0.5, le=5.0),
    ema_signal: Optional[str] = Query(None, description="bullish/bearish/neutral"),
    boll_signal: Optional[str] = Query(None, description="breakout/breakdown/inside"),
    indicator_mode: str = Query("all", pattern="^(all|any)$"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    service = PatternService(db)
    names = [item.strip() for item in (pattern_names or "").split(",") if item.strip()]

    if not start_date and not end_date:
        latest_date = await service.get_latest_trade_date()
        if latest_date:
            results = await service.get_composite_patterns(
                signal=signal,
                limit=limit,
                start_date=latest_date,
                end_date=latest_date,
                min_confidence=min_confidence,
                pattern_names=names or None,
                ema_fast=ema_fast,
                ema_slow=ema_slow,
                boll_period=boll_period,
                boll_std=boll_std,
                ema_signal=ema_signal,
                boll_signal=boll_signal,
                indicator_mode=indicator_mode,
            )
            if results:
                return results
        start_date = None
        end_date = None
    return await service.get_composite_patterns(
        signal=signal,
        limit=limit,
        start_date=start_date,
        end_date=end_date,
        min_confidence=min_confidence,
        pattern_names=names or None,
        ema_fast=ema_fast,
        ema_slow=ema_slow,
        boll_period=boll_period,
        boll_std=boll_std,
        ema_signal=ema_signal,
        boll_signal=boll_signal,
        indicator_mode=indicator_mode,
    )
