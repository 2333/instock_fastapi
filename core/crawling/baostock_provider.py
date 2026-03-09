#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaoStock 数据提供器

仅用于日线数据抓取，作为主数据源；失败时由其他数据源兜底。
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import AdjustType, ProxyPool

logger = logging.getLogger(__name__)


@dataclass
class BaoStockConfig:
    min_delay: float = 0.05


class BaoStockProvider:
    _lock = threading.Lock()
    _proxy_env_lock = threading.Lock()
    _logged_in = False
    _last_request_ts = 0.0

    def __init__(
        self,
        config: Optional[BaoStockConfig] = None,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        self.config = config or BaoStockConfig()
        self.proxy_pool = proxy_pool

    async def fetch_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: AdjustType = AdjustType.NO_ADJUST,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        if period != "daily":
            logger.warning("BaoStock 仅接入日线，收到 period=%s，跳过", period)
            return []
        return await asyncio.to_thread(
            self._fetch_kline_sync, code, start_date, end_date, adjust
        )

    def _fetch_kline_sync(
        self,
        code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: AdjustType,
    ) -> List[Dict[str, Any]]:
        try:
            import baostock as bs  # type: ignore
        except Exception:
            logger.warning("baostock 未安装，跳过 BaoStock 数据源")
            return []

        bs_code = self._to_baostock_code(code)
        if not bs_code:
            return []

        start = (start_date or "1990-01-01").replace("/", "-")
        end = (end_date or "2099-12-31").replace("/", "-")
        adjust_flag = self._to_adjust_flag(adjust)
        proxy = self.proxy_pool.get_proxy() if self.proxy_pool else None

        try:
            with self._proxy_env(proxy):
                self._ensure_login(bs)
                self._wait_rate_limit()
                rs = bs.query_history_k_data_plus(
                    bs_code,
                    "date,open,high,low,close,preclose,volume,amount,pctChg",
                    start_date=start,
                    end_date=end,
                    frequency="d",
                    adjustflag=adjust_flag,
                )
                if rs.error_code != "0":
                    logger.warning("BaoStock 查询失败 %s %s", bs_code, rs.error_msg)
                    if self.proxy_pool and proxy:
                        self.proxy_pool.mark_failed(proxy)
                    return []
        except Exception:
            if self.proxy_pool and proxy:
                self.proxy_pool.mark_failed(proxy)
            raise

        rows: List[Dict[str, Any]] = []
        while rs.next():
            row = rs.get_row_data()
            if not row or len(row) < 8:
                continue
            open_v = self._to_float(row[1])
            high_v = self._to_float(row[2])
            low_v = self._to_float(row[3])
            close_v = self._to_float(row[4])
            pre_close = self._to_float(row[5])
            pct = self._to_float(row[8]) if len(row) > 8 else None
            if pct is None and pre_close not in (None, 0):
                pct = (close_v - pre_close) / pre_close * 100
            change = None
            if pre_close is not None and close_v is not None:
                change = close_v - pre_close

            rows.append(
                {
                    "date": row[0],
                    "open": open_v,
                    "high": high_v,
                    "low": low_v,
                    "close": close_v,
                    "pre_close": pre_close,
                    "volume": self._to_float(row[6]) or 0,
                    "amount": self._to_float(row[7]) or 0,
                    "change_pct": pct or 0,
                    "change": change or 0,
                }
            )
        return rows

    async def fetch_stock_list(self) -> List[Dict[str, Any]]:
        logger.info("BaoStock 不提供 stock_list，返回空结果供下游降级")
        return []

    async def fetch_etf_list(self) -> List[Dict[str, Any]]:
        logger.info("BaoStock 不提供 etf_list，返回空结果供下游降级")
        return []

    async def fetch_fund_flow_rank(self, trade_date: str) -> List[Dict[str, Any]]:
        logger.info("BaoStock 不提供 fund_flow_rank，返回空结果供下游降级")
        return []

    async def fetch_sector_fund_flow(self, sector_type: str, trade_date: str) -> List[Dict[str, Any]]:
        logger.info("BaoStock 不提供 sector_fund_flow，返回空结果供下游降级")
        return []

    def _ensure_login(self, bs: Any) -> None:
        with self._lock:
            if self._logged_in:
                return
            login_result = bs.login()
            if getattr(login_result, "error_code", "-1") != "0":
                raise RuntimeError(f"BaoStock 登录失败: {login_result.error_msg}")
            self._logged_in = True

    def _to_baostock_code(self, code: str) -> Optional[str]:
        if not code:
            return None
        if code.startswith(("sh.", "sz.")):
            return code
        if code.startswith("6"):
            return f"sh.{code}"
        if code.startswith(("0", "3")):
            return f"sz.{code}"
        return None

    def _to_adjust_flag(self, adjust: AdjustType) -> str:
        # BaoStock: 1 后复权，2 前复权，3 不复权
        if adjust == AdjustType.BACKWARD:
            return "1"
        if adjust == AdjustType.FORWARD:
            return "2"
        return "3"

    def _to_float(self, value: Any) -> Optional[float]:
        try:
            if value in (None, "", "null"):
                return None
            return float(value)
        except Exception:
            return None

    def _wait_rate_limit(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_ts
            if elapsed < self.config.min_delay:
                time.sleep(self.config.min_delay - elapsed)
            self._last_request_ts = time.monotonic()

    @contextmanager
    def _proxy_env(self, proxy: Optional[str]):
        if not proxy:
            yield
            return

        with self._proxy_env_lock:
            old_http = os.environ.get("http_proxy")
            old_https = os.environ.get("https_proxy")
            old_all = os.environ.get("all_proxy")
            try:
                os.environ["http_proxy"] = proxy
                os.environ["https_proxy"] = proxy
                os.environ["all_proxy"] = proxy
                yield
            finally:
                if old_http is None:
                    os.environ.pop("http_proxy", None)
                else:
                    os.environ["http_proxy"] = old_http
                if old_https is None:
                    os.environ.pop("https_proxy", None)
                else:
                    os.environ["https_proxy"] = old_https
                if old_all is None:
                    os.environ.pop("all_proxy", None)
                else:
                    os.environ["all_proxy"] = old_all
