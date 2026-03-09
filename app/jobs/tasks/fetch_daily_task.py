import asyncio
import logging
import os
from datetime import datetime, timedelta, date
from typing import List, Optional

from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory
from app.models.stock_model import Stock, DailyBar
from core.crawling.eastmoney import EastMoneyCrawler
from core.crawling.base import AdjustType, ProxyPool
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.tushare_provider import TushareProvider

logger = logging.getLogger(__name__)


def _build_proxy_pool() -> Optional[ProxyPool]:
    proxy_file = os.getenv("CRAWLER_PROXY_FILE", "config/proxy.txt")
    pool = ProxyPool.from_file(proxy_file)
    if pool.proxies:
        logger.info("任务代理池已加载: %s 个代理", len(pool.proxies))
        return pool
    logger.warning("任务代理池为空，将直连运行（file=%s）", proxy_file)
    return None


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
    values = []
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

        close = bar.get("close", 0) or 0
        change = bar.get("change", 0) or 0
        pre_close = bar.get("pre_close")
        if pre_close in (None, ""):
            pre_close = close - change

        values.append(
            {
                "ts_code": ts_code,
                "trade_date": date_str,
                "trade_date_dt": trade_date_dt,
                "open": bar.get("open", 0) or 0,
                "high": bar.get("high", 0) or 0,
                "low": bar.get("low", 0) or 0,
                "close": close,
                "pre_close": pre_close or 0,
                "change": change,
                "pct_chg": bar.get("change_pct", 0) or 0,
                "vol": bar.get("volume", 0) or 0,
                "amount": bar.get("amount", 0) or 0,
            }
        )

    if not values:
        return 0

    stmt = (
        insert(DailyBar)
        .values(values)
        .on_conflict_do_update(
            index_elements=["ts_code", "trade_date", "trade_date_dt"],
            set_={
                "trade_date_dt": insert(DailyBar).excluded.trade_date_dt,
                "open": insert(DailyBar).excluded.open,
                "high": insert(DailyBar).excluded.high,
                "low": insert(DailyBar).excluded.low,
                "close": insert(DailyBar).excluded.close,
                "pre_close": insert(DailyBar).excluded.pre_close,
                "change": insert(DailyBar).excluded.change,
                "pct_chg": insert(DailyBar).excluded.pct_chg,
                "vol": insert(DailyBar).excluded.vol,
                "amount": insert(DailyBar).excluded.amount,
            },
        )
    )
    try:
        await session.execute(stmt)
        await session.commit()
        return len(values)
    except SQLAlchemyError as exc:
        # 兼容历史库结构（可能缺失 uq_daily_bars_ts_code_trade_date）
        logger.warning("批量 upsert 失败，降级逐条保存: %s", exc)
        await session.rollback()

    count = 0
    for item in values:
        result = await session.execute(
            select(DailyBar).where(
                DailyBar.ts_code == item["ts_code"],
                DailyBar.trade_date == item["trade_date"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.trade_date_dt = item["trade_date_dt"]
            existing.open = item["open"]
            existing.high = item["high"]
            existing.low = item["low"]
            existing.close = item["close"]
            existing.pre_close = item["pre_close"]
            existing.change = item["change"]
            existing.pct_chg = item["pct_chg"]
            existing.vol = item["vol"]
            existing.amount = item["amount"]
        else:
            session.add(DailyBar(**item))
        count += 1
    await session.commit()
    return count


async def fetch_and_save_stocks():
    """抓取并保存股票列表"""
    proxy_pool = _build_proxy_pool()
    tushare_provider = TushareProvider()
    baostock_provider = BaoStockProvider(proxy_pool=proxy_pool)
    crawler = EastMoneyCrawler(proxy_pool=proxy_pool)

    try:
        logger.info("Fetching A-stock list (tushare -> baostock -> eastmoney)...")
        stocks = await tushare_provider.fetch_stock_list()
        if not stocks:
            stocks = await baostock_provider.fetch_stock_list()
        if not stocks:
            stocks = await crawler.fetch(data_type="stock_list")
        logger.info(f"Fetched {len(stocks)} stocks")

        async with async_session_factory() as session:
            count = await save_stocks(session, stocks, is_etf=False)
            logger.info(f"Saved {count} stocks to database")

        logger.info("Fetching ETF list (tushare -> baostock -> eastmoney)...")
        etfs = await tushare_provider.fetch_etf_list()
        if not etfs:
            etfs = await baostock_provider.fetch_etf_list()
        if not etfs:
            etfs = await crawler.fetch(data_type="etf_list")
        logger.info(f"Fetched {len(etfs)} ETFs")

        async with async_session_factory() as session:
            count = await save_stocks(session, etfs, is_etf=True)
            logger.info(f"Saved {count} ETFs to database")
    finally:
        await crawler.close()


async def _fetch_bars_with_fallback(
    tushare_provider: TushareProvider,
    baostock_provider: BaoStockProvider,
    em_crawler: EastMoneyCrawler,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: AdjustType,
    max_retries: int = 3,
) -> List[dict]:
    bars = []
    source = "tushare"
    last_error = None

    # 1) 优先 Tushare（不走代理）
    for attempt in range(max_retries):
        try:
            bars = await tushare_provider.fetch_kline(
                code=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust,
                period="daily",
            )
            if bars:
                source = "tushare"
                break
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)

    # 2) Tushare 失败或无数据，降级 BaoStock（使用项目代理）
    if not bars:
        source = "baostock"
        for attempt in range(max_retries):
            try:
                bars = await baostock_provider.fetch_kline(
                    code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    period="daily",
                )
                if bars:
                    break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(0.5)

    # 3) BaoStock 失败或无数据，降级东方财富（使用项目代理）
    if not bars:
        source = "eastmoney"
        for attempt in range(max_retries):
            try:
                bars = await em_crawler.fetch(
                    data_type="kline",
                    code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    period="daily",
                )
                if bars:
                    break
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)

    if not bars and last_error:
        logger.warning("%s 三数据源均失败: %s", symbol, last_error)

    return bars or []


db_semaphore = asyncio.Semaphore(5)


async def _fetch_single_stock(
    semaphore: asyncio.Semaphore,
    tushare_provider: TushareProvider,
    baostock_provider: BaoStockProvider,
    em_crawler: EastMoneyCrawler,
    stock: Stock,
    start_date: str,
    end_date: str,
    idx: int,
    total: int,
) -> tuple[str, int, bool]:
    async with semaphore:
        try:
            bars = await _fetch_bars_with_fallback(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                em_crawler=em_crawler,
                symbol=stock.symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=AdjustType.NO_ADJUST,
            )
            if bars:
                async with db_semaphore:
                    async with async_session_factory() as session:
                        count = await save_daily_bars(session, stock.ts_code, bars)
                        logger.info(f"[{idx}/{total}] {stock.symbol} 保存 {count} 条K线")
                return stock.symbol, count, True
            return stock.symbol, 0, True
        except Exception as e:
            logger.error(f"[{idx}/{total}] {stock.symbol} K线抓取失败: {e}")
            return stock.symbol, 0, False


async def fetch_and_save_daily_bars(days: int = 30, concurrency: int = 20):
    """抓取并保存K线数据"""
    proxy_pool = _build_proxy_pool()
    em_crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    baostock_provider = BaoStockProvider(proxy_pool=proxy_pool)
    tushare_provider = TushareProvider()

    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    async with async_session_factory() as session:
        result = await session.execute(
            select(Stock).where(Stock.list_status == "L").order_by(Stock.ts_code)
        )
        stocks = result.scalars().all()
        total = len(stocks)
        logger.info(f"开始抓取 {total} 只股票的K线数据，并发数: {concurrency}")

        semaphore = asyncio.Semaphore(concurrency)

        tasks = [
            _fetch_single_stock(
                semaphore=semaphore,
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                em_crawler=em_crawler,
                stock=stock,
                start_date=start_date,
                end_date=end_date,
                idx=idx,
                total=total,
            )
            for idx, stock in enumerate(stocks, 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success = sum(1 for r in results if isinstance(r, tuple) and r[2])
        failed = total - success
        logger.info(f"抓取完成: 成功 {success}, 失败 {failed}")

    await em_crawler.close()


async def _get_backfill_targets(
    session: AsyncSession, start: str, end: str, batch_size: int
) -> List[dict]:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS backfill_daily_state (
              ts_code VARCHAR(20) PRIMARY KEY,
              status VARCHAR(20) NOT NULL,
              note TEXT NULL,
              updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    await session.commit()

    query = text(
        """
        SELECT s.*
        FROM stocks s
        WHERE s.list_status = 'L'
          AND COALESCE(s.list_date, '19000101') <= :end
          AND (
                s.delist_date IS NULL
                OR s.delist_date = ''
                OR s.delist_date >= :start
              )
          AND NOT EXISTS (
                SELECT 1
                FROM daily_bars db
                WHERE db.ts_code = s.ts_code
                  AND db.trade_date BETWEEN :start AND :end
          )
          AND NOT EXISTS (
                SELECT 1
                FROM backfill_daily_state st
                WHERE st.ts_code = s.ts_code
                  AND st.status IN ('done', 'nodata')
          )
        ORDER BY s.ts_code
        LIMIT :limit
        """
    )
    result = await session.execute(query, {"start": start, "end": end, "limit": batch_size})
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def _get_backfill_progress(session: AsyncSession, start: str, end: str) -> tuple[int, int]:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS backfill_daily_state (
              ts_code VARCHAR(20) PRIMARY KEY,
              status VARCHAR(20) NOT NULL,
              note TEXT NULL,
              updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    await session.commit()

    total_q = text(
        """
        SELECT COUNT(*)
        FROM stocks s
        WHERE s.list_status = 'L'
          AND COALESCE(s.list_date, '19000101') <= :end
          AND (
                s.delist_date IS NULL
                OR s.delist_date = ''
                OR s.delist_date >= :start
              )
        """
    )
    covered_q = text(
        """
        SELECT COUNT(DISTINCT db.ts_code)
        FROM daily_bars db
        JOIN stocks s ON s.ts_code = db.ts_code
        WHERE db.trade_date BETWEEN :start AND :end
          AND s.list_status = 'L'
          AND COALESCE(s.list_date, '19000101') <= :end
          AND (
                s.delist_date IS NULL
                OR s.delist_date = ''
                OR s.delist_date >= :start
              )
        """
    )
    state_q = text(
        """
        SELECT COUNT(*)
        FROM backfill_daily_state
        WHERE status IN ('done', 'nodata')
        """
    )
    total = (await session.execute(total_q, {"start": start, "end": end})).scalar() or 0
    covered = (await session.execute(covered_q, {"start": start, "end": end})).scalar() or 0
    marked = (await session.execute(state_q)).scalar() or 0
    return int(total), int(max(covered, marked))


async def run_historical_backfill() -> bool:
    """增量回补 2020-2025 日线（Tushare 优先，BaoStock 次之，EastMoney 兜底）"""
    start = os.getenv("BACKFILL_START_DATE", "20200101")
    end = os.getenv("BACKFILL_END_DATE", "20251231")
    batch_size = int(os.getenv("BACKFILL_BATCH_SIZE", "150"))
    sleep_seconds = float(os.getenv("BACKFILL_ITEM_SLEEP", "0.05"))

    proxy_pool = _build_proxy_pool()
    em_crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    baostock_provider = BaoStockProvider(proxy_pool=proxy_pool)
    tushare_provider = TushareProvider()

    async with async_session_factory() as session:
        total, covered = await _get_backfill_progress(session, start, end)
        logger.info("历史回补进度: %s/%s", covered, total)
        if total > 0 and covered >= total:
            logger.info("历史回补已完成（%s-%s）", start, end)
            await em_crawler.close()
            return True

        targets = await _get_backfill_targets(session, start, end, batch_size)
        if not targets:
            logger.info("本轮回补无待处理标的")
            await em_crawler.close()
            return True

        logger.info("开始回补 %s 只股票（%s-%s）", len(targets), start, end)
        for idx, stock in enumerate(targets, 1):
            try:
                bars = await _fetch_bars_with_fallback(
                    tushare_provider=tushare_provider,
                    baostock_provider=baostock_provider,
                    em_crawler=em_crawler,
                    symbol=stock["symbol"],
                    start_date=f"{start[:4]}-{start[4:6]}-{start[6:]}",
                    end_date=f"{end[:4]}-{end[4:6]}-{end[6:]}",
                    adjust=AdjustType.NO_ADJUST,
                )
                if bars:
                    count = await save_daily_bars(session, stock["ts_code"], bars)
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'done', :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='done', note=:note, updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"], "note": f"rows={count}"},
                    )
                    await session.commit()
                    logger.info(
                        "[%s/%s] 回补 %s 成功，写入 %s 条",
                        idx,
                        len(targets),
                        stock["symbol"],
                        count,
                    )
                else:
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'nodata', 'source returned empty', NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='nodata', note='source returned empty', updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"]},
                    )
                    await session.commit()
                    logger.warning("[%s/%s] %s 无可用日线数据", idx, len(targets), stock["symbol"])
            except Exception as exc:
                logger.error("[%s/%s] %s 回补失败: %s", idx, len(targets), stock["symbol"], exc)
            await asyncio.sleep(sleep_seconds)

    await em_crawler.close()
    return False


async def run():
    logger.info(f"执行数据抓取任务: {datetime.now()}")

    try:
        await fetch_and_save_stocks()
        daily_days = int(os.getenv("DAILY_SYNC_DAYS", "60"))
        await fetch_and_save_daily_bars(days=daily_days)
        logger.info("数据抓取任务完成")
    except Exception as e:
        logger.error(f"数据抓取任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
