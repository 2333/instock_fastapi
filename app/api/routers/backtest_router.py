from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from app.database import get_db
from app.services.backtest_service import BacktestService
from app.core.dependencies import get_current_user
from app.models.stock_model import User

router = APIRouter()


@router.post("/backtest")
async def run_backtest(
    params: Dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BacktestService(db)
    return await service.run_backtest(params, user_id=current_user.id)


@router.get("/backtest/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BacktestService(db)
    return await service.get_result(backtest_id, user_id=current_user.id)
