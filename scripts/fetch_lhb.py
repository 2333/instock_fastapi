#!/usr/bin/env python3
"""
龙虎榜数据抓取脚本
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("all_proxy", None)
os.environ.pop("ALL_PROXY", None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database import async_session_factory
from core.crawling.eastmoney import EastMoneyCrawler

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def fetch_and_save_lhb(date_str: str = ""):
    """抓取并保存龙虎榜数据"""
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")

    logger.info(f"开始抓取龙虎榜数据: {date_str}")

    crawler = EastMoneyCrawler()
    data = await crawler.fetch_stock_top(date_str)

    if not data:
        logger.warning(f"未获取到 {date_str} 的龙虎榜数据")
        return

    logger.info(f"获取到 {len(data)} 条龙虎榜数据")

    async with async_session_factory() as db:
        for item in data:
            try:
                await db.execute(
                    text("""
                        INSERT INTO stock_tops (ts_code, trade_date, name, sum_buy, sum_sell, net_amount, ranking_times, buy_seat, sell_seat)
                        VALUES (:ts_code, :trade_date, :name, :sum_buy, :sum_sell, :net_amount, 1, 0, 0)
                        ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                            name = EXCLUDED.name,
                            sum_buy = EXCLUDED.sum_buy,
                            sum_sell = EXCLUDED.sum_sell,
                            net_amount = EXCLUDED.net_amount
                    """),
                    {
                        "ts_code": item["ts_code"],
                        "trade_date": item["trade_date"],
                        "name": item["name"],
                        "sum_buy": item.get("buy_amount"),
                        "sum_sell": item.get("sell_amount"),
                        "net_amount": item.get("net_amount"),
                    },
                )
            except Exception as e:
                logger.error(f"保存失败: {item.get('code')} - {e}")

        await db.commit()

    logger.info(f"龙虎榜数据保存完成: {len(data)} 条")


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    asyncio.run(fetch_and_save_lhb(date_arg))
