import asyncio
import logging
import os
from datetime import datetime
from typing import List, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory
from app.jobs.market_calendar import (
    current_market_date,
    format_trade_date,
    is_trading_day,
    should_skip_market_task,
)
from app.jobs.tasks.fetch_audit import record_fetch_audit, upsert_fetch_audit
from app.models.stock_model import FundFlow, SectorFundFlow
from app.utils.stock_codes import normalize_ts_code
from core.crawling.base import ProxyPool
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.eastmoney import EastMoneyCrawler
from core.crawling.tushare_provider import TushareProvider

logger = logging.getLogger(__name__)


def _normalize_source(value: str, default: str) -> str:
    normalized = (value or default).strip().lower()
    return normalized or default


def _get_stock_fund_flow_source() -> str:
    return _normalize_source(os.getenv("FUND_FLOW_STOCK_SOURCE", "eastmoney"), "eastmoney")


def _get_sector_fund_flow_source() -> str:
    return _normalize_source(os.getenv("FUND_FLOW_SECTOR_SOURCE", "tushare"), "tushare")


def _inline_fallback_enabled() -> bool:
    value = os.getenv("INLINE_FALLBACK_ENABLED", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _build_proxy_pool() -> ProxyPool | None:
    if os.getenv("CRAWLER_PROXY_ENABLED", "false").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        logger.info("资金流任务代理已关闭，使用直连模式")
        return None
    proxy_file = os.getenv("CRAWLER_PROXY_FILE", "config/proxy.txt")
    pool = ProxyPool.from_file(proxy_file)
    if pool.proxies:
        logger.info("资金流任务代理池已加载: %s 个代理", len(pool.proxies))
        return pool
    logger.warning("资金流任务代理池为空，将直连运行（file=%s）", proxy_file)
    return None


def _trade_date_to_date(trade_date: str):
    return datetime.strptime(trade_date, "%Y%m%d").date()


async def _resolve_candidate_trade_dates(
    session: AsyncSession,
    limit: int = 5,
    *,
    include_today: bool = True,
) -> List[str]:
    today = format_trade_date(current_market_date())
    result = await session.execute(
        text(
            """
            SELECT DISTINCT trade_date
            FROM daily_bars
            ORDER BY trade_date DESC
            LIMIT :limit
            """
        ),
        {"limit": limit},
    )
    dates = [row[0] for row in result.fetchall() if row[0]]
    if include_today and today not in dates:
        dates.insert(0, today)
    return dates


async def _fetch_rank_with_fallback(
    tushare_provider: Any,
    baostock_provider: Any,
    crawler: EastMoneyCrawler,
    trade_dates: List[str],
) -> tuple[List[dict], str]:
    for trade_date in trade_dates:
        data: List[dict] = []
        if hasattr(tushare_provider, "fetch_fund_flow_rank"):
            data = await tushare_provider.fetch_fund_flow_rank(trade_date=trade_date)  # type: ignore
        if not data and hasattr(baostock_provider, "fetch_fund_flow_rank"):
            data = await baostock_provider.fetch_fund_flow_rank(trade_date=trade_date)  # type: ignore
        if data:
            return data, trade_date

    fallback_date = trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")
    fetch_fallback = getattr(crawler, "fetch_fund_flow_rank", None)
    fallback_data: List[dict] = []
    if callable(fetch_fallback):
        result = await fetch_fallback(indicator=0)  # type: ignore[call-arg]
        if isinstance(result, list):
            fallback_data = result
    return fallback_data, fallback_date


async def _fetch_rank_by_source(
    tushare_provider: Any,
    crawler: EastMoneyCrawler,
    trade_dates: List[str],
    source: str,
) -> tuple[List[dict], str, str]:
    for trade_date in trade_dates:
        if source == "tushare":
            data = await tushare_provider.fetch_fund_flow_rank(trade_date=trade_date)
        elif source == "eastmoney":
            result = await crawler.fetch_fund_flow_rank(indicator=0)
            data = result if isinstance(result, list) else []
        else:
            raise ValueError(f"不支持的个股资金流来源: {source}")
        if data:
            return data, trade_date, source
    return [], (trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")), source


async def _fetch_sector_with_fallback(
    tushare_provider: Any,
    baostock_provider: Any,
    crawler: EastMoneyCrawler,
    sector_type: str,
    trade_dates: List[str],
) -> tuple[List[dict], str]:
    for trade_date in trade_dates:
        data: List[dict] = []
        if hasattr(tushare_provider, "fetch_sector_fund_flow"):
            data = await tushare_provider.fetch_sector_fund_flow(
                sector_type=sector_type, trade_date=trade_date
            )  # type: ignore
        if not data and hasattr(baostock_provider, "fetch_sector_fund_flow"):
            data = await baostock_provider.fetch_sector_fund_flow(
                sector_type=sector_type, trade_date=trade_date
            )  # type: ignore
        if data:
            return data, trade_date

    fallback_date = trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")
    fetch_fallback_sector = getattr(crawler, "fetch_sector_fund_flow", None)
    fallback_sector: List[dict] = []
    if callable(fetch_fallback_sector):
        result = await fetch_fallback_sector(sector_type=sector_type, trade_date=fallback_date)  # type: ignore[call-arg]
        if isinstance(result, list):
            fallback_sector = result
    return fallback_sector, fallback_date


async def _fetch_sector_by_source(
    tushare_provider: Any,
    crawler: EastMoneyCrawler,
    sector_type: str,
    trade_dates: List[str],
    source: str,
) -> tuple[List[dict], str, str]:
    for trade_date in trade_dates:
        if source == "tushare":
            data = await tushare_provider.fetch_sector_fund_flow(
                sector_type=sector_type, trade_date=trade_date
            )
        elif source == "eastmoney":
            result = await crawler.fetch_sector_fund_flow(sector_type=sector_type)
            data = result if isinstance(result, list) else []
        else:
            raise ValueError(f"不支持的板块资金流来源: {source}")
        if data:
            return data, trade_date, source
    return [], (trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")), source


async def _fetch_sector_data(
    tushare_provider: Any,
    baostock_provider: Any,
    crawler: EastMoneyCrawler,
    sector_type: str,
    trade_dates: List[str],
    source: str,
    primary_only: bool,
) -> tuple[List[dict], str, str]:
    if source == "fallback":
        if primary_only:
            return (
                [],
                trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                source,
            )
        data, trade_date = await _fetch_sector_with_fallback(
            tushare_provider=tushare_provider,
            baostock_provider=baostock_provider,
            crawler=crawler,
            sector_type=sector_type,
            trade_dates=trade_dates,
        )
        return data, trade_date, "fallback"

    return await _fetch_sector_by_source(
        tushare_provider=tushare_provider,
        crawler=crawler,
        sector_type=sector_type,
        trade_dates=trade_dates,
        source=source,
    )


async def save_fund_flows(session: AsyncSession, data: List[dict], trade_date: str) -> int:
    """保存资金流向数据"""
    count = 0
    for item in data:
        code = item.get("code")
        if not code:
            continue

        ts_code = normalize_ts_code(code)

        values = {
            "ts_code": ts_code,
            "trade_date": trade_date,
            "trade_date_dt": _trade_date_to_date(trade_date),
            "net_amount_main": item.get("main_net_inflow", 0),
            "net_amount_hf": item.get("super_net_inflow", 0),
            "net_amount_zz": item.get("big_net_inflow", 0),
            "net_amount_dt": item.get("mid_net_inflow", 0),
            "net_amount_xd": item.get("small_net_inflow", 0),
        }
        stmt = (
            insert(FundFlow)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["ts_code", "trade_date"],
                set_={
                    "net_amount_main": values["net_amount_main"],
                    "net_amount_hf": values["net_amount_hf"],
                    "net_amount_zz": values["net_amount_zz"],
                    "net_amount_dt": values["net_amount_dt"],
                    "net_amount_xd": values["net_amount_xd"],
                },
            )
        )
        try:
            await session.execute(stmt)
        except SQLAlchemyError:
            # 兼容未加唯一约束的历史库，降级为手动查改
            await session.rollback()
            existing = await session.scalar(
                select(FundFlow).where(
                    FundFlow.ts_code == ts_code,
                    FundFlow.trade_date == trade_date,
                )
            )
            if existing:
                existing.trade_date_dt = values["trade_date_dt"]
                existing.net_amount_main = values["net_amount_main"]
                existing.net_amount_hf = values["net_amount_hf"]
                existing.net_amount_zz = values["net_amount_zz"]
                existing.net_amount_dt = values["net_amount_dt"]
                existing.net_amount_xd = values["net_amount_xd"]
            else:
                session.add(FundFlow(**values))
        count += 1

    await session.commit()
    return count


async def save_sector_fund_flows(
    session: AsyncSession, data: List[dict], trade_date: str, sector_type: str
) -> int:
    """保存板块资金流向数据"""
    await session.execute(
        text(
            """
            DELETE FROM sector_fund_flows
            WHERE trade_date = :trade_date AND sector_type = :sector_type
            """
        ),
        {"trade_date": trade_date, "sector_type": sector_type},
    )
    count = 0
    for item in data:
        name = item.get("name")
        if not name:
            continue

        stmt = insert(SectorFundFlow).values(
            sector_name=name,
            sector_type=sector_type,
            trade_date=trade_date,
            pct_chg=item.get("change_pct", 0),
            net_amount_main=item.get("main_net_inflow", 0),
            net_rate_main=item.get("main_net_inflow_rate", 0),
            net_amount_hf=item.get("super_net_inflow", 0),
            net_rate_hf=item.get("super_net_inflow_rate", 0),
            top_stock=item.get("top_stock", ""),
        )
        await session.execute(stmt)
        count += 1

    await session.commit()
    return count


async def run():
    """执行资金流向数据抓取任务"""
    logger.info(f"执行资金流向抓取任务: {datetime.now()}")

    proxy_pool = _build_proxy_pool()
    crawler = EastMoneyCrawler(proxy_pool=proxy_pool)
    baostock_provider = BaoStockProvider(proxy_pool=proxy_pool)
    tushare_provider = TushareProvider()

    try:
        today_is_trading_day = await is_trading_day(crawler=crawler)
        if should_skip_market_task("资金流向抓取任务", today_is_trading_day=today_is_trading_day):
            return

        async with async_session_factory() as session:
            trade_dates = await _resolve_candidate_trade_dates(
                session,
                include_today=today_is_trading_day,
            )
            logger.info("资金流任务候选交易日: %s", trade_dates)

            stock_source = _get_stock_fund_flow_source()
            sector_source = _get_sector_fund_flow_source()
            primary_only = not _inline_fallback_enabled()

            try:
                logger.info("抓取个股资金流向 (source=%s)...", stock_source)
                if stock_source == "fallback" and not primary_only:
                    fund_flow_data, fund_flow_trade_date = await _fetch_rank_with_fallback(
                        tushare_provider=tushare_provider,
                        baostock_provider=baostock_provider,
                        crawler=crawler,
                        trade_dates=trade_dates,
                    )
                else:
                    fund_flow_data, fund_flow_trade_date, _ = await _fetch_rank_by_source(
                        tushare_provider=tushare_provider,
                        crawler=crawler,
                        trade_dates=trade_dates,
                        source=stock_source,
                    )
                if fund_flow_data:
                    count = await save_fund_flows(session, fund_flow_data, fund_flow_trade_date)
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="stock_fund_flow",
                        entity_key="ALL",
                        trade_date=fund_flow_trade_date,
                        status="done",
                        source=stock_source,
                        note=f"rows={count}",
                    )
                    await session.commit()
                    logger.info(
                        "保存 %s 条个股资金流向数据，trade_date=%s", count, fund_flow_trade_date
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="stock_fund_flow",
                        entity_key="ALL",
                        trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                        status="needs_fallback",
                        source=stock_source,
                        note="primary source returned empty",
                    )
                    await session.commit()
                    logger.warning("个股资金流未产出数据，已记录待降级，source=%s", stock_source)
            except Exception as exc:
                await upsert_fetch_audit(
                    session,
                    task_name="fetch_fund_flow",
                    entity_type="stock_fund_flow",
                    entity_key="ALL",
                    trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                    status="needs_fallback",
                    source=stock_source,
                    note=f"source error: {exc}",
                )
                await session.commit()
                logger.warning("个股资金流抓取异常，已记录待降级: %s", exc)
            await asyncio.sleep(0.5)

            try:
                logger.info("抓取行业资金流向 (source=%s)...", sector_source)
                industry_data, industry_trade_date, used_source = await _fetch_sector_data(
                    tushare_provider=tushare_provider,
                    baostock_provider=baostock_provider,
                    crawler=crawler,
                    sector_type="industry",
                    trade_dates=trade_dates,
                    source=sector_source,
                    primary_only=primary_only,
                )
                if industry_data:
                    count = await save_sector_fund_flows(
                        session, industry_data, industry_trade_date, "industry"
                    )
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="sector_fund_flow",
                        entity_key="industry",
                        trade_date=industry_trade_date,
                        status="done",
                        source=used_source,
                        note=f"rows={count}",
                    )
                    await session.commit()
                    logger.info(
                        "保存 %s 条行业资金流向数据，trade_date=%s, source=%s",
                        count,
                        industry_trade_date,
                        used_source,
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="sector_fund_flow",
                        entity_key="industry",
                        trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                        status="needs_fallback",
                        source=sector_source,
                        note="primary source returned empty",
                    )
                    await session.commit()
                    logger.warning("行业资金流未产出数据，已记录待降级，source=%s", sector_source)
            except Exception as exc:
                await upsert_fetch_audit(
                    session,
                    task_name="fetch_fund_flow",
                    entity_type="sector_fund_flow",
                    entity_key="industry",
                    trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                    status="needs_fallback",
                    source=sector_source,
                    note=f"source error: {exc}",
                )
                await session.commit()
                logger.warning("行业资金流抓取异常，已记录待降级: %s", exc)
            await asyncio.sleep(0.5)

            try:
                logger.info("抓取概念资金流向 (source=%s)...", sector_source)
                concept_data, concept_trade_date, used_source = await _fetch_sector_data(
                    tushare_provider=tushare_provider,
                    baostock_provider=baostock_provider,
                    crawler=crawler,
                    sector_type="concept",
                    trade_dates=trade_dates,
                    source=sector_source,
                    primary_only=primary_only,
                )
                if concept_data:
                    count = await save_sector_fund_flows(
                        session, concept_data, concept_trade_date, "concept"
                    )
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="sector_fund_flow",
                        entity_key="concept",
                        trade_date=concept_trade_date,
                        status="done",
                        source=used_source,
                        note=f"rows={count}",
                    )
                    await session.commit()
                    logger.info(
                        "保存 %s 条概念资金流向数据，trade_date=%s, source=%s",
                        count,
                        concept_trade_date,
                        used_source,
                    )
                else:
                    await upsert_fetch_audit(
                        session,
                        task_name="fetch_fund_flow",
                        entity_type="sector_fund_flow",
                        entity_key="concept",
                        trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                        status="needs_fallback",
                        source=sector_source,
                        note="primary source returned empty",
                    )
                    await session.commit()
                    logger.warning("概念资金流未产出数据，已记录待降级，source=%s", sector_source)
            except Exception as exc:
                await upsert_fetch_audit(
                    session,
                    task_name="fetch_fund_flow",
                    entity_type="sector_fund_flow",
                    entity_key="concept",
                    trade_date=trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d"),
                    status="needs_fallback",
                    source=sector_source,
                    note=f"source error: {exc}",
                )
                await session.commit()
                logger.warning("概念资金流抓取异常，已记录待降级: %s", exc)

        logger.info("资金流向抓取任务完成")
    except Exception as e:
        logger.error(f"资金流向抓取任务失败: {e}", exc_info=True)
        await record_fetch_audit(
            task_name="fetch_fund_flow",
            entity_type="task",
            entity_key="run",
            status="needs_fallback",
            source="mixed",
            note=f"task error: {e}",
        )
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(run())
