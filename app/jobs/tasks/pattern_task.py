import asyncio
import logging
from datetime import datetime
from decimal import Decimal

try:
    import numpy as np
except ImportError:
    np = None

try:
    import talib as tl
except ImportError:
    tl = None

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.jobs.market_calendar import is_trading_day, should_skip_market_task
from app.jobs.tasks.fetch_audit import upsert_fetch_audit
from app.models.stock_model import DailyBar, Pattern
from app.services.date_utils import parse_trade_date

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


def _normalize_trade_date(value: str) -> str:
    return value.replace("-", "").strip()


def _pattern_engine_available() -> bool:
    return np is not None and tl is not None


def detect_patterns(bars: list[DailyBar]) -> list[dict]:
    """基于TA-Lib的形态识别"""
    patterns = []

    if not _pattern_engine_available():
        logger.warning("numpy 或 talib 未安装，无法进行形态识别")
        return patterns

    if len(bars) < 30:
        return patterns

    opens = np.array([float(bar.open) for bar in bars], dtype=np.float64)
    highs = np.array([float(bar.high) for bar in bars], dtype=np.float64)
    lows = np.array([float(bar.low) for bar in bars], dtype=np.float64)
    closes = np.array([float(bar.close) for bar in bars], dtype=np.float64)

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


async def _resolve_target_trade_date(session) -> str | None:
    result = await session.execute(text("""
        SELECT MAX(REPLACE(COALESCE(db.trade_date, ''), '-', '')) AS trade_date
        FROM daily_bars db
        JOIN stocks s ON s.ts_code = db.ts_code
        WHERE s.is_etf = false
          AND s.list_status = 'L'
          AND COALESCE(db.trade_date, '') <> ''
        """))
    trade_date = result.scalar_one_or_none()
    return str(trade_date) if trade_date else None


async def _load_target_ts_codes(session, target_trade_date: str) -> list[str]:
    result = await session.execute(
        text("""
            SELECT DISTINCT db.ts_code
            FROM daily_bars db
            JOIN stocks s ON s.ts_code = db.ts_code
            WHERE REPLACE(COALESCE(db.trade_date, ''), '-', '') = :target_trade_date
              AND s.is_etf = false
              AND s.list_status = 'L'
            ORDER BY db.ts_code
            """),
        {"target_trade_date": _normalize_trade_date(target_trade_date)},
    )
    return [row[0] for row in result.fetchall()]


async def _delete_existing_patterns(session, *, ts_code: str, trade_date: str) -> None:
    await session.execute(
        text("""
            DELETE FROM patterns
            WHERE ts_code = :ts_code
              AND REPLACE(COALESCE(trade_date, ''), '-', '') = :trade_date
            """),
        {"ts_code": ts_code, "trade_date": _normalize_trade_date(trade_date)},
    )


async def run():
    logger.info(f"执行形态识别任务: {datetime.now()}")

    try:
        if should_skip_market_task("形态识别任务", today_is_trading_day=await is_trading_day()):
            return
        async with async_session_factory() as session:
            target_trade_date = await _resolve_target_trade_date(session)
            if not target_trade_date:
                logger.info("形态识别任务跳过: 无可识别交易日")
                return

            ts_codes = await _load_target_ts_codes(session, target_trade_date)
            expected_count = len(ts_codes)
            logger.info(f"开始识别形态: trade_date={target_trade_date}, 共 {expected_count} 只股票")

            if not _pattern_engine_available():
                await upsert_fetch_audit(
                    session,
                    task_name="pattern_recognition",
                    entity_type="trade_date",
                    entity_key="ALL",
                    trade_date=target_trade_date,
                    status="failed",
                    source="local",
                    note=(
                        f"expected={expected_count}; evaluated=0; "
                        f"skipped_insufficient_history=0; failed={expected_count}; "
                        "matched_stocks=0; patterns=0; reason=pattern_engine_unavailable"
                    ),
                )
                await session.commit()
                logger.error("形态识别任务失败: numpy 或 talib 未安装")
                return

            matched_count = 0
            evaluated_count = 0
            skipped_insufficient_history_count = 0
            failed_count = 0
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

                        if not bars:
                            skipped_insufficient_history_count += 1
                            continue

                        latest_bar = bars[0]
                        latest_trade_date = _normalize_trade_date(latest_bar.trade_date)
                        if latest_trade_date != _normalize_trade_date(target_trade_date):
                            skipped_insufficient_history_count += 1
                            continue

                        bars = list(reversed(bars))
                        latest_bar = bars[-1]
                        latest_trade_date_dt = latest_bar.trade_date_dt or parse_trade_date(
                            latest_bar.trade_date
                        )
                        if len(bars) < 30 or latest_trade_date_dt is None:
                            await _delete_existing_patterns(
                                session_inner,
                                ts_code=ts_code,
                                trade_date=target_trade_date,
                            )
                            await session_inner.commit()
                            skipped_insufficient_history_count += 1
                            continue

                        await _delete_existing_patterns(
                            session_inner,
                            ts_code=ts_code,
                            trade_date=target_trade_date,
                        )
                        patterns = detect_patterns(bars)
                        evaluated_count += 1

                        if patterns:
                            for pat in patterns:
                                stmt = (
                                    insert(Pattern)
                                    .values(
                                        ts_code=ts_code,
                                        trade_date=latest_bar.trade_date,
                                        trade_date_dt=latest_trade_date_dt,
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

                            pattern_count += len(patterns)
                            matched_count += 1
                        await session_inner.commit()

                        if (idx + 1) % 500 == 0:
                            logger.info(f"进度: {idx + 1}/{len(ts_codes)}")

                except Exception as e:
                    failed_count += 1
                    logger.error(f"形态识别失败 {ts_code}: {e}")

            status = "done" if failed_count == 0 else "partial"
            logger.info(
                "形态识别任务完成: "
                f"trade_date={target_trade_date}, expected={expected_count}, "
                f"evaluated={evaluated_count}, skipped={skipped_insufficient_history_count}, "
                f"failed={failed_count}, matched={matched_count}, patterns={pattern_count}"
            )
            await upsert_fetch_audit(
                session,
                task_name="pattern_recognition",
                entity_type="trade_date",
                entity_key="ALL",
                trade_date=target_trade_date,
                status=status,
                source="local",
                note=(
                    f"expected={expected_count}; evaluated={evaluated_count}; "
                    f"skipped_insufficient_history={skipped_insufficient_history_count}; "
                    f"failed={failed_count}; matched_stocks={matched_count}; "
                    f"patterns={pattern_count}"
                ),
            )
            await session.commit()
    except Exception as e:
        logger.error(f"形态识别任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
