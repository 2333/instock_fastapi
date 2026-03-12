#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股数据爬取脚本

获取所有A股实时行情数据并存储到数据库
"""

import asyncio
import logging
from datetime import datetime
from core.crawling import create_crawler, DataSource
from app.config import get_settings
from app.utils.stock_codes import normalize_exchange_name, normalize_ts_code

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

import psycopg2
from psycopg2.extras import execute_values


def get_db_connection():
    """获取数据库连接"""
    return psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        database=settings.DB_NAME,
    )


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
            "fid": "f3",
            "po": "1",
            "pz": page_size,
            "pn": page,
            "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f24,f25,f62",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
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

        exchange = normalize_exchange_name(None, code)
        ts_code = normalize_ts_code(None, symbol=code, exchange=exchange)

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
                "high": high,
                "low": low,
                "open": open_price,
                "close_prev": close_prev,
            }
        )

    return transformed


def save_to_database(stocks_data: list):
    """保存股票数据到数据库"""
    if not stocks_data:
        return 0

    today = datetime.now().strftime("%Y%m%d")
    trade_date_dt = datetime.strptime(today, "%Y%m%d").date()
    created_at = datetime.now()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # 先确保股票存在于 stocks 表
        existing_codes = set()
        cursor.execute("SELECT ts_code FROM stocks")
        for row in cursor:
            existing_codes.add(row[0])

        missing_stocks = []
        for stock in stocks_data:
            if stock["ts_code"] not in existing_codes:
                missing_stocks.append(
                    (
                        stock["ts_code"],
                        stock["symbol"],
                        stock["name"],
                        stock["exchange"],
                        "CNY",
                        "L",
                        False,  # is_etf
                        created_at,
                        created_at,
                    )
                )

        if missing_stocks:
            insert_stock_sql = """
                INSERT INTO stocks (ts_code, symbol, name, exchange, curr_type, list_status, is_etf, created_at, updated_at)
                VALUES %s
                ON CONFLICT (ts_code) DO NOTHING
            """
            execute_values(cursor, insert_stock_sql, missing_stocks)
            logger.info(f"新增 {len(missing_stocks)} 只股票到 stocks 表")

        insert_sql = """
            INSERT INTO daily_bars (
                ts_code, trade_date, open, high, low, close, 
                pre_close, change, pct_chg, vol, amount, adj_factor, trade_date_dt, created_at
            ) VALUES %s
            ON CONFLICT (ts_code, trade_date) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                pre_close = EXCLUDED.pre_close,
                change = EXCLUDED.change,
                pct_chg = EXCLUDED.pct_chg,
                vol = EXCLUDED.vol,
                amount = EXCLUDED.amount,
                trade_date_dt = EXCLUDED.trade_date_dt
        """

        values = []
        for stock in stocks_data:
            values.append(
                (
                    stock["ts_code"],
                    today,
                    float(stock.get("open", 0) or 0),
                    float(stock.get("high", 0) or 0),
                    float(stock.get("low", 0) or 0),
                    float(stock.get("price", 0) or 0),
                    float(stock.get("close_prev", 0) or 0),
                    float(stock.get("change", 0) or 0),
                    float(stock.get("change_pct", 0) or 0),
                    float(stock.get("volume", 0) or 0),
                    float(stock.get("amount", 0) or 0),
                    1.0,
                    trade_date_dt,
                    created_at,
                )
            )

        execute_values(cursor, insert_sql, values)
        conn.commit()
        logger.info(f"成功存储 {len(stocks_data)} 条数据到数据库")
        cursor.close()
        return len(stocks_data)
    except Exception as e:
        logger.error(f"数据库存储失败: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()


async def main():
    logger.info("=" * 50)
    logger.info("开始执行A股数据爬取任务")
    logger.info("=" * 50)

    stocks = await fetch_all_stocks()

    if stocks:
        transformed = transform_stock_data(stocks)

        logger.info("\n数据示例（前5条）:")
        for i, stock in enumerate(transformed[:5]):
            logger.info(
                f"  {i + 1}. {stock['symbol']} {stock['name']} "
                f"现价:{stock['price']} 涨跌:{stock['change_pct']}% "
                f"成交量:{stock['volume']} 成交额:{stock['amount']}"
            )

        logger.info(f"\n总共获取 {len(transformed)} 只股票的数据")

        logger.info("\n开始存储数据到数据库...")
        saved_count = save_to_database(transformed)
        logger.info(f"成功存储 {saved_count} 条数据到数据库")

    else:
        logger.warning("未获取到任何股票数据")

    logger.info("=" * 50)
    logger.info("任务执行完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
