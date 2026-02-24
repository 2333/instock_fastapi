import asyncio
import logging
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import Stock, DailyBar, Pattern, Indicator, Strategy, StrategyResult

logger = logging.getLogger(__name__)


async def run_strategy(session: AsyncSession, strategy_name: str, ts_codes: list) -> list:
    """运行选股策略"""
    results = []

    for ts_code in ts_codes:
        try:
            result = await session.execute(
                select(DailyBar)
                .where(and_(DailyBar.ts_code == ts_code))
                .order_by(DailyBar.trade_date.desc())
                .limit(5)
            )
            bars = result.scalars().all()

            if len(bars) < 5:
                continue

            bars = list(reversed(bars))
            closes = [float(bar.close) for bar in bars]

            score = 0
            details = {}

            latest = bars[-1]
            latest_close = float(latest.close)
            prev_close = float(bars[-2].close)

            if latest_close > prev_close:
                score += 10
                details["trend"] = "up"
            else:
                score -= 10
                details["trend"] = "down"

            ma5 = sum(closes[-5:]) / 5
            if latest_close > ma5:
                score += 20
                details["above_ma5"] = True
            else:
                score -= 10
                details["above_ma5"] = False

            if len(closes) >= 20:
                ma20 = sum(closes[-20:]) / 20
                if latest_close > ma20:
                    score += 15
                    details["above_ma20"] = True
                else:
                    score -= 10
                    details["above_ma20"] = False

            volume_today = float(latest.vol)
            volume_avg = sum(float(bar.vol) for bar in bars[-5:]) / 5
            if volume_today > volume_avg * 1.5:
                score += 15
                details["volume_surge"] = True

            result = await session.execute(
                select(Pattern).where(
                    and_(Pattern.ts_code == ts_code, Pattern.trade_date == latest.trade_date)
                )
            )
            patterns = result.scalars().all()

            if patterns:
                score += 25
                details["patterns"] = [p.pattern_name for p in patterns]

            signal = "hold"
            if score >= 30:
                signal = "buy"
            elif score <= -20:
                signal = "sell"

            results.append(
                {
                    "ts_code": ts_code,
                    "trade_date": latest.trade_date,
                    "score": score,
                    "signal": signal,
                    "details": details,
                }
            )

        except Exception as e:
            logger.error(f"策略执行失败 {ts_code}: {e}")

    return results


async def run():
    logger.info(f"执行策略选股任务: {datetime.now()}")

    try:
        async with async_session_factory() as session:
            result = await session.execute(select(Strategy).where(Strategy.is_active == True))
            strategies = result.scalars().all()

            if not strategies:
                default_strategy = Strategy(
                    name="default",
                    description="默认选股策略",
                    is_active=True,
                )
                session.add(default_strategy)
                await session.commit()
                strategies = [default_strategy]

            result = await session.execute(select(Stock.ts_code).where(Stock.list_status == "L"))
            ts_codes = [row[0] for row in result.fetchall()]
            logger.info(f"共 {len(ts_codes)} 只股票待处理")

            for strategy in strategies:
                logger.info(f"运行策略: {strategy.name}")

                results = await run_strategy(session, strategy.name, ts_codes)

                selection_id = str(uuid4())

                for res in results:
                    stmt = insert(StrategyResult).values(
                        strategy_id=strategy.id,
                        ts_code=res["ts_code"],
                        trade_date=res["trade_date"],
                        score=Decimal(str(res["score"])),
                        signal=res["signal"],
                        details=res["details"],
                    )
                    await session.execute(stmt)

                await session.commit()
                logger.info(f"策略 {strategy.name} 完成，选出 {len(results)} 只股票")

        logger.info("策略选股任务完成")
    except Exception as e:
        logger.error(f"策略选股任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
