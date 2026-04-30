import asyncio
import logging
import os
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import inspect, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.jobs.market_calendar import is_trading_day, should_skip_market_task
from app.jobs.tasks.fetch_audit import record_fetch_audit, upsert_fetch_audit
from app.models.stock_model import DailyBar, Stock
from app.utils.stock_codes import extract_symbol, normalize_exchange_name, normalize_ts_code
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.base import AdjustType, ProxyPool
from core.crawling.eastmoney import EastMoneyCrawler

logger = logging.getLogger(__name__)
_supports_daily_bar_upsert = True
DAILY_BAR_UPSERT_CONSTRAINT = "uq_daily_bars_ts_code_trade_date_dt"
BACKFILL_TERMINAL_STATUSES = ("done", "needs_fallback", "nodata")
DAILY_BARS_BACKFILL_SOURCE_POLICIES = (
    "baostock",
    "eastmoney",
)
SECURITY_MASTER_SOURCES = ("baostock", "eastmoney")
STOCK_CLASSIFICATION_COLUMNS = (
    "industry_label",
    "industry_taxonomy",
    "industry_source",
    "industry_updated_at",
)
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


def _normalize_ymd(value: str) -> str:
    normalized = value.strip().replace("-", "")
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"invalid trade date: {value!r}")
    return normalized


def _to_iso_ymd(value: str) -> str:
    normalized = _normalize_ymd(value)
    return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"


def _build_proxy_pool() -> ProxyPool | None:
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


def _resolve_source(
    env_name: str,
    allowed: tuple[str, ...],
    default: str,
) -> str:
    value = os.getenv(env_name, default).strip().lower()
    if value not in allowed:
        raise ValueError(f"{env_name} must be one of: {', '.join(allowed)}")
    return value


def _selected_security_master_source() -> str:
    return _resolve_source(
        "SECURITY_MASTER_SOURCE",
        SECURITY_MASTER_SOURCES,
        "baostock",
    )


def _normalize_security_master_source(source: str) -> str:
    normalized = (source or "baostock").strip().lower()
    if normalized not in SECURITY_MASTER_SOURCES:
        allowed = ", ".join(SECURITY_MASTER_SOURCES)
        raise ValueError(f"source must be one of: {allowed}")
    return normalized


def _selected_daily_bar_source() -> str:
    return _resolve_source(
        "DAILY_BARS_SOURCE",
        DAILY_BARS_BACKFILL_SOURCE_POLICIES,
        "baostock",
    )


def _normalize_daily_bar_source(source: str) -> str:
    normalized = (source or "baostock").strip().lower()
    if normalized not in DAILY_BARS_BACKFILL_SOURCE_POLICIES:
        allowed = ", ".join(DAILY_BARS_BACKFILL_SOURCE_POLICIES)
        raise ValueError(f"source must be one of: {allowed}")
    return normalized


def _baostock_request_budget() -> int:
    return max(1, int(os.getenv("BAOSTOCK_DAILY_REQUEST_BUDGET", "90000")))


def _assert_baostock_request_budget(estimated_requests: int, *, context: str) -> None:
    budget = _baostock_request_budget()
    if estimated_requests > budget:
        raise RuntimeError(
            f"BaoStock request budget exceeded for {context}: "
            f"estimated_requests={estimated_requests}, budget={budget}"
        )


async def _resolve_trading_days(
    start_date: str,
    end_date: str,
    *,
    provider: BaoStockProvider,
) -> list[str]:
    calendar = await provider.fetch_trade_calendar(start_date=start_date, end_date=end_date)
    if not calendar:
        logger.warning(
            "交易日历为空，跳过日线抓取窗口: start_date=%s end_date=%s",
            start_date,
            end_date,
        )
        return []

    trading_days: list[str] = []
    for item in calendar:
        trade_date = str(item.get("trade_date") or "").strip()
        if trade_date and item.get("is_trading"):
            trading_days.append(trade_date)
    return trading_days


async def _ensure_backfill_state_table(session: AsyncSession) -> None:
    await session.execute(text("""
            CREATE TABLE IF NOT EXISTS backfill_daily_state (
              ts_code VARCHAR(20) PRIMARY KEY,
              status VARCHAR(20) NOT NULL,
              note TEXT NULL,
              updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """))
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
    list_date: str | None,
    delist_date: str | None,
    is_etf: bool,
    include_industry: bool,
) -> None:
    connection = await session.connection()
    existing_tables = set(
        await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    )

    current = await session.scalar(select(Stock).where(Stock.ts_code == ts_code))
    if current is None:
        current = Stock(
            ts_code=ts_code,
            symbol=symbol,
            name=name,
            area=area,
            industry=industry if include_industry else legacy_stock.industry,
            market=market,
            exchange=exchange,
            list_status="L",
            list_date=list_date,
            delist_date=delist_date,
            is_etf=is_etf,
        )
        session.add(current)
        await session.flush()
    else:
        current.symbol = symbol
        current.name = name
        current.area = area
        if include_industry:
            current.industry = industry
        current.market = market
        current.exchange = exchange
        current.list_status = "L"
        current.list_date = list_date
        current.delist_date = delist_date
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
            text("""
                UPDATE data_fetch_audit
                SET entity_key = :new_ts_code
                WHERE entity_key = :old_ts_code
                """),
            {"new_ts_code": ts_code, "old_ts_code": old_ts_code},
        )

    await session.delete(legacy_stock)


async def save_stocks(
    session: AsyncSession,
    stocks: list[dict],
    is_etf: bool = False,
    *,
    include_industry: bool = False,
) -> int:
    """保存股票/ETF列表"""
    count = 0
    for stock in stocks:
        code = extract_symbol(stock.get("f12") or stock.get("code") or stock.get("symbol"))
        if not code:
            continue

        symbol = code
        exchange = normalize_exchange_name(stock.get("exchange"), symbol)
        ts_code = normalize_ts_code(stock.get("ts_code"), symbol=symbol, exchange=exchange)

        area_value = stock.get("f15") or stock.get("area")
        industry_value = stock.get("f16") or stock.get("industry")
        market_value = stock.get("f17") or stock.get("market")
        area = str(area_value) if area_value else None
        industry = str(industry_value) if industry_value else None
        market = str(market_value) if market_value else None
        name = stock.get("f14") or stock.get("name", "")
        list_date = stock.get("list_date")
        delist_date = stock.get("delist_date")

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
                    list_date=list_date,
                    delist_date=delist_date,
                    is_etf=is_etf,
                    include_industry=include_industry,
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
                **({"industry": industry} if include_industry else {}),
                market=market,
                exchange=exchange,
                list_status="L",
                list_date=list_date,
                delist_date=delist_date,
                is_etf=is_etf,
            )
            .on_conflict_do_update(
                index_elements=["ts_code"],
                set_={
                    "symbol": symbol,
                    "name": name,
                    "area": area,
                    **({"industry": industry} if include_industry else {}),
                    "market": market,
                    "exchange": exchange,
                    "list_status": "L",
                    "list_date": list_date,
                    "delist_date": delist_date,
                    "is_etf": is_etf,
                    "updated_at": datetime.utcnow(),
                },
            )
        )
        await session.execute(stmt)
        count += 1

    await session.commit()
    return count


def _normalize_classification_update_date(update_date: str | None) -> datetime | None:
    if not update_date:
        return None

    for pattern in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(update_date.strip(), pattern)
        except ValueError:
            continue
    return None


def _normalize_classification_ts_code(raw_ts_code: str | None) -> str:
    raw = str(raw_ts_code or "").strip()
    if not raw:
        return ""
    if "." in raw:
        exchange, symbol = raw.split(".", 1)
        if exchange.lower() in {"sh", "sz", "bj"}:
            return normalize_ts_code(None, symbol=symbol, exchange=exchange)
    return normalize_ts_code(raw)


async def _stock_classification_columns_ready(session: AsyncSession) -> bool:
    connection = await session.connection()
    stock_columns = set(
        await connection.run_sync(
            lambda sync_conn: {
                column["name"] for column in inspect(sync_conn).get_columns("stocks")
            }
        )
    )
    return set(STOCK_CLASSIFICATION_COLUMNS) <= stock_columns


async def save_stock_classifications(session: AsyncSession, classifications: list[dict]) -> int:
    """落库股票分类字段，不改写 legacy stocks.industry。"""
    if not classifications:
        return 0

    if not await _stock_classification_columns_ready(session):
        logger.info("stocks 表缺少行业分类字段，跳过分类持久化")
        return 0

    by_ts_code = {}
    for item in classifications:
        normalized_ts_code = _normalize_classification_ts_code(item.get("ts_code"))
        if not normalized_ts_code:
            continue
        by_ts_code[normalized_ts_code] = item

    saved = 0
    result = await session.execute(select(Stock).where(Stock.ts_code.in_(by_ts_code.keys())))
    stocks = result.scalars().all()

    for stock in stocks:
        item = by_ts_code.get(stock.ts_code)
        if item is None:
            continue
        stock.industry_label = (
            str(item.get("industry_label")).strip() if item.get("industry_label") else None
        )
        stock.industry_taxonomy = (
            str(item.get("industry_taxonomy")).strip() if item.get("industry_taxonomy") else None
        )
        stock.industry_source = (
            str(item.get("industry_source")).strip() if item.get("industry_source") else None
        )
        update_at = _normalize_classification_update_date(item.get("update_date"))
        stock.industry_updated_at = update_at or datetime.utcnow()
        saved += 1

    await session.commit()
    return saved


async def save_daily_bars(
    session: AsyncSession,
    ts_code: str,
    bars: list[dict],
    *,
    source: str | None = None,
) -> int:
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
        except ValueError:
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
                "source": source,
            }
        )

    if not values:
        return 0

    global _supports_daily_bar_upsert
    if _supports_daily_bar_upsert:
        daily_bar_insert = insert(DailyBar)
        stmt = daily_bar_insert.values(values).on_conflict_do_update(
            constraint=DAILY_BAR_UPSERT_CONSTRAINT,
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
                "source": daily_bar_insert.excluded.source,
            },
        )
        try:
            await session.execute(stmt)
            await session.commit()
            return len(values)
        except SQLAlchemyError as exc:
            await session.rollback()
            # 兼容历史库结构（可能缺失 M1 trade_date_dt 唯一约束）
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
            existing.source = item["source"]
        else:
            session.add(DailyBar(**item))
        count += 1
    await session.commit()
    return count


async def save_daily_bars_batch(
    session: AsyncSession,
    data: dict[str, list[dict]],
    *,
    source: str | None = None,
) -> int:
    """批量保存多只股票的日线数据（来自 fetch_daily_by_date）。

    data: {ts_code: [bar_dict, ...]}
    """
    all_values = []
    for ts_code, bars in data.items():
        for bar in bars:
            bar_date = bar.get("date")
            if not bar_date:
                continue
            date_str = bar_date.replace("-", "")
            try:
                trade_date_dt = datetime.strptime(bar_date, "%Y-%m-%d").date()
            except ValueError:
                trade_date_dt = None

            close = bar.get("close", 0) or 0
            change = bar.get("change", 0) or 0
            pre_close = bar.get("pre_close")
            if pre_close in (None, ""):
                pre_close = close - change

            all_values.append(
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
                    "source": source,
                }
            )

    if not all_values:
        return 0

    # 分批写入，每批 2000 行
    batch_size = 2000
    total = 0
    for i in range(0, len(all_values), batch_size):
        chunk = all_values[i : i + batch_size]
        global _supports_daily_bar_upsert
        if _supports_daily_bar_upsert:
            daily_bar_insert = insert(DailyBar)
            stmt = daily_bar_insert.values(chunk).on_conflict_do_update(
                constraint=DAILY_BAR_UPSERT_CONSTRAINT,
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
                    "source": daily_bar_insert.excluded.source,
                },
            )
            try:
                await session.execute(stmt)
                total += len(chunk)
            except SQLAlchemyError as exc:
                await session.rollback()
                _supports_daily_bar_upsert = False
                logger.warning("batch upsert 不可用，降级为逐行写入: %s", exc)

    if total > 0:
        await session.commit()
        return total

    # 降级：逐行写入
    count = 0
    for item in all_values:
        result = await session.execute(
            select(DailyBar).where(
                DailyBar.ts_code == item["ts_code"],
                DailyBar.trade_date == item["trade_date"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            for k, v in item.items():
                if k != "ts_code":
                    setattr(existing, k, v)
        else:
            session.add(DailyBar(**item))
        count += 1
    await session.commit()
    return count


async def fetch_and_save_stock_universe() -> int:
    """抓取并保存稳定的股票主数据，不包含行业标签。"""
    return await fetch_and_save_stocks(include_industry=False)


async def fetch_and_save_stock_classifications() -> int:
    """抓取并保存 BaoStock 分类字段（不写入 legacy stocks.industry）。"""
    task_name = "fetch_stock_classification"
    provider = BaoStockProvider()
    try:
        classifications = await provider.fetch_stock_classifications()
        async with async_session_factory() as session:
            saved = await save_stock_classifications(session, classifications)
            await upsert_fetch_audit(
                session,
                task_name=task_name,
                entity_type="stock_classification",
                entity_key="baostock",
                status="done" if saved else "nodata",
                source="baostock",
                note=f"rows={saved}",
            )
            await session.commit()
            logger.info("Saved %s stock classification records", saved)
            return saved
    except Exception as exc:
        await record_fetch_audit(
            task_name=task_name,
            entity_type="stock_classification",
            entity_key="baostock",
            status="needs_fallback",
            source="baostock",
            note=f"fetch stock classification failed: {exc}",
        )
        raise


async def fetch_and_save_stocks(
    *,
    include_industry: bool = False,
    task_name: str = "fetch_stock_universe",
    source_override: str | None = None,
) -> int:
    """抓取并保存股票列表。"""
    if source_override is not None:
        source = _normalize_security_master_source(source_override)
    else:
        source = _selected_security_master_source()

    proxy_pool = _build_proxy_pool()
    baostock_provider = BaoStockProvider()
    crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    total_saved = 0

    try:

        async def _fetch_security_list(
            *,
            entity_key: str,
            is_etf_list: bool,
        ) -> list[dict]:
            label = "ETF list" if is_etf_list else "A-share list"
            fetchers: dict[str, Callable[[], Any]] = {
                "baostock": (
                    lambda: (
                        baostock_provider.fetch_etf_list(include_industry=include_industry)
                        if is_etf_list
                        else baostock_provider.fetch_stock_list(include_industry=include_industry)
                    )
                ),
                "eastmoney": (
                    (lambda: crawler.fetch(data_type="etf_list"))
                    if is_etf_list
                    else (lambda: crawler.fetch(data_type="stock_list"))
                ),
            }

            logger.info("Fetching %s with explicit source=%s", label, source)
            try:
                rows = await fetchers[source]()
            except Exception as exc:
                await record_fetch_audit(
                    task_name=task_name,
                    entity_type="stock_list",
                    entity_key=entity_key,
                    status="needs_fallback",
                    source=source,
                    note=f"explicit source error: {exc}",
                )
                raise

            if not rows:
                await record_fetch_audit(
                    task_name=task_name,
                    entity_type="stock_list",
                    entity_key=entity_key,
                    status="needs_fallback",
                    source=source,
                    note="explicit source returned empty",
                )
                return []
            return rows

        stocks = await _fetch_security_list(entity_key="A_SHARE", is_etf_list=False)
        if stocks:
            logger.info("Fetched %s stocks", len(stocks))
            async with async_session_factory() as session:
                count = await save_stocks(
                    session,
                    stocks,
                    is_etf=False,
                    include_industry=include_industry,
                )
                await upsert_fetch_audit(
                    session,
                    task_name=task_name,
                    entity_type="stock_list",
                    entity_key="A_SHARE",
                    status="done",
                    source=source,
                    note=f"rows={count}",
                )
                await session.commit()
                logger.info("Saved %s stocks to database", count)
                total_saved += count

        etfs = await _fetch_security_list(entity_key="ETF", is_etf_list=True)
        if etfs:
            logger.info("Fetched %s ETFs", len(etfs))
            async with async_session_factory() as session:
                count = await save_stocks(
                    session,
                    etfs,
                    is_etf=True,
                    include_industry=include_industry,
                )
                await upsert_fetch_audit(
                    session,
                    task_name=task_name,
                    entity_type="stock_list",
                    entity_key="ETF",
                    status="done",
                    source=source,
                    note=f"rows={count}",
                )
                await session.commit()
                logger.info("Saved %s ETFs to database", count)
                total_saved += count

        return total_saved
    finally:
        await crawler.close()


async def run_stock_universe_refresh() -> None:
    logger.info("执行股票主数据同步任务: %s", datetime.now())
    try:
        if should_skip_market_task(
            "股票主数据同步任务", today_is_trading_day=await is_trading_day()
        ):
            return
        await fetch_and_save_stock_universe()
        logger.info("股票主数据同步任务完成")
    except Exception as e:
        logger.error("股票主数据同步任务失败: %s", e, exc_info=True)


async def run_stock_classification_refresh() -> None:
    logger.info("执行股票分类同步任务: %s", datetime.now())
    try:
        if should_skip_market_task("股票分类同步任务", today_is_trading_day=await is_trading_day()):
            return
        await fetch_and_save_stock_classifications()
        logger.info("股票分类同步任务完成")
    except Exception as e:
        logger.error("股票分类同步任务失败: %s", e, exc_info=True)


async def _fetch_bars_by_source(
    tushare_provider: Any | None,
    baostock_provider: BaoStockProvider,
    em_crawler: EastMoneyCrawler,
    source: str,
    symbol: str,
    start_date: str,
    end_date: str,
    adjust: AdjustType,
    max_retries: int = 3,
    exchange: str | None = None,
    is_etf: bool = False,
) -> tuple[list[dict], str, str, str]:
    del tushare_provider
    source = _normalize_daily_bar_source(source)
    bars = []
    last_error = None
    normalized_exchange = (exchange or "").strip().upper()
    if source == "baostock" and (is_etf or normalized_exchange == "BJ"):
        return [], source, "needs_fallback", "selected source does not support ETF/BJ contract"

    for attempt in range(max_retries):
        try:
            if source == "baostock":
                bars = await baostock_provider.fetch_kline(
                    code=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                    period="daily",
                )
            else:
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
                await asyncio.sleep(1 if source == "eastmoney" else 0.5)

    if last_error:
        logger.warning("%s source=%s failed: %s", symbol, source, last_error)
        return [], source, "needs_fallback", f"explicit source error: {last_error}"
    return [], source, "needs_fallback", "explicit source returned empty"


db_semaphore = asyncio.Semaphore(5)


async def _fetch_single_stock(
    semaphore: asyncio.Semaphore,
    tushare_provider: Any | None,
    baostock_provider: BaoStockProvider,
    em_crawler: EastMoneyCrawler,
    source: str,
    stock: Stock,
    start_date: str,
    end_date: str,
    idx: int,
    total: int,
) -> tuple[str, int, bool]:
    async with semaphore:
        try:
            bars, source, status, note = await _fetch_bars_by_source(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                em_crawler=em_crawler,
                source=source,
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
                        count = await save_daily_bars(session, stock.ts_code, bars, source=source)
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
                source=source,
                note=f"unexpected task error: {e}",
            )
            return stock.symbol, 0, False


async def fetch_and_save_daily_bars(days: int = 30, concurrency: int = 20):
    """抓取并保存K线数据

    显式单源、按交易日分片抓取，避免运行时混源。
    """
    proxy_pool = _build_proxy_pool()
    selected_source = _selected_daily_bar_source()
    baostock_provider = BaoStockProvider()
    em_crawler = EastMoneyCrawler(proxy_pool=proxy_pool)

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=days)

    try:
        trading_days = await _resolve_trading_days(
            start_dt.date().isoformat(),
            end_dt.date().isoformat(),
            provider=baostock_provider,
        )

        logger.info(
            "开始抓取日线数据: %d 个交易日, source=%s, concurrency=%d",
            len(trading_days),
            selected_source,
            concurrency,
        )

        semaphore = asyncio.Semaphore(max(1, concurrency))
        total_saved = 0
        success_count = 0
        total_tasks = 0

        for trade_date in trading_days:
            async with async_session_factory() as session:
                stocks = await _get_daily_sync_targets(session, trade_date)

            if not stocks:
                logger.info("[%s] 无待同步标的，跳过", trade_date)
                continue

            if selected_source == "baostock":
                _assert_baostock_request_budget(
                    len(stocks), context=f"fetch_and_save_daily_bars:{trade_date}"
                )

            tasks = [
                _fetch_single_stock(
                    semaphore,
                    None,
                    baostock_provider,
                    em_crawler,
                    selected_source,
                    stock,
                    trade_date,
                    trade_date,
                    idx,
                    len(stocks),
                )
                for idx, stock in enumerate(stocks, start=1)
            ]
            results = await asyncio.gather(*tasks)
            total_tasks += len(tasks)
            total_saved += sum(saved for _, saved, _ in results)
            success_count += sum(1 for _, _, ok in results if ok)

        logger.info(
            "日线抓取完成: %d/%d 个分片任务成功，共写入 %d 条",
            success_count,
            total_tasks,
            total_saved,
        )
    finally:
        await em_crawler.close()


async def _get_backfill_targets(
    session: AsyncSession,
    start: str,
    end: str,
    batch_size: int,
    *,
    ensure_state_table: bool = True,
) -> list[dict]:
    state_filter = ""
    if ensure_state_table:
        await _ensure_backfill_state_table(session)
        state_filter = """
          AND NOT EXISTS (
                SELECT 1
                FROM backfill_daily_state st
                WHERE st.ts_code = s.ts_code
                  AND st.status IN ('done', 'needs_fallback', 'nodata')
          )
        """
    else:
        connection = await session.connection()
        existing_tables = set(
            await connection.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        )
        if "backfill_daily_state" in existing_tables:
            state_filter = """
              AND NOT EXISTS (
                    SELECT 1
                    FROM backfill_daily_state st
                    WHERE st.ts_code = s.ts_code
                      AND st.status IN ('done', 'needs_fallback', 'nodata')
              )
            """

    query = text(f"""
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
          {state_filter}
        ORDER BY s.ts_code
        LIMIT :limit
        """)
    result = await session.execute(query, {"start": start, "end": end, "limit": batch_size})
    rows = result.mappings().all()
    return [dict(row) for row in rows]


async def _get_daily_sync_targets(session: AsyncSession, trade_date: str) -> list[Stock]:
    trade_date_ymd = _normalize_ymd(trade_date)
    result = await session.execute(
        select(Stock)
        .where(
            Stock.list_status == "L",
            ~select(DailyBar.id)
            .where(DailyBar.ts_code == Stock.ts_code, DailyBar.trade_date == trade_date_ymd)
            .exists(),
        )
        .order_by(Stock.ts_code)
    )
    return result.scalars().all()


async def _save_daily_bars_small_batch(
    session: AsyncSession,
    ts_code: str,
    bars: list[dict],
    *,
    source: str | None = None,
) -> int:
    count = 0
    for bar in bars:
        bar_date = bar.get("date")
        if not bar_date:
            continue
        date_str = bar_date.replace("-", "")
        try:
            trade_date_dt = datetime.strptime(bar_date, "%Y-%m-%d").date()
        except ValueError:
            continue

        close = bar.get("close", 0) or 0
        change = bar.get("change", 0) or 0
        pre_close = bar.get("pre_close")
        if pre_close in (None, ""):
            pre_close = close - change

        values = {
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
            "source": source,
        }

        existing = await session.scalar(
            select(DailyBar).where(
                DailyBar.ts_code == ts_code,
                DailyBar.trade_date_dt == trade_date_dt,
            )
        )
        if existing:
            for key, value in values.items():
                if key != "ts_code":
                    setattr(existing, key, value)
        else:
            session.add(DailyBar(**values))
        count += 1
    return count


def _resolve_backfill_source_order(
    source_policy: str,
    *,
    exchange: str | None = None,
    is_etf: bool = False,
) -> tuple[str, ...]:
    return (source_policy,)


async def run_daily_bars_backfill_window(
    *,
    start_date: str,
    end_date: str,
    code_limit: int = 20,
    source: str = "baostock",
    execute: bool = False,
    sleep_seconds: float = 0.0,
    provider: Any | None = None,
    baostock_provider: BaoStockProvider | None = None,
    eastmoney_crawler: EastMoneyCrawler | None = None,
    session_factory: Callable[[], Any] = async_session_factory,
) -> dict[str, Any]:
    """Run one bounded daily_bars backfill pass with an explicit source policy."""
    del provider
    start = _normalize_ymd(start_date)
    end = _normalize_ymd(end_date)
    source_policy = _normalize_daily_bar_source(source)
    if start > end:
        raise ValueError("start_date must be <= end_date")
    if code_limit < 1:
        raise ValueError("code_limit must be >= 1")
    if sleep_seconds < 0:
        raise ValueError("sleep_seconds must be >= 0")
    active_baostock = baostock_provider
    active_eastmoney = eastmoney_crawler
    created_eastmoney = False

    try:
        async with session_factory() as session:
            targets = await _get_backfill_targets(
                session,
                start,
                end,
                code_limit,
                ensure_state_table=execute,
            )
            result: dict[str, Any] = {
                "dry_run": not execute,
                "start_date": start,
                "end_date": end,
                "code_limit": code_limit,
                "source": source_policy,
                "target_count": len(targets),
                "saved_rows": 0,
                "targets": [target["ts_code"] for target in targets],
                "items": [],
            }

            if not execute:
                return result

            if source_policy == "baostock":
                _assert_baostock_request_budget(
                    len(targets), context="run_daily_bars_backfill_window"
                )

            for target in targets:
                ts_code = target["ts_code"]
                symbol = target.get("symbol") or extract_symbol(ts_code)
                source_order = _resolve_backfill_source_order(source_policy)
                bars: list[dict] = []
                used_source: str | None = None
                attempts: list[dict[str, Any]] = []

                candidate = source_order[0]
                try:
                    if candidate == "baostock":
                        if active_baostock is None:
                            active_baostock = BaoStockProvider()
                        candidate_bars = await active_baostock.fetch_kline(
                            code=symbol,
                            start_date=_to_iso_ymd(start),
                            end_date=_to_iso_ymd(end),
                            adjust=AdjustType.NO_ADJUST,
                            period="daily",
                        )
                    else:
                        if active_eastmoney is None:
                            active_eastmoney = EastMoneyCrawler(proxy_pool=_build_proxy_pool())
                            created_eastmoney = True
                        candidate_bars = await active_eastmoney.fetch(
                            data_type="kline",
                            code=symbol,
                            start_date=_to_iso_ymd(start),
                            end_date=_to_iso_ymd(end),
                            adjust=AdjustType.NO_ADJUST,
                            period="daily",
                        )
                    attempts.append({"source": candidate, "rows": len(candidate_bars)})
                    if candidate_bars:
                        bars = candidate_bars
                        used_source = candidate
                except Exception as exc:
                    attempts.append({"source": candidate, "error": str(exc)})

                used_source = used_source or candidate
                saved = await _save_daily_bars_small_batch(
                    session, ts_code, bars, source=used_source
                )
                status = "done" if saved else "nodata"
                attempt_note = ",".join(
                    f"{item['source']}:{item.get('rows', 'error')}" for item in attempts
                )
                await upsert_fetch_audit(
                    session,
                    task_name="daily_bars_backfill_window",
                    entity_type="daily_bar",
                    entity_key=ts_code,
                    trade_date=end,
                    status=status,
                    source=used_source,
                    note=f"rows={saved},source_policy={source_policy},attempts={attempt_note}",
                )
                await session.execute(
                    text("""
                        INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                        VALUES (:ts_code, :status, :note, CURRENT_TIMESTAMP)
                        ON CONFLICT (ts_code)
                        DO UPDATE SET status=:status, note=:note, updated_at=CURRENT_TIMESTAMP
                        """),
                    {
                        "ts_code": ts_code,
                        "status": status,
                        "note": (
                            f"rows={saved},source={used_source},"
                            f"source_policy={source_policy},attempts={attempt_note}"
                        ),
                    },
                )
                await session.commit()
                result["saved_rows"] += saved
                result["items"].append(
                    {
                        "ts_code": ts_code,
                        "status": status,
                        "source": used_source,
                        "source_policy": source_policy,
                        "saved_rows": saved,
                        "attempts": attempts,
                    }
                )
                if sleep_seconds:
                    await asyncio.sleep(sleep_seconds)

            return result
    finally:
        if created_eastmoney and active_eastmoney is not None:
            await active_eastmoney.close()


async def _get_backfill_progress(session: AsyncSession, start: str, end: str) -> tuple[int, int]:
    await _ensure_backfill_state_table(session)

    total_q = text("""
        SELECT COUNT(*)
        FROM stocks s
        WHERE s.list_status = 'L'
          AND COALESCE(s.list_date, '19000101') <= :end
          AND (
                s.delist_date IS NULL
                OR s.delist_date = ''
                OR s.delist_date >= :start
              )
        """)
    covered_q = text("""
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
        """)
    state_q = text("""
        SELECT COUNT(*)
        FROM backfill_daily_state
        WHERE status IN ('done', 'needs_fallback', 'nodata')
        """)
    total = (await session.execute(total_q, {"start": start, "end": end})).scalar() or 0
    covered = (await session.execute(covered_q, {"start": start, "end": end})).scalar() or 0
    marked = (await session.execute(state_q)).scalar() or 0
    return int(total), int(max(covered, marked))


async def run_historical_backfill() -> bool:
    """增量回补 2020-2025 日线。仅按显式单源执行。"""
    start = os.getenv("BACKFILL_START_DATE", "20200101")
    end = os.getenv("BACKFILL_END_DATE", "20251231")
    batch_size = int(os.getenv("BACKFILL_BATCH_SIZE", "150"))
    sleep_seconds = float(os.getenv("BACKFILL_ITEM_SLEEP", "0.05"))
    selected_source = _selected_daily_bar_source()

    proxy_pool = _build_proxy_pool()
    em_crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    baostock_provider = BaoStockProvider()

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
        if selected_source == "baostock":
            _assert_baostock_request_budget(len(targets), context="run_historical_backfill")
        for idx, stock in enumerate(targets, 1):
            try:
                bars, used_source, status, note = await _fetch_bars_by_source(
                    tushare_provider=None,
                    baostock_provider=baostock_provider,
                    em_crawler=em_crawler,
                    source=selected_source,
                    symbol=stock["symbol"],
                    start_date=f"{start[:4]}-{start[4:6]}-{start[6:]}",
                    end_date=f"{end[:4]}-{end[4:6]}-{end[6:]}",
                    adjust=AdjustType.NO_ADJUST,
                    exchange=stock.get("exchange"),
                    is_etf=bool(stock.get("is_etf", False)),
                )
                if bars:
                    count = await save_daily_bars(
                        session, stock["ts_code"], bars, source=used_source
                    )
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status="done",
                        source=used_source,
                        note=f"rows={count}",
                    )
                    await session.execute(
                        text("""
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, 'done', :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status='done', note=:note, updated_at=NOW()
                            """),
                        {"ts_code": stock["ts_code"], "note": f"rows={count},source={used_source}"},
                    )
                    await session.commit()
                    logger.info(
                        "[%s/%s] 回补 %s 成功，写入 %s 条, source=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        count,
                        used_source,
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="historical_backfill",
                        entity_type="daily_bar",
                        entity_key=stock["ts_code"],
                        trade_date=end,
                        status=status,
                        source=used_source,
                        note=note,
                    )
                    await session.execute(
                        text("""
                            INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                            VALUES (:ts_code, :status, :note, NOW())
                            ON CONFLICT (ts_code)
                            DO UPDATE SET status=:status, note=:note, updated_at=NOW()
                            """),
                        {"ts_code": stock["ts_code"], "status": status, "note": note},
                    )
                    await session.commit()
                    logger.warning(
                        "[%s/%s] %s 跳过，status=%s, source=%s, note=%s",
                        idx,
                        len(targets),
                        stock["symbol"],
                        status,
                        used_source,
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
                    source=selected_source,
                    note=f"unexpected task error: {exc}",
                )
                await session.execute(
                    text("""
                        INSERT INTO backfill_daily_state(ts_code, status, note, updated_at)
                        VALUES (:ts_code, 'needs_fallback', :note, NOW())
                        ON CONFLICT (ts_code)
                        DO UPDATE SET status='needs_fallback', note=:note, updated_at=NOW()
                        """),
                    {"ts_code": stock["ts_code"], "note": f"unexpected task error: {exc}"},
                )
                await session.commit()
            await asyncio.sleep(sleep_seconds)

    await em_crawler.close()
    return False


async def run():
    logger.info(f"执行数据抓取任务: {datetime.now()}")

    try:
        if should_skip_market_task("数据抓取任务", today_is_trading_day=await is_trading_day()):
            return
        daily_days = int(os.getenv("DAILY_SYNC_DAYS", "1"))
        await fetch_and_save_daily_bars(days=daily_days)
        logger.info("数据抓取任务完成")
    except Exception as e:
        logger.error(f"数据抓取任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
