from typing import Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.backtest_schema import BacktestHistoryResponse
from app.services.backtest_service import BacktestService

router = APIRouter()


@router.post("/backtest")
async def run_backtest(
    params: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BacktestService(db)
    return await service.run_backtest(params, user_id=current_user.id)


@router.get("/backtest/history", response_model=BacktestHistoryResponse)
async def list_backtest_results(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestHistoryResponse:
    service = BacktestService(db)
    items = await service.list_results(user_id=current_user.id, limit=limit)
    return BacktestHistoryResponse(data=items)


@router.get("/backtest/{backtest_id}")
async def get_backtest_result(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = BacktestService(db)
    return await service.get_result(backtest_id, user_id=current_user.id)
