import asyncio
import logging
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.database import async_session_factory
from app.models.stock_model import Stock, FundFlow, SectorFundFlow
from core.crawling.eastmoney import EastMoneyCrawler

logger = logging.getLogger(__name__)


async def save_fund_flows(session: AsyncSession, data: List[dict], trade_date: str) -> int:
    """保存资金流向数据"""
    count = 0
    for item in data:
        code = item.get("code")
        if not code:
            continue

        ts_code = f"{code}.SSE" if code.startswith("6") else f"{code}.SZSE"

        stmt = (
            insert(FundFlow)
            .values(
                ts_code=ts_code,
                trade_date=trade_date,
                net_amount_main=item.get("main_net_inflow", 0),
                net_amount_hf=item.get("super_net_inflow", 0),
                net_amount_zz=item.get("big_net_inflow", 0),
                net_amount_dt=item.get("mid_net_inflow", 0),
                net_amount_xd=item.get("small_net_inflow", 0),
            )
            .on_conflict_do_update(
                index_elements=["ts_code", "trade_date"],
                set_={
                    "net_amount_main": item.get("main_net_inflow", 0),
                    "net_amount_hf": item.get("super_net_inflow", 0),
                    "net_amount_zz": item.get("big_net_inflow", 0),
                    "net_amount_dt": item.get("mid_net_inflow", 0),
                    "net_amount_xd": item.get("small_net_inflow", 0),
                },
            )
        )
        await session.execute(stmt)
        count += 1

    await session.commit()
    return count


async def save_sector_fund_flows(
    session: AsyncSession, data: List[dict], trade_date: str, sector_type: str
) -> int:
    """保存板块资金流向数据"""
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

    crawler = EastMoneyCrawler()
    trade_date = datetime.now().strftime("%Y%m%d")

    try:
        async with async_session_factory() as session:
            logger.info("抓取个股资金流向...")
            fund_flow_data = await crawler.fetch_fund_flow_rank(indicator=0)
            if fund_flow_data:
                count = await save_fund_flows(session, fund_flow_data, trade_date)
                logger.info(f"保存 {count} 条个股资金流向数据")
            await asyncio.sleep(0.5)

            logger.info("抓取行业资金流向...")
            industry_data = await crawler.fetch_sector_fund_flow(sector_type="industry")
            if industry_data:
                count = await save_sector_fund_flows(session, industry_data, trade_date, "industry")
                logger.info(f"保存 {count} 条行业资金流向数据")
            await asyncio.sleep(0.5)

            logger.info("抓取概念资金流向...")
            concept_data = await crawler.fetch_sector_fund_flow(sector_type="concept")
            if concept_data:
                count = await save_sector_fund_flows(session, concept_data, trade_date, "concept")
                logger.info(f"保存 {count} 条概念资金流向数据")

        logger.info("资金流向抓取任务完成")
    except Exception as e:
        logger.error(f"资金流向抓取任务失败: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run())
