import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import DailyBar, Indicator
from core.crawling.eastmoney import EastMoneyCrawler

logger = logging.getLogger(__name__)


async def calculate_indicators(session: AsyncSession, ts_code: str, trade_dates: List[str]):
    """计算技术指标"""
    result = await session.execute(
        select(DailyBar)
        .where(and_(DailyBar.ts_code == ts_code, DailyBar.trade_date.in_(trade_dates)))
        .order_by(DailyBar.trade_date)
    )
    bars = result.scalars().all()

    if len(bars) < 5:
        return

    closes = [float(bar.close) for bar in bars]

    indicators_data = []

    for i, bar in enumerate(bars):
        close = float(bar.close)

        if i >= 4:
            ma5 = sum(closes[i - 4 : i + 1]) / 5
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "indicator_name": "MA5",
                    "indicator_value": Decimal(str(round(ma5, 2))),
                }
            )

        if i >= 9:
            ma10 = sum(closes[i - 9 : i + 1]) / 10
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "indicator_name": "MA10",
                    "indicator_value": Decimal(str(round(ma10, 2))),
                }
            )

        if i >= 19:
            ma20 = sum(closes[i - 19 : i + 1]) / 20
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "indicator_name": "MA20",
                    "indicator_value": Decimal(str(round(ma20, 2))),
                }
            )

        if i >= 4 and closes[i - 4] != 0:
            rsi = 100 - (
                100
                / (1 + (close - closes[i - 4]) / abs(closes[i - 4]) if closes[i - 4] != 0 else 0)
            )
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "indicator_name": "RSI",
                    "indicator_value": Decimal(str(round(rsi, 2))),
                }
            )

        if i >= 1:
            diff = close - closes[i - 1]
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "indicator_name": "PRICE_CHANGE",
                    "indicator_value": Decimal(str(round(diff, 2))),
                }
            )

    for ind in indicators_data:
        stmt = (
            insert(Indicator)
            .values(**ind)
            .on_conflict_do_update(
                index_elements=["ts_code", "trade_date", "indicator_name"],
                set_={
                    "indicator_value": ind["indicator_value"],
                },
            )
        )
        await session.execute(stmt)

    await session.commit()


async def run():
    logger.info(f"执行指标计算任务: {datetime.now()}")

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(DailyBar.trade_date)
                .distinct()
                .order_by(DailyBar.trade_date.desc())
                .limit(30)
            )
            trade_dates = [row[0] for row in result.fetchall()]

            if not trade_dates:
                logger.warning("没有找到K线数据")
                return

            result = await session.execute(select(DailyBar.ts_code).distinct().limit(100))
            ts_codes = [row[0] for row in result.fetchall()]

            for ts_code in ts_codes:
                try:
                    await calculate_indicators(session, ts_code, trade_dates)
                    logger.info(f"计算指标完成: {ts_code}")
                except Exception as e:
                    logger.error(f"计算指标失败 {ts_code}: {e}")

        logger.info("指标计算任务完成")
    except Exception as e:
        logger.error(f"指标计算任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
