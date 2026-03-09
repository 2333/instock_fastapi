from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import os
from typing import Optional
from zoneinfo import ZoneInfo

try:
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Shanghai"))
_scheduler_lock_handle: Optional[object] = None


def _acquire_scheduler_lock() -> bool:
    global _scheduler_lock_handle

    if fcntl is None:
        return True

    lock_path = os.getenv("SCHEDULER_LOCK_PATH", "/tmp/instock_scheduler.lock")
    try:
        lock_handle = open(lock_path, "w")
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _scheduler_lock_handle = lock_handle
        return True
    except BlockingIOError:
        return False
    except Exception as exc:
        logger.warning("Scheduler lock error: %s", exc)
        return True


def start_scheduler() -> bool:
    if scheduler.running:
        logger.info("Scheduler already running in current process; skipping start.")
        return True

    if not _acquire_scheduler_lock():
        logger.info("Scheduler already running in another process; skipping start.")
        return False

    scheduler.add_job(
        id="fetch_daily_data",
        func="app.jobs.tasks.fetch_daily_task:run",
        trigger=CronTrigger(hour=15, minute=30),
        name="每日数据抓取",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        id="fetch_fund_flow",
        func="app.jobs.tasks.fetch_fund_flow_task:run",
        trigger=CronTrigger(hour=16, minute=0),
        name="资金流向抓取",
        max_instances=1,
    )
    scheduler.add_job(
        id="calculate_indicators",
        func="app.jobs.tasks.indicator_task:run",
        trigger=CronTrigger(hour=17, minute=0),
        name="指标计算",
        max_instances=1,
    )
    scheduler.add_job(
        id="run_pattern_recognition",
        func="app.jobs.tasks.pattern_task:run",
        trigger=CronTrigger(hour=17, minute=30),
        name="形态识别",
        max_instances=1,
    )
    scheduler.add_job(
        id="run_strategy_selection",
        func="app.jobs.tasks.strategy_task:run",
        trigger=CronTrigger(hour=18, minute=0),
        name="策略选股",
        max_instances=1,
    )
    scheduler.add_job(
        id="cleanup_old_data",
        func="app.jobs.tasks.cleanup_task:run",
        trigger=CronTrigger(hour=3, minute=0, day_of_week="sun"),
        name="数据清理",
        max_instances=1,
    )
    scheduler.start()
    logger.info("定时任务调度器已启动")
    return True


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
    global _scheduler_lock_handle
    if _scheduler_lock_handle is not None:
        try:
            _scheduler_lock_handle.close()
        finally:
            _scheduler_lock_handle = None
    logger.info("定时任务调度器已停止")
