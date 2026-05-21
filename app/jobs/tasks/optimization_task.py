"""In-process parameter optimization task runner."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from app.database import async_session_factory
from app.models.stock_model import ParameterOptimizationJob
from app.services.optimization_service import OptimizationService

logger = logging.getLogger(__name__)

_background_tasks: set[asyncio.Task] = set()


def schedule_optimization_job(job_id: int) -> asyncio.Task:
    task = asyncio.create_task(run_optimization_job(job_id))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def run_optimization_job(job_id: int) -> None:
    async with async_session_factory() as db:
        service = OptimizationService(db)
        try:
            await service.run_job(job_id=job_id)
        except Exception as exc:
            logger.exception("Parameter optimization job %d failed", job_id)
            await db.rollback()
            await mark_optimization_job_failed(job_id, str(exc))


async def mark_optimization_job_failed(job_id: int, message: str) -> None:
    async with async_session_factory() as db:
        job = await db.get(ParameterOptimizationJob, job_id)
        if job is None or job.status in {"completed", "failed", "cancelled"}:
            return
        job.status = "failed"
        job.progress = 100
        job.error_message = message
        job.completed_at = datetime.utcnow()
        await db.commit()
