import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.optimization_models import ParameterOptimizationJob, ParameterOptimizationTrial
from app.schemas.optimization_schema import OptimizationJobCreate, OptimizationJobResponse, OptimizationProgress
from app.optimization.algorithms import create_optimizer, Trial

logger = logging.getLogger(__name__)


class OptimizationService:
    """参数优化服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        user_id: int,
        data: OptimizationJobCreate,
    ) -> ParameterOptimizationJob:
        """创建优化任务"""
        job = ParameterOptimizationJob(
            user_id=user_id,
            strategy_type=data.strategy_type,
            parameter_space=data.parameter_space,
            optimization_method=data.optimization_method,
            objective_metric=data.objective_metric,
            total_trials=data.total_trials,
            max_parallel=data.max_parallel,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: int, user_id: Optional[int] = None) -> Optional[ParameterOptimizationJob]:
        """查询优化任务"""
        stmt = select(ParameterOptimizationJob).where(ParameterOptimizationJob.id == job_id)
        if user_id is not None:
            stmt = stmt.where(ParameterOptimizationJob.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        user_id: int,
        status: Optional[str] = None,
        limit: int = 20,
    ) -> List[ParameterOptimizationJob]:
        """列出用户的优化任务"""
        stmt = (
            select(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.user_id == user_id)
            .order_by(ParameterOptimizationJob.created_at.desc())
            .limit(limit)
        )
        if status:
            stmt = stmt.where(ParameterOptimizationJob.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_job_progress(
        self,
        job_id: int,
        completed_trials: int,
        best_score: Optional[float] = None,
        best_params: Optional[Dict[str, Any]] = None,
    ):
        """更新任务进度"""
        values = {"completed_trials": completed_trials}
        if best_score is not None:
            values["best_score"] = best_score
        if best_params is not None:
            values["best_parameters"] = best_params

        await self.db.execute(
            update(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.id == job_id)
            .values(**values)
        )
        await self.db.flush()

    async def mark_job_running(self, job_id: int):
        """标记任务开始运行"""
        await self.db.execute(
            update(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.id == job_id)
            .values(status="running", started_at=datetime.utcnow())
        )
        await self.db.flush()

    async def mark_job_completed(
        self,
        job_id: int,
        best_parameters: Dict[str, Any],
        best_score: float,
        best_backtest_result_id: Optional[int] = None,
    ):
        """标记任务完成"""
        await self.db.execute(
            update(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.id == job_id)
            .values(
                status="completed",
                completed_at=datetime.utcnow(),
                best_parameters=best_parameters,
                best_score=best_score,
                best_backtest_result_id=best_backtest_result_id,
            )
        )
        await self.db.flush()

    async def mark_job_failed(self, job_id: int, error_message: str):
        """标记任务失败"""
        await self.db.execute(
            update(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.id == job_id)
            .values(status="failed", error_message=error_message, completed_at=datetime.utcnow())
        )
        await self.db.flush()

    async def cancel_job(self, job_id: int, user_id: int) -> bool:
        """取消任务"""
        job = await self.get_job(job_id, user_id)
        if not job or job.status not in ("pending", "running"):
            return False

        await self.db.execute(
            update(ParameterOptimizationJob)
            .where(ParameterOptimizationJob.id == job_id)
            .values(status="cancelled", completed_at=datetime.utcnow())
        )
        await self.db.flush()
        return True

    async def create_trial(
        self,
        job_id: int,
        parameters: Dict[str, Any],
    ) -> ParameterOptimizationTrial:
        """创建试验记录"""
        trial = ParameterOptimizationTrial(
            job_id=job_id,
            parameters=parameters,
        )
        self.db.add(trial)
        await self.db.flush()
        await self.db.refresh(trial)
        return trial

    async def update_trial_result(
        self,
        trial_id: int,
        score: float,
        metrics: Optional[Dict[str, Any]] = None,
        backtest_result_id: Optional[int] = None,
    ):
        """更新试验结果"""
        await self.db.execute(
            update(ParameterOptimizationTrial)
            .where(ParameterOptimizationTrial.id == trial_id)
            .values(
                score=score,
                metrics=metrics,
                backtest_result_id=backtest_result_id,
                status="completed",
                completed_at=datetime.utcnow(),
            )
        )
        await self.db.flush()

    async def get_trials(self, job_id: int) -> List[ParameterOptimizationTrial]:
        """获取任务的所有试验"""
        result = await self.db.execute(
            select(ParameterOptimizationTrial)
            .where(ParameterOptimizationTrial.job_id == job_id)
            .order_by(ParameterOptimizationTrial.id.asc())
        )
        return list(result.scalars().all())

    async def get_progress(self, job_id: int) -> Optional[OptimizationProgress]:
        """获取任务进度"""
        job = await self.get_job(job_id)
        if not job:
            return None

        progress_pct = (job.completed_trials / job.total_trials * 100) if job.total_trials > 0 else 0
        return OptimizationProgress(
            job_id=job_id,
            status=job.status,
            completed_trials=job.completed_trials,
            total_trials=job.total_trials,
            progress_percent=progress_pct,
            best_score=job.best_score,
            best_parameters=job.best_parameters,
        )


# 全局服务实例（用于 Celery 任务）
_global_session = None

def get_optimization_service() -> OptimizationService:
    """获取服务实例（用于异步任务）"""
    async def _get_service():
        async with async_session_factory() as session:
            return OptimizationService(session)
    return _get_service()
