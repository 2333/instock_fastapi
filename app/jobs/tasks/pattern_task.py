import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from typing import List

try:
    import numpy as np
except ImportError:
    np = None

try:
    import talib as tl
except ImportError:
    tl = None

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import DailyBar, Pattern

logger = logging.getLogger(__name__)

PATTERN_MAP = {
    "CDLHAMMER": "HAMMER",
    "CDLINVERTEDHAMMER": "INVERTED_HAMMER",
    "CDLDOJI": "DOJI",
    "CDLENGULFING": "BULLISH_ENGULFING",
    "CDLMORNINGSTAR": "MORNING_STAR",
    "CDLEVENINGSTAR": "EVENING_STAR",
    "CDL3WHITESOLDIERS": "THREE_WHITE_SOLDIERS",
    "CDL3BLACKCROWS": "THREE_BLACK_CROWS",
    "CDLSPINNINGTOP": "SPINNING_TOP",
    "CDLMARUBOZU": "MARUBOZU",
    "CDLSHOOTINGSTAR": "SHOOTING_STAR",
    "CDLHARAMI": "BULLISH_HARAMI",
    "CDLDRAGONFLYDOJI": "DRAGONFLY_DOJI",
    "CDLGRAVESTONEDOJI": "GRAVESTONE_DOJI",
    "CDLPIERCING": "PIERCING",
    "CDLDARKCLOUDCOVER": "DARK_CLOUD_COVER",
    "CDLHANGINGMAN": "HANGING_MAN",
    "CDLTRISTAR": "TRISTAR",
    "CDLTAKURI": "TAKURI",
}


def detect_patterns(bars: List[DailyBar]) -> List[dict]:
    """基于TA-Lib的形态识别"""
    patterns = []

    if np is None or tl is None:
        logger.warning("numpy 或 talib 未安装，无法进行形态识别")
        return patterns

    if len(bars) < 30:
        return patterns

    opens = np.array([float(bar.open) for bar in bars], dtype=np.float64)
    highs = np.array([float(bar.high) for bar in bars], dtype=np.float64)
    lows = np.array([float(bar.low) for bar in bars], dtype=np.float64)
    closes = np.array([float(bar.close) for bar in bars], dtype=np.float64)

    recent_date = bars[-1].trade_date

    pattern_functions = [
        ("CDLHAMMER", tl.CDLHAMMER),
        ("CDLINVERTEDHAMMER", tl.CDLINVERTEDHAMMER),
        ("CDLDOJI", tl.CDLDOJI),
        ("CDLENGULFING", tl.CDLENGULFING),
        ("CDLMORNINGSTAR", tl.CDLMORNINGSTAR),
        ("CDLEVENINGSTAR", tl.CDLEVENINGSTAR),
        ("CDL3WHITESOLDIERS", tl.CDL3WHITESOLDIERS),
        ("CDL3BLACKCROWS", tl.CDL3BLACKCROWS),
        ("CDLSPINNINGTOP", tl.CDLSPINNINGTOP),
        ("CDLMARUBOZU", tl.CDLMARUBOZU),
        ("CDLSHOOTINGSTAR", tl.CDLSHOOTINGSTAR),
        ("CDLHARAMI", tl.CDLHARAMI),
        ("CDLDRAGONFLYDOJI", tl.CDLDRAGONFLYDOJI),
        ("CDLGRAVESTONEDOJI", tl.CDLGRAVESTONEDOJI),
        ("CDLPIERCING", tl.CDLPIERCING),
        ("CDLDARKCLOUDCOVER", tl.CDLDARKCLOUDCOVER),
        ("CDLHANGINGMAN", tl.CDLHANGINGMAN),
        ("CDLTRISTAR", tl.CDLTRISTAR),
        ("CDLTAKURI", tl.CDLTAKURI),
    ]

    for func_name, func in pattern_functions:
        try:
            signals = func(opens, highs, lows, closes)
        except Exception as e:
            logger.debug(f"形态识别失败 {func_name}: {e}")
            continue

        for i, signal in enumerate(signals):
            if signal != 0:
                confidence = min(abs(signal) * 10, 100)

                if func_name == "CDLENGULFING":
                    pattern_type = "reversal"
                    pattern_name = "BULLISH_ENGULFING" if signal > 0 else "BEARISH_ENGULFING"
                elif func_name == "CDLHARAMI":
                    pattern_type = "reversal"
                    pattern_name = "BULLISH_HARAMI" if signal > 0 else "BEARISH_HARAMI"
                else:
                    pattern_type = "candlestick"
                    pattern_name = PATTERN_MAP.get(func_name, func_name)

                patterns.append(
                    {
                        "pattern_name": pattern_name,
                        "pattern_type": pattern_type,
                        "confidence": Decimal(str(round(confidence, 2))),
                    }
                )

    if len(closes) >= 5:
        recent_close = closes[-1]
        recent_high = np.max(highs[-5:])
        recent_low = np.min(lows[-5:])

        if recent_close > recent_high * 0.98:
            patterns.append(
                {
                    "pattern_name": "BREAKTHROUGH_HIGH",
                    "pattern_type": "breakout",
                    "confidence": Decimal("70.00"),
                }
            )

        if recent_close < recent_low * 1.02:
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

        ma5 = np.mean(closes[-5:])
        ma10 = np.mean(closes[-10:]) if len(closes) >= 10 else ma5

        if ma5 > ma10 * 1.02:
            patterns.append(
                {
                    "pattern_name": "MA_GOLDEN_CROSS",
                    "pattern_type": "trend",
                    "confidence": Decimal("75.00"),
                }
            )
        elif ma5 < ma10 * 0.98:
            patterns.append(
                {
                    "pattern_name": "MA_DEATH_CROSS",
                    "pattern_type": "trend",
                    "confidence": Decimal("75.00"),
                }
            )

    return patterns


async def run():
    logger.info(f"执行形态识别任务: {datetime.now()}")

    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text(
                    """
                    SELECT DISTINCT db.ts_code 
                    FROM daily_bars db
                    JOIN stocks s ON s.ts_code = db.ts_code
                    WHERE db.trade_date >= '20260220'
                    AND s.is_etf = false
                    AND s.list_status = 'L'
                    """
                )
            )
            ts_codes = [row[0] for row in result.fetchall()]
            logger.info(f"开始识别形态，共 {len(ts_codes)} 只股票")

            success_count = 0
            pattern_count = 0

            for idx, ts_code in enumerate(ts_codes):
                try:
                    async with async_session_factory() as session_inner:
                        result = await session_inner.execute(
                            select(DailyBar)
                            .where(DailyBar.ts_code == ts_code)
                            .order_by(DailyBar.trade_date.desc())
                            .limit(60)
                        )
                        bars = result.scalars().all()

                        if len(bars) < 30:
                            continue

                        bars = list(reversed(bars))
                        patterns = detect_patterns(bars)

                        if patterns:
                            latest_bar = bars[-1]
                            for pat in patterns:
                                stmt = (
                                    insert(Pattern)
                                    .values(
                                        ts_code=ts_code,
                                        trade_date=latest_bar.trade_date,
                                        trade_date_dt=latest_bar.trade_date_dt,
                                        **pat,
                                    )
                                    .on_conflict_do_update(
                                        index_elements=["ts_code", "trade_date_dt", "pattern_name"],
                                        set_={
                                            "confidence": pat["confidence"],
                                        },
                                    )
                                )
                                await session_inner.execute(stmt)

                            await session_inner.commit()
                            pattern_count += len(patterns)
                            success_count += 1

                        if (idx + 1) % 500 == 0:
                            logger.info(f"进度: {idx + 1}/{len(ts_codes)}")

                except Exception as e:
                    logger.error(f"形态识别失败 {ts_code}: {e}")

            logger.info(
                f"形态识别任务完成: 成功处理 {success_count}/{len(ts_codes)} 只股票，共识别 {pattern_count} 个形态"
            )
    except Exception as e:
        logger.error(f"形态识别任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
