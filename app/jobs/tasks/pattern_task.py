import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import DailyBar, Pattern

logger = logging.getLogger(__name__)


def detect_patterns(bars: List[DailyBar]) -> List[dict]:
    """简单的形态识别"""
    patterns = []

    if len(bars) < 5:
        return patterns

    closes = [float(bar.close) for bar in bars]
    highs = [float(bar.high) for bar in bars]
    lows = [float(bar.low) for bar in bars]

    recent = bars[-1]
    recent_close = float(recent.close)
    recent_high = max(highs[-5:])
    recent_low = min(lows[-5:])

    if closes[-1] > closes[-2] > closes[-3] and closes[-3] < closes[-4]:
        patterns.append(
            {
                "pattern_name": "MORNING_STAR",
                "pattern_type": "reversal",
                "confidence": Decimal("75.00"),
            }
        )

    if closes[-1] < closes[-2] < closes[-3] and closes[-3] > closes[-4]:
        patterns.append(
            {
                "pattern_name": "EVENING_STAR",
                "pattern_type": "reversal",
                "confidence": Decimal("75.00"),
            }
        )

    if recent_close > recent_high * 0.95 and closes[-1] > closes[-5]:
        patterns.append(
            {
                "pattern_name": "BREAKTHROUGH_HIGH",
                "pattern_type": "breakout",
                "confidence": Decimal("70.00"),
            }
        )

    if recent_close < recent_low * 1.05 and closes[-1] < closes[-5]:
        patterns.append(
            {
                "pattern_name": "BREAKDOWN_LOW",
                "pattern_type": "breakdown",
                "confidence": Decimal("70.00"),
            }
        )

    if all(closes[-i] > closes[-i - 1] for i in range(1, 4)):
        patterns.append(
            {
                "pattern_name": "CONTINUOUS_RISE",
                "pattern_type": "trend",
                "confidence": Decimal("80.00"),
            }
        )

    if all(closes[-i] < closes[-i - 1] for i in range(1, 4)):
        patterns.append(
            {
                "pattern_name": "CONTINUOUS_FALL",
                "pattern_type": "trend",
                "confidence": Decimal("80.00"),
            }
        )

    return patterns


async def run():
    logger.info(f"执行形态识别任务: {datetime.now()}")

    try:
        async with async_session_factory() as session:
            result = await session.execute(select(DailyBar.ts_code).distinct().limit(100))
            ts_codes = [row[0] for row in result.fetchall()]

            for ts_code in ts_codes:
                try:
                    result = await session.execute(
                        select(DailyBar)
                        .where(DailyBar.ts_code == ts_code)
                        .order_by(DailyBar.trade_date.desc())
                        .limit(10)
                    )
                    bars = result.scalars().all()

                    if len(bars) < 5:
                        continue

                    bars = list(reversed(bars))
                    patterns = detect_patterns(bars)

                    if patterns:
                        latest_bar = bars[-1]
                        for pat in patterns:
                            stmt = (
                                insert(Pattern)
                                .values(ts_code=ts_code, trade_date=latest_bar.trade_date, **pat)
                                .on_conflict_do_update(
                                    index_elements=["ts_code", "trade_date", "pattern_name"],
                                    set_={
                                        "confidence": pat["confidence"],
                                    },
                                )
                            )
                            await session.execute(stmt)

                        await session.commit()
                        logger.info(f"识别形态 {ts_code}: {[p['pattern_name'] for p in patterns]}")
                except Exception as e:
                    logger.error(f"形态识别失败 {ts_code}: {e}")

        logger.info("形态识别任务完成")
    except Exception as e:
        logger.error(f"形态识别任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
