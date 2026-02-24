import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.stock_model import DailyBar, Indicator, Pattern, FundFlow

logger = logging.getLogger(__name__)

DAILY_BAR_RETENTION_DAYS = 730
INDICATOR_RETENTION_DAYS = 365
PATTERN_RETENTION_DAYS = 180
FUND_FLOW_RETENTION_DAYS = 365


async def cleanup_old_data():
    """清理过期数据"""
    logger.info(f"开始清理过期数据: {datetime.now()}")

    cutoff_date_daily = (datetime.now() - timedelta(days=DAILY_BAR_RETENTION_DAYS)).strftime(
        "%Y%m%d"
    )
    cutoff_date_indicator = (datetime.now() - timedelta(days=INDICATOR_RETENTION_DAYS)).strftime(
        "%Y%m%d"
    )
    cutoff_date_pattern = (datetime.now() - timedelta(days=PATTERN_RETENTION_DAYS)).strftime(
        "%Y%m%d"
    )
    cutoff_date_fundflow = (datetime.now() - timedelta(days=FUND_FLOW_RETENTION_DAYS)).strftime(
        "%Y%m%d"
    )

    async with async_session_factory() as session:
        try:
            result = await session.execute(
                text("DELETE FROM daily_bars WHERE trade_date < :cutoff"),
                {"cutoff": cutoff_date_daily},
            )
            logger.info(f"删除了 {result.rowcount} 条过期日K线数据")

            result = await session.execute(
                text("DELETE FROM indicators WHERE trade_date < :cutoff"),
                {"cutoff": cutoff_date_indicator},
            )
            logger.info(f"删除了 {result.rowcount} 条过期指标数据")

            result = await session.execute(
                text("DELETE FROM patterns WHERE trade_date < :cutoff"),
                {"cutoff": cutoff_date_pattern},
            )
            logger.info(f"删除了 {result.rowcount} 条过期形态数据")

            result = await session.execute(
                text("DELETE FROM fund_flows WHERE trade_date < :cutoff"),
                {"cutoff": cutoff_date_fundflow},
            )
            logger.info(f"删除了 {result.rowcount} 条过期资金流数据")

            await session.commit()
            logger.info("数据清理任务完成")

        except Exception as e:
            logger.error(f"数据清理任务失败: {e}", exc_info=True)
            await session.rollback()


async def vacuum_database():
    """清理数据库空间"""
    logger.info("开始清理数据库空间...")

    async with async_session_factory() as session:
        try:
            await session.execute(text("VACUUM ANALYZE daily_bars"))
            await session.execute(text("VACUUM ANALYZE indicators"))
            await session.execute(text("VACUUM ANALYZE patterns"))
            await session.execute(text("VACUUM ANALYZE fund_flows"))
            await session.commit()
            logger.info("数据库空间清理完成")
        except Exception as e:
            logger.error(f"数据库空间清理失败: {e}", exc_info=True)
            await session.rollback()


async def run():
    """清理任务入口"""
    logger.info(f"执行数据清理任务: {datetime.now()}")
    await cleanup_old_data()
    await vacuum_database()


if __name__ == "__main__":
    asyncio.run(run())
