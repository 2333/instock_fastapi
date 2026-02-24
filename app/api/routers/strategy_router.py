from fastapi import APIRouter, Depends, Query, Body, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from app.database import get_db
from app.schemas.strategy_schema import StrategyResponse, StrategyResultResponse
from app.services.strategy_service import StrategyService
from pydantic import BaseModel

router = APIRouter()

class StrategyRunRequest(BaseModel):
    strategy: Optional[str] = None
    date: Optional[str] = None


@router.get("/strategies", response_model=List[StrategyResponse])
async def get_strategies():
    return StrategyService.get_strategy_list()


@router.post("/strategies/run")
async def run_strategy(
    strategy_name: Optional[str] = Query(None, description="策略名称"),
    date: Optional[str] = Query(None),
    payload: Optional[StrategyRunRequest] = Body(None),
    db: AsyncSession = Depends(get_db),
):
    service = StrategyService(db)
    resolved_strategy = (
        payload.strategy if payload and payload.strategy else strategy_name
    )
    resolved_date = payload.date if payload and payload.date else date
    if not resolved_strategy:
        raise HTTPException(status_code=400, detail="strategy is required")
    return await service.run_strategy(resolved_strategy, resolved_date)


@router.get("/strategies/results", response_model=List[StrategyResultResponse])
async def get_strategy_results(
    strategy: Optional[str] = Query(None),
    strategy_name: Optional[str] = Query(None),
    date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    service = StrategyService(db)
    resolved_strategy = strategy or strategy_name
    return await service.get_results(resolved_strategy, date, limit)
