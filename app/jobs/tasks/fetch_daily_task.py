import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import Stock, DailyBar
from core.crawling.eastmoney import EastMoneyCrawler
from core.crawling.base import AdjustType

logger = logging.getLogger(__name__)


async def save_stocks(session: AsyncSession, stocks: List[dict], is_etf: bool = False) -> int:
    """保存股票/ETF列表"""
    count = 0
    for stock in stocks:
        code = stock.get("f12") or stock.get("code")
        if not code:
            continue

        symbol = code
        if code.startswith("6"):
            exchange = "SSE"
        elif code.startswith(("0", "3")):
            exchange = "SZSE"
        else:
            exchange = "UNKNOWN"

        area = str(stock.get("f15")) if stock.get("f15") else None
        industry = str(stock.get("f16")) if stock.get("f16") else None
        market = str(stock.get("f17")) if stock.get("f17") else None

        stmt = (
            insert(Stock)
            .values(
                ts_code=f"{code}.{exchange}",
                symbol=code,
                name=stock.get("f14") or stock.get("name", ""),
                area=area,
                industry=industry,
                market=market,
                exchange=exchange,
                list_status="L",
                is_etf=is_etf,
            )
            .on_conflict_do_update(
                index_elements=["ts_code"],
                set_={
                    "name": stock.get("f14") or stock.get("name", ""),
                    "area": area,
                    "industry": industry,
                    "market": market,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        await session.execute(stmt)
        count += 1

    await session.commit()
    return count


async def save_daily_bars(session: AsyncSession, ts_code: str, bars: List[dict]) -> int:
    """保存每日K线数据"""
    count = 0
    for bar in bars:
        bar_date = bar.get("date")
        if not bar_date:
            continue

        date_str = bar_date.replace("-", "")

        # 解析日期为 date 对象
        try:
            trade_date_dt = datetime.strptime(bar_date, "%Y-%m-%d").date()
        except:
            trade_date_dt = None

        # 先检查是否存在
        result = await session.execute(
            select(DailyBar).where(DailyBar.ts_code == ts_code, DailyBar.trade_date == date_str)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # 更新现有记录
            existing.open = bar.get("open", 0)
            existing.high = bar.get("high", 0)
            existing.low = bar.get("low", 0)
            existing.close = bar.get("close", 0)
            existing.pct_chg = bar.get("change_pct", 0)
            existing.vol = bar.get("volume", 0)
            existing.amount = bar.get("amount", 0)
            existing.trade_date_dt = trade_date_dt
        else:
            # 插入新记录
            new_bar = DailyBar(
                ts_code=ts_code,
                trade_date=date_str,
                trade_date_dt=trade_date_dt,
                open=bar.get("open", 0),
                high=bar.get("high", 0),
                low=bar.get("low", 0),
                close=bar.get("close", 0),
                pre_close=bar.get("close", 0),
                change=bar.get("change", 0),
                pct_chg=bar.get("change_pct", 0),
                vol=bar.get("volume", 0),
                amount=bar.get("amount", 0),
            )
            session.add(new_bar)

        count += 1

    await session.commit()
    return count


async def fetch_and_save_stocks():
    """抓取并保存股票列表"""
    crawler = EastMoneyCrawler()

    logger.info("Fetching A-stock list...")
    stocks = await crawler.fetch(data_type="stock_list")
    logger.info(f"Fetched {len(stocks)} stocks")

    async with async_session_factory() as session:
        count = await save_stocks(session, stocks, is_etf=False)
        logger.info(f"Saved {count} stocks to database")

    logger.info("Fetching ETF list...")
    etfs = await crawler.fetch(data_type="etf_list")
    logger.info(f"Fetched {len(etfs)} ETFs")

    async with async_session_factory() as session:
        count = await save_stocks(session, etfs, is_etf=True)
        logger.info(f"Saved {count} ETFs to database")


async def fetch_and_save_daily_bars(days: int = 30):
    """抓取并保存K线数据"""
    crawler = EastMoneyCrawler()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Stock).where(Stock.list_status == "L").order_by(Stock.ts_code)
        )
        stocks = result.scalars().all()
        total = len(stocks)
        logger.info(f"开始抓取 {total} 只股票的K线数据")

        for idx, stock in enumerate(stocks, 1):
            try:
                bars = await crawler.fetch(
                    data_type="kline",
                    code=stock.symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=AdjustType.FORWARD,
                )
                if bars:
                    count = await save_daily_bars(session, stock.ts_code, bars)
                    logger.info(f"[{idx}/{total}] {stock.symbol} 保存 {count} 条K线")
            except Exception as e:
                logger.error(f"[{idx}/{total}] {stock.symbol} K线抓取失败: {e}")

            await asyncio.sleep(0.1)


async def run():
    logger.info(f"执行数据抓取任务: {datetime.now()}")

    try:
        await fetch_and_save_stocks()
        await fetch_and_save_daily_bars(days=60)
        logger.info("数据抓取任务完成")
    except Exception as e:
        logger.error(f"数据抓取任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
