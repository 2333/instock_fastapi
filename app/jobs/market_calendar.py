import asyncio
import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from core.crawling.baostock_provider import BaoStockProvider

logger = logging.getLogger(__name__)

MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")


def current_market_date(reference: datetime | None = None) -> date:
    current = reference.astimezone(MARKET_TIMEZONE) if reference else datetime.now(MARKET_TIMEZONE)
    return current.date()


def format_trade_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def should_force_run_market_tasks() -> bool:
    return os.getenv("MARKET_TASK_FORCE_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


def market_calendar_timeout_seconds() -> float:
    return max(0.01, float(os.getenv("MARKET_CALENDAR_TIMEOUT_SECONDS", "15")))


def should_skip_market_task(task_name: str, *, today_is_trading_day: bool) -> bool:
    if today_is_trading_day:
        return False

    if should_force_run_market_tasks():
        logger.warning("%s 遇到非交易日，但已启用强制执行", task_name)
        return False

    logger.info("%s 跳过执行: 今天不是交易日", task_name)
    return True


async def is_trading_day(
    target_date: date | None = None,
    *,
    provider: BaoStockProvider | None = None,
) -> bool:
    day = target_date or current_market_date()
    if day.weekday() >= 5:
        return False

    active_provider = provider or BaoStockProvider()

    try:
        calendar = await asyncio.wait_for(
            active_provider.fetch_trade_calendar(
                start_date=day.isoformat(),
                end_date=day.isoformat(),
            ),
            timeout=market_calendar_timeout_seconds(),
        )
        if calendar:
            return bool(calendar[0].get("is_trading"))
    except TimeoutError:
        logger.warning("BaoStock 交易日历获取超时，按非交易日处理: date=%s", day.isoformat())
        return False
    except Exception as exc:
        logger.warning("BaoStock 交易日历获取失败，按非交易日处理: %s", exc)
        return False

    logger.warning("BaoStock 交易日历为空，按非交易日处理: date=%s", day.isoformat())
    return False
