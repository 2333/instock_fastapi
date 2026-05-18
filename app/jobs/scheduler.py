import logging
import os
from datetime import datetime, time
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from app.database import async_session_factory
from app.jobs.market_calendar import MARKET_TIMEZONE, current_market_date, format_trade_date, is_trading_day

try:
    import fcntl  # type: ignore
except Exception:  # pragma: no cover - non-POSIX fallback
    fcntl = None  # type: ignore

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Shanghai"))
_scheduler_lock_handle: object | None = None

# BaoStock update schedule:
# - current trading day 17:30: daily K-lines complete
# - current trading day 18:00: adjust factors complete
# - current trading day 20:00: minute K-lines complete
# - every Monday afternoon: index constituent/weekly datasets refresh
# We start the root daily sync shortly after 17:30, then leave wider gaps for
# downstream local-compute jobs because fetch_daily_data itself needs time to
# finish a full-market run.
FETCH_DAILY_DATA_TIME = time(hour=17, minute=40)
FETCH_STOCK_UNIVERSE_TIME = time(hour=17, minute=35)
FETCH_STOCK_CLASSIFICATION_TIME = time(hour=17, minute=50)
FETCH_FUND_FLOW_TIME = time(hour=16, minute=0)
CALCULATE_INDICATORS_TIME = time(hour=19, minute=10)
RUN_PATTERN_RECOGNITION_TIME = time(hour=19, minute=40)
RUN_STRATEGY_SELECTION_TIME = time(hour=20, minute=10)
RUN_POST_CLOSE_ALERTS_TIME = time(hour=20, minute=25)
FETCH_MARKET_REFERENCE_TIME = time(hour=21, minute=45)


MarketJobRunner = Callable[[], Awaitable[None]]


def _normalize_trade_date_value(trade_date: str | None) -> str | None:
    if trade_date is None:
        return None
    normalized = trade_date.replace("-", "").strip()
    return normalized or None


def should_recover_market_job(
    *,
    now: datetime,
    scheduled_time: time,
    today_trade_date: str,
    latest_trade_dates: list[str | None],
    today_is_trading_day: bool,
    has_partial_gap: bool = False,
) -> bool:
    if not today_is_trading_day:
        return False

    scheduled_at = datetime.combine(now.date(), scheduled_time, tzinfo=now.tzinfo)
    if now < scheduled_at:
        return False

    normalized_today_trade_date = _normalize_trade_date_value(today_trade_date)
    normalized_latest_trade_dates = [_normalize_trade_date_value(latest_date) for latest_date in latest_trade_dates]

    return has_partial_gap or any(
        latest_date != normalized_today_trade_date for latest_date in normalized_latest_trade_dates
    )


async def _get_latest_trade_dates(table_names: tuple[str, ...]) -> dict[str, str | None]:
    latest_dates: dict[str, str | None] = {}

    async with async_session_factory() as session:
        for table_name in table_names:
            result = await session.execute(text(f"SELECT MAX(trade_date) FROM {table_name}"))
            latest_dates[table_name] = result.scalar_one_or_none()

    return latest_dates


async def _get_daily_bar_coverage_status(trade_date: str) -> dict[str, int | bool]:
    query = text(
        """
        WITH supported_active_universe AS (
            SELECT s.ts_code
            FROM stocks s
            WHERE s.list_status = 'L'
              AND COALESCE(s.is_etf, FALSE) = FALSE
              AND (
                    UPPER(COALESCE(s.exchange, '')) IN ('SH', 'SZ', 'SSE', 'SHSE', 'SZSE')
                    OR s.ts_code LIKE '%.SH'
                    OR s.ts_code LIKE '%.SZ'
                    OR s.ts_code LIKE '%.SSE'
                    OR s.ts_code LIKE '%.SHSE'
                    OR s.ts_code LIKE '%.SZSE'
                  )
              AND REPLACE(COALESCE(NULLIF(s.list_date, ''), '19000101'), '-', '')
                    <= REPLACE(:trade_date, '-', '')
              AND REPLACE(COALESCE(NULLIF(s.delist_date, ''), '99991231'), '-', '')
                    >= REPLACE(:trade_date, '-', '')
        )
        SELECT
            (SELECT COUNT(*) FROM supported_active_universe) AS expected_count,
            (
                SELECT COUNT(DISTINCT db.ts_code)
                FROM daily_bars db
                JOIN supported_active_universe u ON u.ts_code = db.ts_code
                WHERE REPLACE(COALESCE(db.trade_date, ''), '-', '') = REPLACE(:trade_date, '-', '')
            ) AS covered_count
        """
    )

    async with async_session_factory() as session:
        row = (await session.execute(query, {"trade_date": trade_date})).mappings().one()

    expected_count = int(row["expected_count"] or 0)
    covered_count = int(row["covered_count"] or 0)
    return {
        "expected_count": expected_count,
        "covered_count": covered_count,
        "has_partial_gap": expected_count > covered_count,
    }


async def recover_missed_market_jobs() -> None:
    from app.jobs.tasks.fetch_daily_task import run as run_daily_task
    from app.jobs.tasks.fetch_fund_flow_task import run as run_fund_flow_task
    from app.jobs.tasks.fetch_market_reference_task import run as run_market_reference_task

    now = datetime.now(MARKET_TIMEZONE)
    today = format_trade_date(current_market_date(now))
    normalized_today = _normalize_trade_date_value(today)
    today_is_trading_day = await is_trading_day(target_date=current_market_date(now))
    recovery_jobs: tuple[tuple[str, time, tuple[str, ...], MarketJobRunner], ...] = (
        ("fetch_daily_data", FETCH_DAILY_DATA_TIME, ("daily_bars",), run_daily_task),
        ("fetch_fund_flow", FETCH_FUND_FLOW_TIME, ("fund_flows",), run_fund_flow_task),
        (
            "fetch_market_reference",
            FETCH_MARKET_REFERENCE_TIME,
            ("stock_tops", "stock_block_trades"),
            run_market_reference_task,
        ),
    )

    for job_id, scheduled_time, table_names, runner in recovery_jobs:
        latest_dates = await _get_latest_trade_dates(table_names)
        daily_bar_coverage_status: dict[str, int | bool] | None = None
        if (
            job_id == "fetch_daily_data"
            and _normalize_trade_date_value(latest_dates.get("daily_bars")) == normalized_today
        ):
            daily_bar_coverage_status = await _get_daily_bar_coverage_status(today)

        if not should_recover_market_job(
            now=now,
            scheduled_time=scheduled_time,
            today_trade_date=today,
            latest_trade_dates=list(latest_dates.values()),
            today_is_trading_day=today_is_trading_day,
            has_partial_gap=bool(daily_bar_coverage_status and daily_bar_coverage_status["has_partial_gap"]),
        ):
            continue

        coverage_log = ""
        if daily_bar_coverage_status:
            coverage_log = (
                f", coverage={daily_bar_coverage_status['covered_count']}/"
                f"{daily_bar_coverage_status['expected_count']}"
            )
        logger.warning(
            "检测到错过的市场任务，立即补跑 %s: latest=%s, target=%s%s",
            job_id,
            latest_dates,
            today,
            coverage_log,
        )
        try:
            await runner()
        except Exception:
            logger.exception("启动补偿任务失败: %s", job_id)


async def recover_missed_alert_subscriptions() -> None:
    from app.jobs.tasks.alert_subscription_task import has_due_post_close_runs, run as run_alert_subscriptions

    now = datetime.now(MARKET_TIMEZONE)
    today = format_trade_date(current_market_date(now))
    today_is_trading_day = await is_trading_day(target_date=current_market_date(now))
    scheduled_at = datetime.combine(now.date(), RUN_POST_CLOSE_ALERTS_TIME, tzinfo=now.tzinfo)

    if not today_is_trading_day or now < scheduled_at:
        return
    if not await has_due_post_close_runs(today):
        return

    logger.warning("检测到错过的盘后告警订阅任务，立即补跑: target=%s", today)
    try:
        await run_alert_subscriptions(date=today)
    except Exception:
        logger.exception("启动盘后告警订阅补偿任务失败")


async def recover_missed_jobs() -> None:
    await recover_missed_market_jobs()
    await recover_missed_alert_subscriptions()


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
        trigger=CronTrigger(
            hour=FETCH_DAILY_DATA_TIME.hour,
            minute=FETCH_DAILY_DATA_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="每日数据抓取",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        id="fetch_stock_universe",
        func="app.jobs.tasks.fetch_daily_task:run_stock_universe_refresh",
        trigger=CronTrigger(
            hour=FETCH_STOCK_UNIVERSE_TIME.hour,
            minute=FETCH_STOCK_UNIVERSE_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="股票主数据同步",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        id="fetch_stock_classification",
        func="app.jobs.tasks.fetch_daily_task:run_stock_classification_refresh",
        trigger=CronTrigger(
            hour=FETCH_STOCK_CLASSIFICATION_TIME.hour,
            minute=FETCH_STOCK_CLASSIFICATION_TIME.minute,
            day_of_week="mon",
        ),
        name="股票分类同步",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
    )
    scheduler.add_job(
        id="fetch_fund_flow",
        func="app.jobs.tasks.fetch_fund_flow_task:run",
        trigger=CronTrigger(
            hour=FETCH_FUND_FLOW_TIME.hour,
            minute=FETCH_FUND_FLOW_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="资金流向抓取",
        max_instances=1,
    )
    scheduler.add_job(
        id="fetch_market_reference",
        func="app.jobs.tasks.fetch_market_reference_task:run",
        trigger=CronTrigger(
            hour=FETCH_MARKET_REFERENCE_TIME.hour,
            minute=FETCH_MARKET_REFERENCE_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="龙虎榜与大宗交易",
        max_instances=1,
    )
    scheduler.add_job(
        id="calculate_indicators",
        func="app.jobs.tasks.indicator_task:run",
        trigger=CronTrigger(
            hour=CALCULATE_INDICATORS_TIME.hour,
            minute=CALCULATE_INDICATORS_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="指标计算",
        max_instances=1,
    )
    scheduler.add_job(
        id="run_pattern_recognition",
        func="app.jobs.tasks.pattern_task:run",
        trigger=CronTrigger(
            hour=RUN_PATTERN_RECOGNITION_TIME.hour,
            minute=RUN_PATTERN_RECOGNITION_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="形态识别",
        max_instances=1,
    )
    scheduler.add_job(
        id="run_strategy_selection",
        func="app.jobs.tasks.strategy_task:run",
        trigger=CronTrigger(
            hour=RUN_STRATEGY_SELECTION_TIME.hour,
            minute=RUN_STRATEGY_SELECTION_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="策略选股",
        max_instances=1,
    )
    scheduler.add_job(
        id="run_post_close_alerts",
        func="app.jobs.tasks.alert_subscription_task:run",
        trigger=CronTrigger(
            hour=RUN_POST_CLOSE_ALERTS_TIME.hour,
            minute=RUN_POST_CLOSE_ALERTS_TIME.minute,
            day_of_week="mon-fri",
        ),
        name="告警订阅盘后检查",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=1800,
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
