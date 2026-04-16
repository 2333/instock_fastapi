#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BaoStock 数据提供器

用于 BaoStock 单源抓取，并在提供器内执行 IP 级请求预算约束。
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

from app.utils.stock_codes import normalize_ts_code

from .base import AdjustType, ProxyPool

logger = logging.getLogger(__name__)


@dataclass
class BaoStockConfig:
    min_delay: float = 0.05


class BaoStockProvider:
    _lock = threading.Lock()
    _budget_lock = threading.Lock()
    _logged_in = False
    _last_request_ts = 0.0
    _public_ip: str | None = None

    def __init__(
        self,
        config: Optional[BaoStockConfig] = None,
        proxy_pool: Optional[ProxyPool] = None,
    ):
        self.config = config or BaoStockConfig()
        if proxy_pool is not None:
            logger.warning("BaoStockProvider ignores proxy_pool to keep a stable internet IP")
        self.proxy_pool = None

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
        try:
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
                raise RuntimeError(f"BaoStock 查询失败 {bs_code}: {rs.error_msg}")
        except Exception:
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

    async def fetch_stock_list(self, include_industry: bool = True) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(
            self._fetch_security_list_sync,
            "1",
            include_industry=include_industry,
        )

    async def fetch_etf_list(self, include_industry: bool = True) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(
            self._fetch_security_list_sync,
            "5",
            include_industry=include_industry,
        )

    async def fetch_stock_classifications(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_stock_classification_sync)

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
            error_code = getattr(login_result, "error_code", "-1")
            if error_code != "0":
                if error_code == "10001011":
                    raise RuntimeError("BaoStock 登录失败: 当前公网 IP 已进入黑名单控制 (error_code=10001011)")
                raise RuntimeError(f"BaoStock 登录失败: {login_result.error_msg}")
            self._logged_in = True

    def _fetch_security_list_sync(
        self,
        security_type: str,
        *,
        include_industry: bool = True,
    ) -> List[Dict[str, Any]]:
        try:
            import baostock as bs  # type: ignore
        except Exception:
            logger.warning("baostock 未安装，跳过 BaoStock 数据源")
            return []

        try:
            self._ensure_login(bs)
            self._wait_rate_limit()
            basic_rs = bs.query_stock_basic()
            if basic_rs.error_code != "0":
                raise RuntimeError(f"BaoStock query_stock_basic 失败: {basic_rs.error_msg}")
            basic_rows = self._collect_rows(basic_rs)

            industry_map: dict[str, str] = {}
            if include_industry:
                self._wait_rate_limit()
                industry_rs = bs.query_stock_industry()
                if industry_rs.error_code == "0":
                    for row in self._collect_rows(industry_rs):
                        if len(row) < 4:
                            continue
                        code = str(row[1]).strip()
                        industry = str(row[3]).strip()
                        if code:
                            industry_map[code] = industry
                else:
                    logger.warning("BaoStock query_stock_industry 失败: %s", industry_rs.error_msg)
        except Exception:
            raise

        items: List[Dict[str, Any]] = []
        for row in basic_rows:
            if len(row) < 6:
                continue
            code = str(row[0]).strip()
            if not code or str(row[4]).strip() != security_type or str(row[5]).strip() != "1":
                continue
            symbol = code.split(".", 1)[-1] if "." in code else code
            exchange = code.split(".", 1)[0].upper() if "." in code else ""
            items.append(
                {
                    "code": symbol,
                    "symbol": symbol,
                    "ts_code": f"{symbol}.{exchange.upper()}",
                    "exchange": exchange.upper(),
                    "name": str(row[1]).strip(),
                    "industry": industry_map.get(code) if include_industry else None,
                    "market": "ETF" if security_type == "5" else "A",
                    "list_date": self._normalize_basic_date(row[2]),
                    "delist_date": self._normalize_basic_date(row[3]),
                }
            )
        logger.info("BaoStock %s 列表拉取完成: %s 条", "ETF" if security_type == "5" else "A股", len(items))
        return items

    def _fetch_stock_classification_sync(self) -> List[Dict[str, Any]]:
        try:
            import baostock as bs  # type: ignore
        except Exception:
            logger.warning("baostock 未安装，跳过 BaoStock 数据源")
            return []

        try:
            self._ensure_login(bs)
            self._wait_rate_limit()
            industry_rs = bs.query_stock_industry()
            if industry_rs.error_code != "0":
                logger.warning("BaoStock query_stock_industry 失败: %s", industry_rs.error_msg)
                return []

            items: List[Dict[str, Any]] = []
            for row in self._collect_rows(industry_rs):
                if len(row) < 3:
                    continue
                code = str(row[1]).strip()
                if not code:
                    continue
                if "." in code:
                    exchange, symbol = code.split(".", 1)
                    normalized_ts_code = normalize_ts_code(
                        None,
                        symbol=symbol,
                        exchange=exchange,
                    )
                else:
                    normalized_ts_code = normalize_ts_code(code)

                items.append(
                    {
                        "ts_code": normalized_ts_code,
                        "industry_label": str(row[3]).strip() if len(row) > 3 else None,
                        "industry_taxonomy": (
                            str(row[4]).strip() if len(row) > 4 else None
                        ),
                        "industry_source": "baostock",
                        "update_date": str(row[0]).strip() if row else None,
                    }
                )

            logger.info("BaoStock 行业分类拉取完成: %s 条", len(items))
            return items
        except Exception:
            raise

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

    def _collect_rows(self, rs: Any) -> List[List[str]]:
        rows: List[List[str]] = []
        while getattr(rs, "error_code", "-1") == "0" and rs.next():
            row = rs.get_row_data()
            if row:
                rows.append(row)
        return rows

    def _normalize_basic_date(self, value: Any) -> Optional[str]:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return datetime.strptime(raw, "%Y-%m-%d").strftime("%Y%m%d")
        except ValueError:
            return raw

    def _wait_rate_limit(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_ts
            if elapsed < self.config.min_delay:
                time.sleep(self.config.min_delay - elapsed)
            self._last_request_ts = time.monotonic()
        self._record_request_usage()

    def _record_request_usage(self) -> None:
        budget = max(1, int(os.getenv("BAOSTOCK_DAILY_REQUEST_BUDGET", "90000")))
        counter_file = Path(
            os.getenv("BAOSTOCK_REQUEST_COUNTER_FILE", "runtime/baostock_request_counter.json")
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        public_ip = self._get_public_ip()
        key = f"{today}:{public_ip}"

        with self._budget_lock:
            payload: dict[str, int] = {}
            if counter_file.exists():
                try:
                    payload = json.loads(counter_file.read_text(encoding="utf-8"))
                except Exception:
                    payload = {}

            current = int(payload.get(key, 0))
            if current + 1 > budget:
                raise RuntimeError(
                    "BaoStock request budget exceeded "
                    f"(date={today}, public_ip={public_ip}, count={current}, budget={budget})"
                )

            payload = {k: int(v) for k, v in payload.items() if k.startswith(today)}
            payload[key] = current + 1
            counter_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _get_public_ip(self) -> str:
        if self._public_ip:
            return self._public_ip
        configured = os.getenv("BAOSTOCK_INTERNET_IP", "").strip()
        if configured:
            self._public_ip = configured
            return configured
        try:
            with urlopen("https://api.ipify.org", timeout=3) as response:
                self._public_ip = response.read().decode("utf-8").strip() or "unknown"
        except Exception:
            self._public_ip = "unknown"
        return self._public_ip
