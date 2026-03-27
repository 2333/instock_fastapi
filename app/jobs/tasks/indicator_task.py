import asyncio
import logging
from datetime import datetime
from decimal import Decimal

import numpy as np
import talib as tl
from sqlalchemy import and_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.market_calendar import is_trading_day, should_skip_market_task
from app.models.stock_model import DailyBar, Indicator

logger = logging.getLogger(__name__)


def _resolve_trade_date_dt(bar: DailyBar):
    if bar.trade_date_dt is not None:
        return bar.trade_date_dt
    return datetime.strptime(bar.trade_date, "%Y%m%d").date()


async def calculate_indicators(session: AsyncSession, ts_code: str, trade_dates: list[str]):
    """Calculate technical indicators for given ts_code and trade_dates."""
    result = await session.execute(
        select(DailyBar)
        .where(and_(DailyBar.ts_code == ts_code, DailyBar.trade_date.in_(trade_dates)))
        .order_by(DailyBar.trade_date)
    )
    bars = result.scalars().all()

    # Require enough data points to compute indicators
    if len(bars) < 30:
        return

    closes = np.array([float(bar.close) for bar in bars], dtype=np.float64)
    highs = np.array([float(bar.high) for bar in bars], dtype=np.float64)
    lows = np.array([float(bar.low) for bar in bars], dtype=np.float64)
    indicators_data: list[dict] = []

    for i, bar in enumerate(bars):
        trade_date_dt = _resolve_trade_date_dt(bar)
        # Moving Averages
        if i >= 4:
            ma5 = np.mean(closes[max(0, i - 4) : i + 1])
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "trade_date_dt": trade_date_dt,
                    "indicator_name": "MA5",
                    "indicator_value": Decimal(str(round(ma5, 2))),
                }
            )
        if i >= 9:
            ma10 = np.mean(closes[max(0, i - 9) : i + 1])
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "trade_date_dt": trade_date_dt,
                    "indicator_name": "MA10",
                    "indicator_value": Decimal(str(round(ma10, 2))),
                }
            )
        if i >= 19:
            ma20 = np.mean(closes[max(0, i - 19) : i + 1])
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "trade_date_dt": trade_date_dt,
                    "indicator_name": "MA20",
                    "indicator_value": Decimal(str(round(ma20, 2))),
                }
            )
        if i >= 29:
            ma60 = np.mean(closes[max(0, i - 29) : i + 1])
            indicators_data.append(
                {
                    "ts_code": ts_code,
                    "trade_date": bar.trade_date,
                    "trade_date_dt": trade_date_dt,
                    "indicator_name": "MA60",
                    "indicator_value": Decimal(str(round(ma60, 2))),
                }
            )

    # RSI (14)
    if len(closes) >= 14:
        try:
            rsi = tl.RSI(closes, timeperiod=14)
            for i, bar in enumerate(bars):
                if not np.isnan(rsi[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "RSI14",
                            "indicator_value": Decimal(str(round(rsi[i], 2))),
                        }
                    )
        except Exception as e:
            logger.debug(f"RSI计算失败 {ts_code}: {e}")

    # MACD
    if len(closes) >= 26:
        try:
            macd, macd_signal, macd_hist = tl.MACD(closes)
            for i, bar in enumerate(bars):
                if not np.isnan(macd[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "MACD",
                            "indicator_value": Decimal(str(round(macd[i], 4))),
                        }
                    )
                if not np.isnan(macd_signal[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "MACD_SIGNAL",
                            "indicator_value": Decimal(str(round(macd_signal[i], 4))),
                        }
                    )
                if not np.isnan(macd_hist[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "MACD_HIST",
                            "indicator_value": Decimal(str(round(macd_hist[i], 4))),
                        }
                    )
        except Exception as e:
            logger.debug(f"MACD计算失败 {ts_code}: {e}")

    # Boll Bands
    if len(closes) >= 20:
        try:
            upper, middle, lower = tl.BBANDS(closes, timeperiod=20)
            for i, bar in enumerate(bars):
                if not np.isnan(upper[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "BOLL_UPPER",
                            "indicator_value": Decimal(str(round(upper[i], 2))),
                        }
                    )
                if not np.isnan(middle[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "BOLL_MIDDLE",
                            "indicator_value": Decimal(str(round(middle[i], 2))),
                        }
                    )
                if not np.isnan(lower[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "BOLL_LOWER",
                            "indicator_value": Decimal(str(round(lower[i], 2))),
                        }
                    )
        except Exception as e:
            logger.debug(f"布林带计算失败 {ts_code}: {e}")

    # KDJ (Stochastic) -- K and D values
    if len(closes) >= 9:
        try:
            k, d = tl.STOCH(highs, lows, closes)
            for i, bar in enumerate(bars):
                if not np.isnan(k[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "K",
                            "indicator_value": Decimal(str(round(k[i], 2))),
                        }
                    )
                if not np.isnan(d[i]):
                    indicators_data.append(
                        {
                            "ts_code": ts_code,
                            "trade_date": bar.trade_date,
                            "trade_date_dt": _resolve_trade_date_dt(bar),
                            "indicator_name": "D",
                            "indicator_value": Decimal(str(round(d[i], 2))),
                        }
                    )
        except Exception as e:
            logger.debug(f"KDJ计算失败 {ts_code}: {e}")

    # Upsert all indicators
    try:
        for ind in indicators_data:
            stmt = (
                insert(Indicator)
                .values(**ind)
                .on_conflict_do_update(
                    index_elements=["ts_code", "trade_date", "indicator_name"],
                    set_={
                        "trade_date_dt": ind["trade_date_dt"],
                        "indicator_value": ind["indicator_value"],
                    },
                )
            )
            await session.execute(stmt)
    except SQLAlchemyError as exc:
        logger.warning("指标 upsert 失败，降级逐条保存 %s: %s", ts_code, exc)
        await session.rollback()

        for ind in indicators_data:
            existing = await session.scalar(
                select(Indicator).where(
                    Indicator.ts_code == ind["ts_code"],
                    Indicator.trade_date == ind["trade_date"],
                    Indicator.indicator_name == ind["indicator_name"],
                )
            )
            if existing:
                existing.trade_date_dt = ind["trade_date_dt"]
                existing.indicator_value = ind["indicator_value"]
            else:
                session.add(Indicator(**ind))

    await session.commit()


async def run():
    logger.info(f"执行指标计算任务: {datetime.now()}")

    try:
        if should_skip_market_task("指标计算任务", today_is_trading_day=await is_trading_day()):
            return
        async with async_session_factory() as session:
            result = await session.execute(
                select(DailyBar.trade_date)
                .distinct()
                .order_by(DailyBar.trade_date.desc())
                .limit(60)
            )
            trade_dates = [row[0] for row in result.fetchall()]

            if not trade_dates:
                logger.warning("没有找到K线数据")
                return

            result = await session.execute(text("""
                    SELECT DISTINCT db.ts_code
                    FROM daily_bars db
                    JOIN stocks s ON s.ts_code = db.ts_code
                    WHERE s.is_etf = false AND s.list_status = 'L'
                    """))
            ts_codes = [row[0] for row in result.fetchall()]
            logger.info(f"开始计算指标，共 {len(ts_codes)} 只股票")

            success_count = 0

            for idx, ts_code in enumerate(ts_codes):
                try:
                    await calculate_indicators(session, ts_code, trade_dates)
                    success_count += 1
                    if (idx + 1) % 500 == 0:
                        logger.info(f"进度: {idx + 1}/{len(ts_codes)}")
                except Exception as e:
                    logger.error(f"计算指标失败 {ts_code}: {e}")

            logger.info(f"指标计算任务完成: 成功处理 {success_count}/{len(ts_codes)} 只股票")
    except Exception as e:
        logger.error(f"指标计算任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
