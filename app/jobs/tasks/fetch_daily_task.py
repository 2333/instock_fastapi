import asyncio
import logging
import os
from datetime import datetime, timedelta, date
from typing import List, Optional

from sqlalchemy import inspect, select, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory
from app.jobs.tasks.fetch_audit import record_fetch_audit, upsert_fetch_audit
from app.models.stock_model import Stock, DailyBar
from app.utils.stock_codes import extract_symbol, normalize_exchange_name, normalize_ts_code
from core.crawling.eastmoney import EastMoneyCrawler
from core.crawling.base import AdjustType, ProxyPool
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.tushare_provider import TushareProvider

logger = logging.getLogger(__name__)
_supports_daily_bar_upsert = True
BACKFILL_TERMINAL_STATUSES = ("done", "needs_fallback", "nodata")
TS_CODE_CHILD_TABLES = (
    "daily_bars",
    "fund_flows",
    "attention",
    "indicators",
    "patterns",
    "strategy_results",
    "selection_results",
    "stock_tops",
    "stock_block_trades",
    "stock_bonus",
    "stock_limitup_reasons",
    "stock_chip_races",
    "north_bound_funds",
    "backfill_daily_state",
)


def _build_proxy_pool() -> Optional[ProxyPool]:
    if os.getenv("CRAWLER_PROXY_ENABLED", "false").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        logger.info("任务代理已关闭，使用直连模式")
        return None
    proxy_file = os.getenv("CRAWLER_PROXY_FILE", "config/proxy.txt")
    pool = ProxyPool.from_file(proxy_file)
    if pool.proxies:
        logger.info("任务代理池已加载: %s 个代理", len(pool.proxies))
        return pool
    logger.warning("任务代理池为空，将直连运行（file=%s）", proxy_file)
    return None


def _is_tushare_required() -> bool:
    value = os.getenv("TUSHARE_REQUIRED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _inline_fallback_enabled() -> bool:
    value = os.getenv("INLINE_FALLBACK_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _should_use_eastmoney_direct(*, exchange: str | None = None, is_etf: bool = False) -> bool:
    """ETF 与北交所日线直接走 EastMoney。

    这两类标的在当前接入里，Tushare/BaoStock 要么天然不支持、要么经常返回空，
    继续走 primary-only 逻辑只会稳定地产生 needs_fallback，造成“经常更新不全”。
    """
    normalized_exchange = (exchange or "").strip().upper()
    return is_etf or normalized_exchange == "BJ"


async def _ensure_backfill_state_table(session: AsyncSession) -> None:
    await session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS backfill_daily_state (
              ts_code VARCHAR(20) PRIMARY KEY,
              status VARCHAR(20) NOT NULL,
              note TEXT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    await session.commit()


async def _migrate_legacy_stock_code(
    session: AsyncSession,
    legacy_stock: Stock,
    *,
    ts_code: str,
    symbol: str,
    name: str,
    area: str | None,
    industry: str | None,
    market: str | None,
    exchange: str,
    is_etf: bool,
) -> None:
    connection = await session.connection()
    existing_tables = set(await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names()))

    current = await session.scalar(select(Stock).where(Stock.ts_code == ts_code))
    if current is None:
        current = Stock(
            ts_code=ts_code,
            symbol=symbol,
            name=name,
            area=area,
            industry=industry,
            market=market,
            exchange=exchange,
            list_status="L",
            is_etf=is_etf,
        )
        session.add(current)
        await session.flush()
    else:
        current.symbol = symbol
        current.name = name
        current.area = area
        current.industry = industry
        current.market = market
        current.exchange = exchange
        current.list_status = "L"
        current.is_etf = is_etf

    old_ts_code = legacy_stock.ts_code
    for table in TS_CODE_CHILD_TABLES:
        if table not in existing_tables:
            continue
        await session.execute(
            text(f"UPDATE {table} SET ts_code = :new_ts_code WHERE ts_code = :old_ts_code"),
            {"new_ts_code": ts_code, "old_ts_code": old_ts_code},
        )

    if "data_fetch_audit" in existing_tables:
        await session.execute(
            text(
                """
                UPDATE data_fetch_audit
                SET entity_key = :new_ts_code
                WHERE entity_key = :old_ts_code
                """
            ),
            {"new_ts_code": ts_code, "old_ts_code": old_ts_code},
        )

    await session.delete(legacy_stock)


async def save_stocks(session: AsyncSession, stocks: List[dict], is_etf: bool = False) -> int:
    """保存股票/ETF列表"""
    count = 0
    for stock in stocks:
        code = extract_symbol(stock.get("f12") or stock.get("code") or stock.get("symbol"))
        if not code:
            continue

        symbol = code
        exchange = normalize_exchange_name(stock.get("exchange"), symbol)
        ts_code = normalize_ts_code(stock.get("ts_code"), symbol=symbol, exchange=exchange)

        area = str(stock.get("f15")) if stock.get("f15") else None
        industry = str(stock.get("f16")) if stock.get("f16") else None
        market = str(stock.get("f17")) if stock.get("f17") else None
        name = stock.get("f14") or stock.get("name", "")

        normalized_stock = await session.scalar(select(Stock).where(Stock.ts_code == ts_code))
        if normalized_stock is None:
            legacy_stock = await session.scalar(
                select(Stock).where(
                    Stock.symbol == symbol,
                    Stock.is_etf == is_etf,
                    Stock.ts_code != ts_code,
                )
            )
            if legacy_stock is not None:
                await _migrate_legacy_stock_code(
                    session,
                    legacy_stock,
                    ts_code=ts_code,
                    symbol=symbol,
                    name=name,
                    area=area,
                    industry=industry,
                    market=market,
                    exchange=exchange,
                    is_etf=is_etf,
                )
                count += 1
                continue

        stmt = (
            insert(Stock)
            .values(
                ts_code=ts_code,
                symbol=code,
                name=name,
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
                    "symbol": symbol,
                    "name": name,
                    "area": area,
                    "industry": industry,
                    "market": market,
                    "exchange": exchange,
                    "list_status": "L",
                    "is_etf": is_etf,
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

    global _supports_daily_bar_upsert
    if _supports_daily_bar_upsert:
        daily_bar_insert = insert(DailyBar)
        stmt = daily_bar_insert.values(values).on_conflict_do_update(
            constraint="uq_daily_bars_ts_code_trade_date",
            set_={
                "trade_date_dt": daily_bar_insert.excluded.trade_date_dt,
                "open": daily_bar_insert.excluded.open,
                "high": daily_bar_insert.excluded.high,
                "low": daily_bar_insert.excluded.low,
                "close": daily_bar_insert.excluded.close,
                "pre_close": daily_bar_insert.excluded.pre_close,
                "change": daily_bar_insert.excluded.change,
                "pct_chg": daily_bar_insert.excluded.pct_chg,
                "vol": daily_bar_insert.excluded.vol,
                "amount": daily_bar_insert.excluded.amount,
            },
        )
        try:
            await session.execute(stmt)
            await session.commit()
            return len(values)
        except SQLAlchemyError as exc:
            await session.rollback()
            # 兼容历史库结构（可能缺失 uq_daily_bars_ts_code_trade_date）
            _supports_daily_bar_upsert = False
            logger.warning("daily_bars upsert 不可用，后续改为兼容写入: %s", exc)

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
        primary_only = not _inline_fallback_enabled()

        logger.info(
            "Fetching A-stock list (primary=tushare%s)...",
            ", no-inline-fallback" if primary_only else " -> baostock -> eastmoney",
        )
        stocks = await tushare_provider.fetch_stock_list()
        if not stocks and primary_only:
            logger.warning("A 股列表主数据源 Tushare 未返回结果，已记录待降级")
            await record_fetch_audit(
                task_name="fetch_daily_data",
                entity_type="stock_list",
                entity_key="A_SHARE",
                status="needs_fallback",
                source="tushare",
                note="primary source returned empty",
            )
            stocks = []
        if not stocks:
            stocks = await baostock_provider.fetch_stock_list()
        if not stocks:
            stocks = await crawler.fetch(data_type="stock_list")
        if stocks:
            logger.info("Fetched %s stocks", len(stocks))
            async with async_session_factory() as session:
                count = await save_stocks(session, stocks, is_etf=False)
                await upsert_fetch_audit(
                    session,
                    task_name="fetch_daily_data",
                    entity_type="stock_list",
                    entity_key="A_SHARE",
                    status="done",
                    source="tushare" if primary_only else "mixed",
                    note=f"rows={count}",
                )
                await session.commit()
                logger.info("Saved %s stocks to database", count)

        logger.info(
            "Fetching ETF list (primary=tushare%s)...",
            ", no-inline-fallback" if primary_only else " -> baostock -> eastmoney",
        )
        etfs = await tushare_provider.fetch_etf_list()
        if not etfs and primary_only:
            logger.warning("ETF 列表主数据源 Tushare 未返回结果，已记录待降级")
            await record_fetch_audit(
                task_name="fetch_daily_data",
                entity_type="stock_list",
                entity_key="ETF",
                status="needs_fallback",
                source="tushare",
                note="primary source returned empty",
            )
            etfs = []
        if not etfs:
            etfs = await baostock_provider.fetch_etf_list()
        if not etfs:
            etfs = await crawler.fetch(data_type="etf_list")
        if etfs:
            logger.info("Fetched %s ETFs", len(etfs))
            async with async_session_factory() as session:
                count = await save_stocks(session, etfs, is_etf=True)
                await upsert_fetch_audit(
                    session,
                    task_name="fetch_daily_data",
                    entity_type="stock_list",
                    entity_key="ETF",
                    status="done",
                    source="tushare" if primary_only else "mixed",
                    note=f"rows={count}",
                )
                await session.commit()
                logger.info("Saved %s ETFs to database", count)
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
    exchange: str | None = None,
    is_etf: bool = False,
) -> tuple[List[dict], str, str, str]:
    bars = []
    source = "tushare"
    last_error = None
    primary_only = _is_tushare_required() or not _inline_fallback_enabled()
    eastmoney_direct = _should_use_eastmoney_direct(exchange=exchange, is_etf=is_etf)

    # ETF 与北交所当前直接交给 EastMoney，避免主源稳定返回空结果。
    if eastmoney_direct:
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
                    return bars, source, "done", ""
            except Exception as exc:
                last_error = exc
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)
        if last_error:
            return [], source, "needs_fallback", f"eastmoney direct error: {last_error}"
        return [], source, "needs_fallback", "eastmoney direct returned empty"

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

    if primary_only:
        if bars:
            return bars, "tushare", "done", ""
        if last_error:
            return [], "tushare", "needs_fallback", f"primary source error: {last_error}"
        return [], "tushare", "needs_fallback", "primary source returned empty"

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

    if bars:
        return bars, source, "done", ""
    if last_error:
        return [], source, "needs_fallback", f"all sources failed: {last_error}"
    return [], source, "needs_fallback", "all sources returned empty"


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
            bars, source, status, note = await _fetch_bars_with_fallback(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                em_crawler=em_crawler,
                symbol=stock.symbol,
                start_date=start_date,
                end_date=end_date,
                adjust=AdjustType.NO_ADJUST,
                exchange=stock.exchange,
                is_etf=stock.is_etf,
            )
            if bars:
                async with db_semaphore:
                    async with async_session_factory() as session:
                        count = await save_daily_bars(session, stock.ts_code, bars)
                        await upsert_fetch_audit(
                            session,
                            task_name="fetch_daily_data",
                            entity_type="daily_bar_sync",
                            entity_key=stock.ts_code,
                            status="done",
                            source=source,
                            note=f"rows={count}",
                        )
                        await session.commit()
                        logger.info(
                            f"[{idx}/{total}] {stock.symbol} 保存 {count} 条K线, source={source}"
                        )
                return stock.symbol, count, True
            await record_fetch_audit(
                task_name="fetch_daily_data",
                entity_type="daily_bar_sync",
                entity_key=stock.ts_code,
                status=status,
                source=source,
                note=note,
            )
            logger.warning(
                "[%s/%s] %s 未写入K线，status=%s, source=%s, note=%s",
                idx,
                total,
                stock.symbol,
                status,
                source,
                note,
            )
            return stock.symbol, 0, True
        except Exception as e:
            logger.error(f"[{idx}/{total}] {stock.symbol} K线抓取失败: {e}")
            if "session" in locals():
                await session.rollback()
            await record_fetch_audit(
                task_name="fetch_daily_data",
                entity_type="daily_bar_sync",
                entity_key=stock.ts_code,
                status="needs_fallback",
                source="tushare",
                note=f"unexpected task error: {e}",
            )
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
    await _ensure_backfill_state_table(session)

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
                  AND st.status IN ('done', 'needs_fallback', 'nodata')
          )
        ORDER BY s.ts_code
        LIMIT :limit
        """
    )
    result = await session.execute(query, {"start": start, "end": end, "limit": batch_size})
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def _get_backfill_progress(session: AsyncSession, start: str, end: str) -> tuple[int, int]:
    await _ensure_backfill_state_table(session)

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
        WHERE status IN ('done', 'needs_fallback', 'nodata')
        """
    )
    total = (await session.execute(total_q, {"start": start, "end": end})).scalar() or 0
    covered = (await session.execute(covered_q, {"start": start, "end": end})).scalar() or 0
    marked = (await session.execute(state_q)).scalar() or 0
    return int(total), int(max(covered, marked))


async def _get_fallback_targets(session: AsyncSession, batch_size: int) -> List[dict]:
    query = text(
        """
        SELECT s.*
        FROM stocks s
        JOIN backfill_daily_state st ON st.ts_code = s.ts_code
        WHERE st.status = 'needs_fallback'
          AND s.list_status = 'L'
        ORDER BY s.ts_code
        LIMIT :limit
        """
    )
    result = await session.execute(query, {"limit": batch_size})
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def _fetch_bars_from_fallback(
    baostock_provider: BaoStockProvider,
    em_crawler: EastMoneyCrawler,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: AdjustType,
    max_retries: int = 3,
) -> tuple[List[dict], str, str]:
    bars: List[dict] = []
    last_error = None

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
                return bars, "baostock", ""
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                await asyncio.sleep(0.5)

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
                return bars, "eastmoney", ""
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                await asyncio.sleep(1)

    if last_error:
        return [], "fallback", f"all fallback sources failed: {last_error}"
    return [], "fallback", "all fallback sources returned empty"


async def run_historical_backfill() -> bool:
    """增量回补 2020-2025 日线。可通过 TUSHARE_REQUIRED 强制仅允许 Tushare。"""
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
                bars, source, status, note = await _fetch_bars_with_fallback(
                    tushare_provider=tushare_provider,
                    baostock_provider=baostock_provider,
                    em_crawler=em_crawler,
                    symbol=stock["symbol"],
                    start_date=f"{start[:4]}-{start[4:6]}-{start[6:]}",
                    end_date=f"{end[:4]}-{end[4:6]}-{end[6:]}",
                    adjust=AdjustType.NO_ADJUST,
                    exchange=stock.get("exchange"),
                    is_etf=bool(stock.get("is_etf", False)),
                )
                if bars:
                    count = await save_daily_bars(session, stock["ts_code"], bars)
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status="done",
                        source=source,
                        note=f"rows={count}",
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'done', :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='done', note=:note, updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"], "note": f"rows={count},source={source}"},
                    )
                    await session.commit()
                    logger.info(
                        "[%s/%s] 回补 %s 成功，写入 %s 条, source=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        count,
                        source,
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status=status,
                        source=source,
                        note=note,
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, :status, :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status=:status, note=:note, updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"], "status": status, "note": note},
                    )
                    await session.commit()
                    logger.warning(
                        "[%s/%s] %s 跳过，status=%s, source=%s, note=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        status,
                        source,
                        note,
                    )
            except Exception as exc:
                logger.error("[%s/%s] %s 回补失败: %s", idx, len(targets), stock["symbol"], exc)
                await session.rollback()
                await upsert_fetch_audit(
                    session,
                    task_name="historical_backfill",
                    entity_type="daily_bar",
                    entity_key=stock["ts_code"],
                    trade_date=end,
                    status="needs_fallback",
                    source="tushare",
                    note=f"unexpected task error: {exc}",
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                        VALUES (:ts_code, 'needs_fallback', :note, NOW())
                        ON CONFLICT (ts_code)
                        DO UPDATE SET status='needs_fallback', note=:note, updated_at=NOW()
                        """
                    ),
                    {"ts_code": stock["ts_code"], "note": f"unexpected task error: {exc}"},
                )
                await session.commit()
            await asyncio.sleep(sleep_seconds)

    await em_crawler.close()
    return False


async def run_historical_fallback_backfill() -> bool:
    start = os.getenv("BACKFILL_START_DATE", "20200101")
    end = os.getenv("BACKFILL_END_DATE", "20251231")
    batch_size = int(os.getenv("FALLBACK_BACKFILL_BATCH_SIZE", os.getenv("BACKFILL_BATCH_SIZE", "100")))
    sleep_seconds = float(os.getenv("FALLBACK_BACKFILL_ITEM_SLEEP", os.getenv("BACKFILL_ITEM_SLEEP", "0.05")))

    proxy_pool = _build_proxy_pool()
    em_crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    baostock_provider = BaoStockProvider(proxy_pool=proxy_pool)

    async with async_session_factory() as session:
        await _ensure_backfill_state_table(session)
        pending_q = text("SELECT COUNT(*) FROM backfill_daily_state WHERE status = 'needs_fallback'")
        pending = (await session.execute(pending_q)).scalar() or 0
        logger.info("降级补偿待处理: %s", pending)
        if pending == 0:
            logger.info("降级补偿已完成")
            await em_crawler.close()
            return True

        targets = await _get_fallback_targets(session, batch_size)
        if not targets:
            logger.info("本轮降级补偿无待处理标的")
            await em_crawler.close()
            return True

        logger.info("开始降级补偿 %s 只股票（%s-%s）", len(targets), start, end)
        start_date = f"{start[:4]}-{start[4:6]}-{start[6:]}"
        end_date = f"{end[:4]}-{end[4:6]}-{end[6:]}"
        for idx, stock in enumerate(targets, 1):
            try:
                bars, source, note = await _fetch_bars_from_fallback(
                    baostock_provider=baostock_provider,
                    em_crawler=em_crawler,
                    symbol=stock["symbol"],
                    start_date=start_date,
                    end_date=end_date,
                    adjust=AdjustType.NO_ADJUST,
                )
                if bars:
                    count = await save_daily_bars(session, stock["ts_code"], bars)
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill_fallback",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status="done",
                        source=source,
                        note=f"rows={count}",
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'done', :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='done', note=:note, updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"], "note": f"rows={count},source={source}"},
                    )
                    await session.commit()
                    logger.info(
                        "[%s/%s] 降级补偿 %s 成功，写入 %s 条, source=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        count,
                        source,
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill_fallback",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status="needs_fallback",
                        source=source,
                        note=note,
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'needs_fallback', :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='needs_fallback', note=:note, updated_at=NOW()
                            """
                        ),
                        {"ts_code": stock["ts_code"], "note": note},
                    )
                    await session.commit()
                    logger.warning(
                        "[%s/%s] %s 降级补偿未写入，source=%s, note=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        source,
                        note,
                    )
            except Exception as exc:
                await session.rollback()
                logger.error("[%s/%s] %s 降级补偿失败: %s", idx, len(targets), stock["symbol"], exc)
                await upsert_fetch_audit(
                    session,
                    task_name="historical_backfill_fallback",
                    entity_type="daily_bar",
                    entity_key=stock["ts_code"],
                    trade_date=end,
                    status="needs_fallback",
                    source="fallback",
                    note=f"unexpected fallback error: {exc}",
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                        VALUES (:ts_code, 'needs_fallback', :note, NOW())
                        ON CONFLICT (ts_code)
                        DO UPDATE SET status='needs_fallback', note=:note, updated_at=NOW()
                        """
                    ),
                    {"ts_code": stock["ts_code"], "note": f"unexpected fallback error: {exc}"},
                )
                await session.commit()
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
