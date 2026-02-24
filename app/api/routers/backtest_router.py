from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from app.database import get_db
from app.services.backtest_service import BacktestService

router = APIRouter()


@router.post("/backtest")
async def run_backtest(
    params: Dict[str, Any] = Body(...), db: AsyncSession = Depends(get_db)
):
    service = BacktestService(db)
    return await service.run_backtest(params)


@router.get("/backtest/{backtest_id}")
async def get_backtest_result(backtest_id: str, db: AsyncSession = Depends(get_db)):
    service = BacktestService(db)
    return await service.get_result(backtest_id)
