#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据爬取脚本

获取所有A股实时行情数据
"""

import asyncio
import logging
from datetime import datetime
from core.crawling import create_crawler, DataSource

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def fetch_all_stocks():
    """获取所有A股数据"""
    crawler = await create_crawler(DataSource.EAST_MONEY)

    total_stocks = 5507
    page_size = 100
    total_pages = (total_stocks + page_size - 1) // page_size

    logger.info(f"开始获取A股数据，共 {total_stocks} 只股票，预计 {total_pages} 页")

    all_stocks = []

    for page in range(1, total_pages + 1):
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "fid": "f3",  # 按涨跌幅排序
            "po": "1",  # 正序
            "pz": page_size,
            "pn": page,
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f24,f25,f62",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",  # 上海、深圳A股
        }

        try:
            data = await crawler._request(url, params=params)
            if data and data.get("data"):
                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    page_stocks = list(diff.values())
                else:
                    page_stocks = data["data"].get("list", [])

                all_stocks.extend(page_stocks)
                logger.info(
                    f"第 {page}/{total_pages} 页，获取 {len(page_stocks)} 只股票，累计 {len(all_stocks)} 只"
                )
            else:
                logger.warning(f"第 {page} 页无数据")

        except Exception as e:
            logger.error(f"第 {page} 页出错: {e}")

        # 避免请求过快
        await asyncio.sleep(0.2)

    await crawler.close()

    logger.info(f"获取完成，共 {len(all_stocks)} 只股票")
    return all_stocks


def transform_stock_data(stocks):
    """转换数据格式"""
    transformed = []
    today = datetime.now().strftime("%Y-%m-%d")

    for stock in stocks:
        code = stock.get("f12", "")
        name = stock.get("f14", "")

        # 判断市场
        if code.startswith(("6", "5")):
            ts_code = f"{code}.SH"
            exchange = "SSE"
        else:
            ts_code = f"{code}.SZ"
            exchange = "SZSE"

        # 解析数值
        try:
            price = float(stock.get("f2", 0)) if stock.get("f2") else 0
        except (ValueError, TypeError):
            price = 0

        try:
            change_pct = float(stock.get("f3", 0)) if stock.get("f3") else 0
        except (ValueError, TypeError):
            change_pct = 0

        try:
            change = float(stock.get("f4", 0)) if stock.get("f4") else 0
        except (ValueError, TypeError):
            change = 0

        try:
            volume = float(stock.get("f5", 0)) if stock.get("f5") else 0
        except (ValueError, TypeError):
            volume = 0

        try:
            amount = float(stock.get("f6", 0)) if stock.get("f6") else 0
        except (ValueError, TypeError):
            amount = 0

        try:
            amplitude = float(stock.get("f7", 0)) if stock.get("f7") else 0
        except (ValueError, TypeError):
            amplitude = 0

        try:
            high = float(stock.get("f15", 0)) if stock.get("f15") else 0
        except (ValueError, TypeError):
            high = 0

        try:
            low = float(stock.get("f16", 0)) if stock.get("f16") else 0
        except (ValueError, TypeError):
            low = 0

        try:
            open_price = float(stock.get("f17", 0)) if stock.get("f17") else 0
        except (ValueError, TypeError):
            open_price = 0

        try:
            close_prev = float(stock.get("f18", 0)) if stock.get("f18") else 0
        except (ValueError, TypeError):
            close_prev = 0

        try:
            turnover_rate = float(stock.get("f8", 0)) if stock.get("f8") else 0
        except (ValueError, TypeError):
            turnover_rate = 0

        try:
            volume_ratio = float(stock.get("f10", 0)) if stock.get("f10") else 0
        except (ValueError, TypeError):
            volume_ratio = 0

        try:
            pe = float(stock.get("f24", 0)) if stock.get("f24") else 0
        except (ValueError, TypeError):
            pe = 0

        try:
            pb = float(stock.get("f25", 0)) if stock.get("f25") else 0
        except (ValueError, TypeError):
            pb = 0

        try:
            main_net_inflow = float(stock.get("f62", 0)) if stock.get("f62") else 0
        except (ValueError, TypeError):
            main_net_inflow = 0

        transformed.append(
            {
                "ts_code": ts_code,
                "symbol": code,
                "name": name,
                "exchange": exchange,
                "date": today,
                "price": price,
                "change_pct": change_pct,
                "change": change,
                "volume": volume,
                "amount": amount,
                "amplitude": amplitude,
                "high": high,
                "low": low,
                "open": open_price,
                "close_prev": close_prev,
                "turnover_rate": turnover_rate,
                "volume_ratio": volume_ratio,
                "pe": pe,
                "pb": pb,
                "main_net_inflow": main_net_inflow,
            }
        )

    return transformed


async def main():
    logger.info("=" * 50)
    logger.info("开始执行A股数据爬取任务")
    logger.info("=" * 50)

    # 获取所有股票数据
    stocks = await fetch_all_stocks()

    if stocks:
        # 转换数据格式
        transformed = transform_stock_data(stocks)

        # 输出前5条数据作为示例
        logger.info("\n数据示例（前5条）:")
        for i, stock in enumerate(transformed[:5]):
            logger.info(
                f"  {i + 1}. {stock['symbol']} {stock['name']} "
                f"现价:{stock['price']} 涨跌:{stock['change_pct']}% "
                f"成交量:{stock['volume']} 成交额:{stock['amount']}"
            )

        logger.info(f"\n总共获取 {len(transformed)} 只股票的数据")

        # TODO: 存储到数据库
        logger.info("\n注意: 数据存储功能待实现")

    else:
        logger.warning("未获取到任何股票数据")

    logger.info("=" * 50)
    logger.info("任务执行完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
