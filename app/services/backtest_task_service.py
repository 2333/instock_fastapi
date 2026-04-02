import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stock_model import BacktestTask
from app.services.backtest_service import BacktestService

logger = logging.getLogger(__name__)

# 后台任务registry（简化版：使用asyncio.create_task）
_background_tasks: set[asyncio.Task] = set()


async def run_backtest_task(task_id: int, db: AsyncSession, params: dict[str, Any], user_id: int) -> None:
    """后台执行回测任务，更新任务状态与进度"""
    service = BacktestService(db)

    try:
        # 标记开始
        stmt = (
            update(BacktestTask)
            .where(BacktestTask.id == task_id)
            .values(status="running", started_at=datetime.utcnow(), progress=5)
        )
        await db.execute(stmt)
        await db.commit()

        # 执行回测（带进度回调）
        result = await service.run_backtest_async(params, user_id=user_id, progress_callback=lambda p: asyncio.create_task(_update_progress(db, task_id, p)))

        # 完成后保存 BacktestResult 并关联 task_id
        backtest_id = result.get("backtest_id")
        if backtest_id:
            # 更新任务完成状态
            stmt = (
                update(BacktestTask)
                .where(BacktestTask.id == task_id)
                .values(
                    status="completed",
                    progress=100,
                    backtest_id=backtest_id,
                    completed_at=datetime.utcnow(),
                )
            )
            await db.execute(stmt)
            await db.commit()
            logger.info("Backtest task %d completed, backtest_id=%s", task_id, backtest_id)
        else:
            raise Exception("Backtest completed without backtest_id")

    except Exception as e:
        logger.exception("Backtest task %d failed: %s", task_id, e)
        stmt = (
            update(BacktestTask)
            .where(BacktestTask.id == task_id)
            .values(status="failed", error_message=str(e), completed_at=datetime.utcnow(), progress=100)
        )
        await db.execute(stmt)
        await db.commit()


async def _update_progress(db: AsyncSession, task_id: int, progress: int) -> None:
    """异步更新任务进度（不阻塞主任务）"""
    try:
        stmt = update(BacktestTask).where(BacktestTask.id == task_id).values(progress=min(progress, 100))
        await db.execute(stmt)
        await db.commit()
    except Exception:
        pass  # 进度更新失败不干扰主流程


class BacktestTaskService:
    """回测任务服务（异步）"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(self, user_id: int, params: dict[str, Any]) -> BacktestTask:
        """创建后台回测任务"""
        task = BacktestTask(user_id=user_id, params=params, status="pending", progress=0)
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)

        # 启动后台 asyncio 任务
        asyncio.create_task(run_backtest_task(task.id, self.db, params, user_id))
        _background_tasks.add(asyncio.current_task())
        return task

    async def get_task(self, task_id: int, user_id: int) -> BacktestTask | None:
        """查询任务状态"""
        stmt = select(BacktestTask).where(BacktestTask.id == task_id, BacktestTask.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(self, user_id: int, limit: int = 10) -> list[BacktestTask]:
        """列出用户最近任务"""
        stmt = (
            select(BacktestTask)
            .where(BacktestTask.user_id == user_id)
            .order_by(BacktestTask.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
