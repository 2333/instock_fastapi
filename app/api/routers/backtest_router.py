from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models.stock_model import User
from app.schemas.backtest_schema import BacktestDetailResponse, BacktestHistoryResponse
from app.services.backtest_service import BacktestService
from app.services.backtest_task_service import BacktestTaskService

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


@router.get("/backtest/{backtest_id}", response_model=BacktestDetailResponse)
async def get_backtest_result(
    backtest_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BacktestDetailResponse:
    service = BacktestService(db)
    return await service.get_result(backtest_id, user_id=current_user.id)


# --- 异步回测任务 ---

@router.post("/backtest/async")
async def run_backtest_async(
    params: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """启动后台回测任务，立即返回 task_id"""
    task_service = BacktestTaskService(db)
    task = await task_service.create_task(user_id=current_user.id, params=params)
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "backtest_id": task.backtest_id,
    }


@router.get("/backtest/tasks/{task_id}")
async def get_backtest_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询后台任务状态"""
    task_service = BacktestTaskService(db)
    task = await task_service.get_task(task_id, user_id=current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "backtest_id": task.backtest_id,
        "error_message": task.error_message,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.get("/backtest/tasks")
async def list_backtest_tasks(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """列出最近回测任务"""
    task_service = BacktestTaskService(db)
    tasks = await task_service.list_tasks(user_id=current_user.id, limit=limit)
    return [
        {
            "task_id": t.id,
            "status": t.status,
            "progress": t.progress,
            "backtest_id": t.backtest_id,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]
