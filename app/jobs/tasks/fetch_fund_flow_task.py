import asyncio
import logging
import os
from datetime import datetime
from typing import List

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory
from app.models.stock_model import FundFlow, SectorFundFlow
from core.crawling.base import ProxyPool
from core.crawling.baostock_provider import BaoStockProvider
from core.crawling.eastmoney import EastMoneyCrawler
from core.crawling.tushare_provider import TushareProvider
from core.proxy_manager import get_proxy_manager

logger = logging.getLogger(__name__)


def _build_proxy_pool() -> ProxyPool | None:
    if os.getenv("CRAWLER_PROXY_ENABLED", "false").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        logger.info("资金流任务代理未启用，将直连运行")
        return None

    proxy_manager = get_proxy_manager()
    pool = ProxyPool(proxies=[f"http://{proxy}" for proxy in proxy_manager.data])
    if pool.proxies:
        logger.info("资金流任务代理池已加载: %s 个代理", len(pool.proxies))
        return pool
    logger.warning("资金流任务代理池为空，将直连运行")
    return None


def _trade_date_to_date(trade_date: str):
    return datetime.strptime(trade_date, "%Y%m%d").date()


async def _resolve_candidate_trade_dates(session: AsyncSession, limit: int = 5) -> List[str]:
    today = datetime.now().strftime("%Y%m%d")
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
    if today not in dates:
        dates.insert(0, today)
    return dates


async def _fetch_rank_with_fallback(
    tushare_provider: TushareProvider,
    baostock_provider: BaoStockProvider,
    crawler: EastMoneyCrawler,
    trade_dates: List[str],
) -> tuple[List[dict], str]:
    for trade_date in trade_dates:
        data = await tushare_provider.fetch_fund_flow_rank(trade_date=trade_date)
        if not data:
            data = await baostock_provider.fetch_fund_flow_rank(trade_date=trade_date)
        if data:
            return data, trade_date

    fallback_date = trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")
    return await crawler.fetch_fund_flow_rank(indicator=0), fallback_date


async def _fetch_sector_with_fallback(
    tushare_provider: TushareProvider,
    baostock_provider: BaoStockProvider,
    crawler: EastMoneyCrawler,
    sector_type: str,
    trade_dates: List[str],
) -> tuple[List[dict], str]:
    for trade_date in trade_dates:
        data = await tushare_provider.fetch_sector_fund_flow(
            sector_type=sector_type,
            trade_date=trade_date,
        )
        if not data:
            data = await baostock_provider.fetch_sector_fund_flow(
                sector_type=sector_type,
                trade_date=trade_date,
            )
        if data:
            return data, trade_date

    fallback_date = trade_dates[0] if trade_dates else datetime.now().strftime("%Y%m%d")
    return await crawler.fetch_sector_fund_flow(sector_type=sector_type), fallback_date


async def save_fund_flows(session: AsyncSession, data: List[dict], trade_date: str) -> int:
    """保存资金流向数据"""
    count = 0
    for item in data:
        code = item.get("code")
        if not code:
            continue

        ts_code = f"{code}.SSE" if code.startswith("6") else f"{code}.SZSE"

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
        async with async_session_factory() as session:
            trade_dates = await _resolve_candidate_trade_dates(session)
            logger.info("资金流任务候选交易日: %s", trade_dates)

            logger.info("抓取个股资金流向 (tushare -> baostock -> eastmoney)...")
            fund_flow_data, fund_flow_trade_date = await _fetch_rank_with_fallback(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                crawler=crawler,
                trade_dates=trade_dates,
            )
            if fund_flow_data:
                count = await save_fund_flows(session, fund_flow_data, fund_flow_trade_date)
                logger.info("保存 %s 条个股资金流向数据，trade_date=%s", count, fund_flow_trade_date)
            await asyncio.sleep(0.5)

            logger.info("抓取行业资金流向 (tushare -> baostock -> eastmoney)...")
            industry_data, industry_trade_date = await _fetch_sector_with_fallback(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                crawler=crawler,
                sector_type="industry",
                trade_dates=trade_dates,
            )
            if industry_data:
                count = await save_sector_fund_flows(
                    session, industry_data, industry_trade_date, "industry"
                )
                logger.info("保存 %s 条行业资金流向数据，trade_date=%s", count, industry_trade_date)
            await asyncio.sleep(0.5)

            logger.info("抓取概念资金流向 (tushare -> baostock -> eastmoney)...")
            concept_data, concept_trade_date = await _fetch_sector_with_fallback(
                tushare_provider=tushare_provider,
                baostock_provider=baostock_provider,
                crawler=crawler,
                sector_type="concept",
                trade_dates=trade_dates,
            )
            if concept_data:
                count = await save_sector_fund_flows(
                    session, concept_data, concept_trade_date, "concept"
                )
                logger.info("保存 %s 条概念资金流向数据，trade_date=%s", count, concept_trade_date)

        logger.info("资金流向抓取任务完成")
    except Exception as e:
        logger.error(f"资金流向抓取任务失败: {e}", exc_info=True)
    finally:
        await crawler.close()


if __name__ == "__main__":
    asyncio.run(run())
