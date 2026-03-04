#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
东方财富数据爬虫

实现A股、ETF、K线等数据的爬取
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
from decimal import Decimal
import pandas as pd

from .base import (
    BaseCrawler,
    DataSource,
    Market,
    AdjustType,
    CrawlConfig,
    RateLimiter,
    ProxyPool,
)
from core.proxy_manager import get_proxy_manager

logger = logging.getLogger(__name__)


class EastMoneyCrawler(BaseCrawler):
    """东方财富数据爬虫"""

    def __init__(self, **kwargs):
        config = kwargs.pop("config", None)
        proxy_pool = kwargs.pop("proxy_pool", None)
        if proxy_pool is None and os.getenv("CRAWLER_PROXY_ENABLED", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }:
            proxy_manager = get_proxy_manager()
            proxies = proxy_manager.load_proxies()
            if proxies:
                pool = ProxyPool(proxies=[f"http://{p}" for p in proxies])
                logger.info("EastMoney 已启用代理池，代理数量: %s", len(pool.proxies))
                proxy_pool = pool
            else:
                logger.warning("CRAWLER_PROXY_ENABLED=true，但未加载到可用代理")
        super().__init__(config=config or CrawlConfig(min_delay=0.2), proxy_pool=proxy_pool)

    @property
    def data_source(self) -> DataSource:
        return DataSource.EAST_MONEY

    @property
    def source_name(self) -> str:
        return "东方财富"

    def get_base_url(self) -> str:
        return "http://push2.eastmoney.com"

    def get_referer(self) -> str:
        return "http://quote.eastmoney.com/"

    async def fetch(self, data_type: str = "stock_list", **kwargs) -> Any:
        """
        统一的数据获取接口

        Args:
            data_type: 数据类型 (stock_list/etf_list/kline/spot)
            **kwargs: 其他参数
        """
        if data_type == "stock_list":
            return await self.fetch_stock_list()
        elif data_type == "etf_list":
            return await self.fetch_etf_list()
        elif data_type == "kline":
            return await self.fetch_kline(**kwargs)
        elif data_type == "spot":
            return await self.fetch_stock_spot(kwargs.get("code"))
        elif data_type == "trade_calendar":
            return await self.fetch_trade_calendar(
                start_date=kwargs.get("start_date"),
                end_date=kwargs.get("end_date"),
            )
        else:
            raise ValueError(f"Unknown data type: {data_type}")

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """解析JSON响应"""
        try:
            # 东方财富返回格式: var xxx=...;
            match = re.search(r"var\s+\w+\s*=\s*({.+?});", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            return {}

    async def fetch_stock_list(self) -> List[Dict[str, Any]]:
        """获取A股列表（分页获取）"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        all_stocks = []
        page_size = 5000
        page = 1

        while True:
            params = {
                "fid": "f3",
                "po": "1",
                "pz": page_size,
                "pn": page,
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f24,f25,f62",
                "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
            }

            try:
                data = await self._request(url, params=params)
                if not data or "data" not in data:
                    break

                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])

                if not items:
                    break

                all_stocks.extend(items)

                total = data["data"].get("total", 0)
                if len(all_stocks) >= total:
                    break

                page += 1
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"获取A股列表失败 (page {page}): {e}")
                break

        logger.info(f"获取A股列表完成，共 {len(all_stocks)} 只股票")
        return all_stocks

    async def fetch_etf_list(self) -> List[Dict[str, Any]]:
        """获取ETF列表（分页获取）"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        all_etfs = []
        page_size = 5000
        page = 1

        while True:
            params = {
                "fid": "f3",
                "po": "1",
                "pz": page_size,
                "pn": page,
                "fields": "f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21",
                "fs": "m:0+t:8,m:1+t:8",
            }

            try:
                data = await self._request(url, params=params)
                if not data or "data" not in data:
                    break

                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])

                if not items:
                    break

                all_etfs.extend(items)

                total = data["data"].get("total", 0)
                if len(all_etfs) >= total:
                    break

                page += 1
                await asyncio.sleep(0.1)

            except Exception as e:
                logger.error(f"获取ETF列表失败 (page {page}): {e}")
                break

        logger.info(f"获取ETF列表完成，共 {len(all_etfs)} 只ETF")
        return all_etfs

    async def fetch_stock_spot(self, code: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取实时行情"""
        if code:
            url = "http://push2.eastmoney.com/api/qt/stock/get"
            params = {
                "secid": self._convert_code_to_secid(code),
                "fields": "f2,f3,f4,f5,f6,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f22,f23,f24,f25,f26,f27,f28,f31,f32,f33,f34,f35,f36,f37,f38,f39,f40,f41,f43,f44,f45,f46,f47,f48,f49,f50,f51,f57,f58,f59,f60,f61,f62,f63,f64,f65",
            }
        else:
            url = "http://push2.eastmoney.com/api/qt/stock/kline/get"
            params = {
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",  # 日K
                "fqt": "1",  # 前复权
                "secid": "1.000001",  # 上证指数
                "pk": "",
                "fields": "",
            }

        try:
            data = await self._request(url, params=params)
            return data or {}
        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            return {}

    def _convert_code_to_secid(self, code: str) -> str:
        """转换股票代码为东方财富格式"""
        if code.startswith(("6", "5")):
            return f"1.{code}"
        return f"0.{code}"

    async def fetch_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: AdjustType = AdjustType.FORWARD,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        """
        获取K线数据

        Args:
            code: 股票代码
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            adjust: 复权类型
            period: 周期 daily/weekly/monthly
        """
        secid = self._convert_code_to_secid(code)

        # 周期映射
        period_map = {
            "daily": "101",
            "weekly": "102",
            "monthly": "103",
            "quarterly": "104",
            "yearly": "105",
        }
        klt = period_map.get(period, "101")

        # 复权映射
        fqt_map = {
            AdjustType.NO_ADJUST: "0",
            AdjustType.FORWARD: "1",
            AdjustType.BACKWARD: "2",
        }
        fqt = fqt_map.get(adjust, "1")

        url = "http://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65,f66,f67,f68",
            "klt": klt,
            "fqt": fqt,
            "secid": secid,
            "lmt": 5000,  # 最大5000条
        }

        if start_date:
            params["beg"] = start_date.replace("-", "")
        if end_date:
            params["end"] = end_date.replace("-", "")

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                return self._parse_kline_data(data["data"]["klines"])
            return []
        except Exception as e:
            logger.error(f"获取K线失败 {code}: {e}")
            return []

    def _parse_kline_data(self, klines: List[str]) -> List[Dict[str, Any]]:
        """解析K线数据"""
        result = []
        for kline in klines:
            parts = kline.split(",")
            if len(parts) >= 15:
                result.append(
                    {
                        "date": parts[0],
                        "open": float(parts[1]),
                        "close": float(parts[2]),
                        "high": float(parts[3]),
                        "low": float(parts[4]),
                        "volume": int(parts[5]),
                        "amount": float(parts[6]) if len(parts) > 6 else 0,
                        "change_pct": float(parts[7]) if len(parts) > 7 else 0,
                        "change": float(parts[8]) if len(parts) > 8 else 0,
                        "turnover_rate": float(parts[9]) if len(parts) > 9 else 0,
                        "volume_ratio": float(parts[10]) if len(parts) > 10 else 0,
                        "pe": float(parts[11]) if len(parts) > 11 else 0,
                        "pb": float(parts[12]) if len(parts) > 12 else 0,
                        "ps": float(parts[13]) if len(parts) > 13 else 0,
                        "dv_ratio": float(parts[14]) if len(parts) > 14 else 0,
                        "dv_ttm": float(parts[15]) if len(parts) > 15 else 0,
                        "total_mv": float(parts[16]) if len(parts) > 16 else 0,
                        "circ_mv": float(parts[17]) if len(parts) > 17 else 0,
                    }
                )
        return result

    async def fetch_fund_flow(self, code: str) -> Dict[str, Any]:
        """获取资金流向"""
        secid = self._convert_code_to_secid(code)
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": secid,
            "fields": "f43,f44,f45,f46,f47,f48,f49,f50,f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                return self._parse_fund_flow(data["data"])
            return {}
        except Exception as e:
            logger.error(f"获取资金流向失败 {code}: {e}")
            return {}

    def _parse_fund_flow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """解析资金流向数据"""
        return {
            "code": data.get("f12"),
            "name": data.get("f14"),
            "main_net_inflow": data.get("f43", 0),  # 主力净流入
            "main_inflow": data.get("f44", 0),  # 主力流入
            "main_outflow": data.get("f45", 0),  # 主力流出
            "retail_net_inflow": data.get("f46", 0),  # 散户净流入
            "retail_inflow": data.get("f47", 0),  # 散户流入
            "retail_outflow": data.get("f48", 0),  # 散户流出
            "net_inflow_rate": data.get("f49", 0),  # 净流入占比
            "main_net_inflow_rate": data.get("f50", 0),  # 主力净流入占比
            "close_price": data.get("f51", 0),  # 收盘价
            "change_pct": data.get("f52", 0),  # 涨跌幅
            "trade_amount": data.get("f53", 0),  # 成交额
        }

    async def fetch_trade_calendar(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """获取交易日历"""
        url = "http://push2.eastmoney.com/api/qt/cal/get"
        params = {
            "lmt": "0",
            "type": "RANGE:CALENDAR",
            "isNew": "1",
        }

        if start_date:
            params["start"] = start_date.replace("-", "")
        if end_date:
            params["end"] = end_date.replace("-", "")

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                return [
                    {"trade_date": item["calDate"], "is_trading": item["isOpen"] == 1}
                    for item in data["data"]
                ]
            return []
        except Exception as e:
            logger.error(f"获取交易日历失败: {e}")
            return []

    async def fetch_stock_top(self, date_str: str) -> List[Dict[str, Any]]:
        """获取龙虎榜数据"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        params = {
            "pn": 1,
            "pz": 100,
            "po": 1,
            "np": 1,
            "ut": "bd341d99f5cc44d2b04b3d5b82f3f85b",
            "fid": "f62",
            "fs": "m:90+t:2",
            "fields": "f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data and data["data"]["diff"]:
                return self._parse_top_data(data["data"]["diff"], date_str)
            return []
        except Exception as e:
            logger.error(f"获取龙虎榜失败: {e}")
            return []

    def _parse_top_data(self, data: List[Dict], date_str: str) -> List[Dict[str, Any]]:
        """解析龙虎榜数据"""
        result = []
        for item in data:
            code = item.get("f12", "")
            name = item.get("f14", "")
            if not code:
                continue
            market = "SZ" if code.startswith(("0", "3")) else "SH"
            ts_code = f"{code}.SSE" if market == "SH" else f"{code}.SZSE"
            result.append(
                {
                    "ts_code": ts_code,
                    "code": code,
                    "name": name,
                    "close": item.get("f2"),
                    "pct_chg": item.get("f3"),
                    "turnover_rate": item.get("f8"),
                    "amount": item.get("f6"),
                    "net_amount": item.get("f9"),
                    "buy_amount": item.get("f10"),
                    "sell_amount": item.get("f11"),
                    "trade_date": date_str,
                }
            )
        return result

    async def fetch_zh_a_hist(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: AdjustType = AdjustType.FORWARD,
    ) -> pd.DataFrame:
        """获取A股历史数据（返回DataFrame）"""
        klines = await self.fetch_kline(
            code=code,
            start_date=start_date,
            end_date=end_date,
            adjust=adjust,
        )
        if klines:
            return pd.DataFrame(klines)
        return pd.DataFrame()

    async def fetch_limit_up_reason(self, date_str: str) -> List[Dict[str, Any]]:
        """获取涨停原因"""
        url = "http://push2.eastmoney.com/api/qt/stock/get"
        params = {
            "secid": "90.000001",
            "pn": 1,
            "pz": 100,
            "fields": "f12,f14,f2,f3,f8,f10",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                return [
                    {
                        "code": item["f12"],
                        "name": item["f14"],
                        "price": item["f2"],
                        "change_pct": item["f3"],
                        "reason": item.get("f10", ""),
                    }
                    for item in data["data"]["list"]
                ]
            return []
        except Exception as e:
            logger.error(f"获取涨停原因失败: {e}")
            return []

    async def fetch_fund_flow_rank(self, indicator: int = 0) -> List[Dict[str, Any]]:
        """
        获取资金流向排名

        Args:
            indicator: 0=今日, 1=3日, 2=5日, 3=10日
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"
        indicator_map = {0: "今日", 1: "3日", 2: "5日", 3: "10日"}

        params = {
            "fid": "f184",
            "po": "1",
            "pz": 500,
            "pn": 1,
            "fields": "f12,f13,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])

                result = []
                for item in items:
                    result.append(
                        {
                            "code": item.get("f12"),
                            "name": item.get("f14"),
                            "price": item.get("f2"),
                            "change_pct": item.get("f3"),
                            "main_net_inflow": item.get("f62", 0),
                            "main_net_inflow_rate": item.get("f184", 0),
                            "super_net_inflow": item.get("f66", 0),
                            "super_net_inflow_rate": item.get("f69", 0),
                            "big_net_inflow": item.get("f72", 0),
                            "big_net_inflow_rate": item.get("f75", 0),
                            "mid_net_inflow": item.get("f78", 0),
                            "mid_net_inflow_rate": item.get("f81", 0),
                            "small_net_inflow": item.get("f84", 0),
                            "small_net_inflow_rate": item.get("f87", 0),
                        }
                    )
                return result
            return []
        except Exception as e:
            logger.error(f"获取资金流向排名失败: {e}")
            return []

    async def fetch_sector_fund_flow(self, sector_type: str = "industry") -> List[Dict[str, Any]]:
        """
        获取板块资金流向

        Args:
            sector_type: industry=行业, concept=概念
        """
        url = "http://push2.eastmoney.com/api/qt/clist/get"

        if sector_type == "industry":
            fs = "m:90+t:2"
        else:
            fs = "m:90+t:3"

        params = {
            "fid": "f184",
            "po": "1",
            "pz": 200,
            "pn": 1,
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f128",
            "fs": fs,
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])

                result = []
                for item in items:
                    result.append(
                        {
                            "name": item.get("f14"),
                            "change_pct": item.get("f3"),
                            "main_net_inflow": item.get("f62", 0),
                            "main_net_inflow_rate": item.get("f184", 0),
                            "super_net_inflow": item.get("f66", 0),
                            "super_net_inflow_rate": item.get("f69", 0),
                            "big_net_inflow": item.get("f72", 0),
                            "big_net_inflow_rate": item.get("f75", 0),
                            "top_stock": item.get("f128", ""),
                        }
                    )
                return result
            return []
        except Exception as e:
            logger.error(f"获取板块资金流向失败: {e}")
            return []

    async def fetch_block_trade(self, date_str: str) -> List[Dict[str, Any]]:
        """获取大宗交易数据"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"

        params = {
            "fid": "f75",
            "po": "1",
            "pz": 500,
            "pn": 1,
            "fields": "f12,f14,f2,f3,f4,f5,f6,f7,f8",
            "fs": "b:MK0404",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])

                result = []
                for item in items:
                    result.append(
                        {
                            "code": item.get("f12"),
                            "name": item.get("f14"),
                            "close_price": item.get("f2"),
                            "change_pct": item.get("f3"),
                            "avg_price": item.get("f4"),
                            "premium_rate": item.get("f5"),
                            "trade_count": item.get("f6"),
                            "total_volume": item.get("f7"),
                            "total_amount": item.get("f8"),
                        }
                    )
                return result
            return []
        except Exception as e:
            logger.error(f"获取大宗交易失败: {e}")
            return []

    async def fetch_stock_bonus(self) -> List[Dict[str, Any]]:
        """获取分红配送数据"""
        url = "http://push2.eastmoney.com/api/qt/clist/get"

        params = {
            "fid": "f184",
            "po": "1",
            "pz": 500,
            "pn": 1,
            "fields": "f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f128",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
        }

        try:
            data = await self._request(url, params=params)
            if data and "data" in data:
                diff = data["data"].get("diff", {})
                if isinstance(diff, dict):
                    items = list(diff.values())
                else:
                    items = data["data"].get("list", [])
                return items
            return []
        except Exception as e:
            logger.error(f"获取分红配送失败: {e}")
            return []


# 注册数据提供者
from .base import DataProvider


@DataProvider.register(DataSource.EAST_MONEY)
class EastMoneyProvider(EastMoneyCrawler):
    """东方财富数据提供者"""

    pass
