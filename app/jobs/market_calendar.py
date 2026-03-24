import logging
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

from core.crawling.tushare_provider import TushareProvider
from core.crawling.eastmoney import EastMoneyCrawler

logger = logging.getLogger(__name__)

MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")


def current_market_date(reference: datetime | None = None) -> date:
    current = reference.astimezone(MARKET_TIMEZONE) if reference else datetime.now(MARKET_TIMEZONE)
    return current.date()


def format_trade_date(value: date) -> str:
    return value.strftime("%Y%m%d")


def should_force_run_market_tasks() -> bool:
    return os.getenv("MARKET_TASK_FORCE_RUN", "").strip().lower() in {"1", "true", "yes", "on"}


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
    crawler: EastMoneyCrawler | None = None,
) -> bool:
    day = target_date or current_market_date()
    if day.weekday() >= 5:
        return False

    tushare_provider = TushareProvider()
    if tushare_provider.token:
        try:
            return await tushare_provider.is_trade_date(format_trade_date(day))
        except Exception as exc:
            logger.warning("Tushare 交易日历获取失败，回退到 EastMoney/工作日判断: %s", exc)

    own_crawler = crawler is None
    active_crawler = crawler or EastMoneyCrawler()

    try:
        calendar = await active_crawler.fetch_trade_calendar(
            start_date=day.isoformat(),
            end_date=day.isoformat(),
        )
        if calendar:
            return bool(calendar[0].get("is_trading"))
    except Exception as exc:
        logger.warning("交易日历获取失败，退化为工作日判断: %s", exc)
    finally:
        if own_crawler:
            await active_crawler.close()

    return True
