import asyncio
import logging
import os
from datetime import datetime, timedelta

from sqlalchemy import text

from app.database import async_session_factory, sync_engine

logger = logging.getLogger(__name__)


def _get_retention_days(env_name: str, default: int) -> int:
    raw = os.getenv(env_name, str(default)).strip()
    try:
        return max(int(raw), 0)
    except ValueError:
        logger.warning("%s=%s 非法，回退默认值 %s", env_name, raw, default)
        return default


DAILY_BAR_RETENTION_DAYS = _get_retention_days("DAILY_BAR_RETENTION_DAYS", 3650)
INDICATOR_RETENTION_DAYS = _get_retention_days("INDICATOR_RETENTION_DAYS", 1095)
PATTERN_RETENTION_DAYS = _get_retention_days("PATTERN_RETENTION_DAYS", 365)
FUND_FLOW_RETENTION_DAYS = _get_retention_days("FUND_FLOW_RETENTION_DAYS", 1095)


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

    def _vacuum_sync() -> None:
        statements = [
            "VACUUM ANALYZE daily_bars",
            "VACUUM ANALYZE indicators",
            "VACUUM ANALYZE patterns",
            "VACUUM ANALYZE fund_flows",
        ]
        with sync_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            for stmt in statements:
                conn.execute(text(stmt))

    try:
        await asyncio.to_thread(_vacuum_sync)
        logger.info("数据库空间清理完成")
    except Exception as e:
        logger.error(f"数据库空间清理失败: {e}", exc_info=True)


async def run():
    """清理任务入口"""
    logger.info(f"执行数据清理任务: {datetime.now()}")
    await cleanup_old_data()
    await vacuum_database()


if __name__ == "__main__":
    asyncio.run(run())
