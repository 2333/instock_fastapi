import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import User
from app.schemas.optimization_schema import (
    OptimizationJobCreate,
    OptimizationJobResponse,
    OptimizationProgress,
    OptimizationTrialResponse,
)
from app.services.optimization_service import OptimizationService
from app.core.dependencies import get_current_user
from app.jobs.tasks.optimization_tasks import run_optimization_job

router = APIRouter(prefix="/api/v1/optimization", tags=["optimization"])


# Dependency
async def get_optimization_service() -> OptimizationService:
    async with async_session_factory() as session:
        yield OptimizationService(session)


@router.post("/jobs", response_model=OptimizationJobResponse, status_code=status.HTTP_201_CREATED)
async def create_optimization_job(
    data: OptimizationJobCreate,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """创建参数优化任务"""
    job = await service.create_job(current_user.id, data)
    # 触发异步执行（后台任务）
    asyncio.create_task(run_optimization_job(job.id))
    return OptimizationJobResponse.model_validate(job)


@router.get("/jobs")
async def list_optimization_jobs(
    status: Optional[str] = None,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """列出我的优化任务"""
    jobs = await service.list_jobs(current_user.id, status=status, limit=limit)
    return [OptimizationJobResponse.model_validate(j) for j in jobs]


@router.get("/jobs/{job_id}")
async def get_optimization_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """查询优化任务详情"""
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return OptimizationJobResponse.model_validate(job)


@router.get("/jobs/{job_id}/progress")
async def get_optimization_progress(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """获取优化进度（简化的进度查询）"""
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    progress_pct = (job.completed_trials / job.total_trials * 100) if job.total_trials > 0 else 0
    return {
        "job_id": job_id,
        "status": job.status,
        "completed_trials": job.completed_trials,
        "total_trials": job.total_trials,
        "progress_percent": round(progress_pct, 2),
        "best_score": job.best_score,
        "best_parameters": job.best_parameters,
    }


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_optimization_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """取消优化任务"""
    ok = await service.cancel_job(job_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=400, detail="无法取消该任务（可能已完成或不存在）")
    return None


@router.get("/jobs/{job_id}/trials", response_model=list[OptimizationTrialResponse])
async def get_optimization_trials(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """获取所有试验结果"""
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    trials = await service.get_trials(job_id)
    return [OptimizationTrialResponse.model_validate(t) for t in trials]


@router.get("/jobs/{job_id}/best")
async def get_best_parameters(
    job_id: int,
    current_user: User = Depends(get_current_user),
    service: OptimizationService = Depends(get_optimization_service),
):
    """获取最优参数"""
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")

    if job.status != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    return {
        "parameters": job.best_parameters,
        "score": job.best_score,
        "backtest_result_id": job.best_backtest_result_id,
    }
