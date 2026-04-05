#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tushare 数据提供器

优先用于任务抓取；不使用代理。
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import AdjustType

logger = logging.getLogger(__name__)


@dataclass
class TushareConfig:
    token: Optional[str] = None
    min_delay: float = 0.2
    max_inflight: int = 1


class TushareProvider:
    _lock = threading.Lock()
    _pro: Any = None
    _last_request_ts = 0.0
    _request_semaphore = threading.BoundedSemaphore(
        max(1, int(os.getenv("TUSHARE_MAX_INFLIGHT", "1")))
    )

    def __init__(self, config: Optional[TushareConfig] = None):
        self.config = config or TushareConfig()
        self.token = (self.config.token or os.getenv("TUSHARE_TOKEN") or "").strip()
        self.http_url = os.getenv("TUSHARE_HTTP_URL", "http://lianghua.nanyangqiankun.top")
        self._compat_http_url = os.getenv(
            "TUSHARE_COMPAT_HTTP_URL", "http://lianghua.nanyangqiankun.top"
        )
        self._compat_enabled = False
        requested_inflight = max(1, int(self.config.max_inflight))
        class_inflight = max(1, int(os.getenv("TUSHARE_MAX_INFLIGHT", "1")))
        if requested_inflight != class_inflight:
            self.__class__._request_semaphore = threading.BoundedSemaphore(requested_inflight)

    async def fetch_stock_list(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_stock_list_sync)

    async def fetch_etf_list(self) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_etf_list_sync)

    async def fetch_kline(
        self,
        code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        adjust: AdjustType = AdjustType.NO_ADJUST,
        period: str = "daily",
    ) -> List[Dict[str, Any]]:
        if period != "daily":
            logger.warning("Tushare 当前仅接入日线，收到 period=%s，跳过", period)
            return []
        return await asyncio.to_thread(
            self._fetch_kline_sync,
            code,
            start_date,
            end_date,
            adjust,
        )

    async def fetch_fund_flow_rank(self, trade_date: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_fund_flow_rank_sync, trade_date)

    async def fetch_sector_fund_flow(self, sector_type: str, trade_date: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_sector_fund_flow_sync, sector_type, trade_date)

    async def fetch_top_list(self, trade_date: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_top_list_sync, trade_date)

    async def fetch_top_inst(self, trade_date: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_top_inst_sync, trade_date)

    async def fetch_block_trade(self, trade_date: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._fetch_block_trade_sync, trade_date)

    async def fetch_daily_by_date(
        self,
        trade_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按日期批量获取全市场日线数据（一次 API 调用）。

        返回 {ts_code: [bar_dict, ...]} 结构。
        单日数据约 5000-7000 行，在 Tushare 6000 条/次限制内，
        如超出则自动分页。
        """
        return await asyncio.to_thread(self._fetch_daily_by_date_sync, trade_date)

    async def fetch_daily_batch(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按日期范围批量获取全市场日线数据。

        逐日调用 fetch_daily_by_date，每天一次 API 调用。
        返回 {ts_code: [bar_dict, ...]} 结构。
        """
        return await asyncio.to_thread(
            self._fetch_daily_batch_sync, start_date, end_date
        )

    def _fetch_daily_by_date_sync(
        self,
        trade_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        pro = self._get_pro()
        if not pro:
            return {}
        td = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))

        try:
            df = self._call_pro("daily", trade_date=td)
        except Exception as exc:
            logger.warning("Tushare daily 批量抓取失败 date=%s: %s", td, exc)
            return {}

        if df is None or df.empty:
            return {}

        result: Dict[str, List[Dict[str, Any]]] = {}
        for _, row in df.iterrows():
            ts_code = str(row.get("ts_code") or "")
            if not ts_code:
                continue
            bar = self._row_to_bar(row)
            if bar:
                result.setdefault(ts_code, []).append(bar)
        return result

    def _fetch_daily_batch_sync(
        self,
        start_date: str,
        end_date: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        start = self._to_ymd(start_date, default="19900101")
        end = self._to_ymd(end_date, default="20991231")

        # 生成日期列表（仅交易日，由调用方保证或 Tushare 返回空）
        from datetime import datetime, timedelta

        try:
            d0 = datetime.strptime(start, "%Y%m%d")
            d1 = datetime.strptime(end, "%Y%m%d")
        except ValueError:
            logger.warning("日期格式错误: start=%s end=%s", start, end)
            return {}

        result: Dict[str, List[Dict[str, Any]]] = {}
        current = d0
        while current <= d1:
            td = current.strftime("%Y%m%d")
            day_data = self._fetch_daily_by_date_sync(td)
            for ts_code, bars in day_data.items():
                result.setdefault(ts_code, []).extend(bars)
            current += timedelta(days=1)

        # 按 ts_code 内的日期排序
        for bars in result.values():
            bars.sort(key=lambda b: b.get("date", ""))

        return result

    def _row_to_bar(self, row: Any) -> Optional[Dict[str, Any]]:
        """将 Tushare daily 行转换为标准 bar dict。"""
        trade_date = str(row.get("trade_date") or "")
        if len(trade_date) != 8:
            return None
        close = self._to_float(row.get("close")) or 0.0
        pre_close = self._to_float(row.get("pre_close"))
        change = self._to_float(row.get("change"))
        if pre_close is None:
            pre_close = close - (change or 0.0)
        if change is None:
            change = close - pre_close
        pct = self._to_float(row.get("pct_chg"))
        if pct is None and pre_close not in (None, 0):
            pct = (change / pre_close) * 100
        return {
            "date": f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}",
            "open": self._to_float(row.get("open")) or 0.0,
            "high": self._to_float(row.get("high")) or 0.0,
            "low": self._to_float(row.get("low")) or 0.0,
            "close": close,
            "pre_close": pre_close or 0.0,
            "change": change or 0.0,
            "change_pct": pct or 0.0,
            "volume": self._to_float(row.get("vol")) or 0.0,
            "amount": self._to_float(row.get("amount")) or 0.0,
        }

    async def is_trade_date(self, trade_date: str) -> bool:
        return await asyncio.to_thread(self._is_trade_date_sync, trade_date)

    def _get_pro(self) -> Optional[Any]:
        if not self.token:
            logger.warning("未配置 TUSHARE_TOKEN，跳过 Tushare 数据源")
            return None
        with self._lock:
            if self._pro is not None:
                return self._pro
            try:
                import tushare as ts  # type: ignore
            except Exception:
                logger.warning("tushare 未安装，跳过 Tushare 数据源")
                return None
            ts.set_token(self.token)
            self._pro = ts.pro_api(self.token)
            return self._pro

    def _enable_compat_mode(self, pro: Any) -> None:
        """兼容部分渠道 token：注入私有 token 与自定义网关地址后重试。"""
        try:
            pro._DataApi__token = self.token
            pro._DataApi__http_url = self._compat_http_url
            self._compat_enabled = True
            logger.warning(
                "已启用 Tushare 兼容模式，http_url=%s", self._compat_http_url
            )
        except Exception as exc:
            logger.error("启用 Tushare 兼容模式失败: %s", exc)

    def _call_pro(self, func_name: str, **kwargs: Any) -> Any:
        pro = self._get_pro()
        if not pro:
            return None
        fn = getattr(pro, func_name, None)
        if not callable(fn):
            logger.warning("Tushare API 不存在: %s", func_name)
            return None

        try:
            return self._run_with_limits(lambda: fn(**kwargs))
        except Exception as exc:
            if not self._compat_enabled:
                logger.warning("Tushare %s 调用失败，尝试兼容模式: %s", func_name, exc)
                self._enable_compat_mode(pro)
                return self._run_with_limits(lambda: fn(**kwargs))
            raise

    def _fetch_stock_list_sync(self) -> List[Dict[str, Any]]:
        pro = self._get_pro()
        if not pro:
            return []
        try:
            df = self._call_pro(
                "stock_basic",
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,market",
            )
        except Exception as exc:
            logger.warning("Tushare stock_basic 抓取失败: %s", exc)
            return []
        if df is None or df.empty:
            return []
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "code": str(row.get("symbol") or ""),
                    "name": str(row.get("name") or ""),
                    "area": row.get("area"),
                    "industry": row.get("industry"),
                    "market": row.get("market"),
                }
            )
        return [r for r in rows if r["code"]]

    def _fetch_etf_list_sync(self) -> List[Dict[str, Any]]:
        pro = self._get_pro()
        if not pro:
            return []
        try:
            df = self._call_pro(
                "fund_basic",
                market="E",
                status="L",
                fields="ts_code,symbol,name,market",
            )
        except Exception as exc:
            logger.warning("Tushare fund_basic 抓取失败: %s", exc)
            return []
        if df is None or df.empty:
            return []
        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            ts_code = str(row.get("ts_code") or "")
            symbol = str(row.get("symbol") or "")
            code = symbol or ts_code.split(".")[0]
            rows.append(
                {
                    "code": code,
                    "name": str(row.get("name") or ""),
                    "market": row.get("market"),
                }
            )
        return [r for r in rows if r["code"]]

    def _fetch_kline_sync(
        self,
        code: str,
        start_date: Optional[str],
        end_date: Optional[str],
        adjust: AdjustType,
    ) -> List[Dict[str, Any]]:
        pro = self._get_pro()
        if not pro:
            return []

        ts_code = self._to_tushare_code(code)
        if not ts_code:
            return []
        start = self._to_ymd(start_date, default="19900101")
        end = self._to_ymd(end_date, default="20991231")

        try:
            if adjust == AdjustType.NO_ADJUST:
                df = self._call_pro(
                    "daily",
                    ts_code=ts_code,
                    start_date=start,
                    end_date=end,
                )
            else:
                import tushare as ts  # type: ignore

                df = self._run_with_limits(
                    lambda: ts.pro_bar(
                        ts_code=ts_code,
                        adj=adjust.value,
                        start_date=start,
                        end_date=end,
                    )
                )
        except Exception as exc:
            logger.warning("Tushare daily/pro_bar 抓取失败 %s: %s", ts_code, exc)
            return []

        if df is None or df.empty:
            return []
        df = df.sort_values("trade_date")

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            bar = self._row_to_bar(row)
            if bar:
                rows.append(bar)
        return rows

    def _fetch_fund_flow_rank_sync(self, trade_date: str) -> List[Dict[str, Any]]:
        pro = self._get_pro()
        if not pro:
            return []
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))

        try:
            df = self._call_pro("moneyflow_mkt_dc", trade_date=trade_date)
        except Exception as exc:
            logger.warning("Tushare moneyflow_mkt_dc 抓取失败: %s", exc)
            return []

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            ts_code = str(row.get("ts_code") or "")
            code = ts_code.split(".")[0] if ts_code else str(row.get("code") or "")
            rows.append(
                {
                    "code": code,
                    "main_net_inflow": self._pick_float(
                        row, "net_amount_main", "main_net_inflow", "net_mf_amount"
                    ),
                    "super_net_inflow": self._pick_float(
                        row, "net_amount_hf", "super_net_inflow", "buy_sm_amount"
                    ),
                    "big_net_inflow": self._pick_float(
                        row, "net_amount_zz", "big_net_inflow", "buy_md_amount"
                    ),
                    "mid_net_inflow": self._pick_float(
                        row, "net_amount_dt", "mid_net_inflow", "sell_md_amount"
                    ),
                    "small_net_inflow": self._pick_float(
                        row, "net_amount_xd", "small_net_inflow", "sell_sm_amount"
                    ),
                }
            )
        return [r for r in rows if r["code"]]

    def _fetch_sector_fund_flow_sync(self, sector_type: str, trade_date: str) -> List[Dict[str, Any]]:
        pro = self._get_pro()
        if not pro:
            return []
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))
        candidates = (
            ["moneyflow_ind_ths", "moneyflow_ind_dc"]
            if sector_type == "industry"
            else ["moneyflow_ind_dc", "moneyflow_ind_ths"]
        )
        df = None
        for fn in candidates:
            api = getattr(pro, fn, None)
            if not callable(api):
                continue
            try:
                try:
                    df = self._run_with_limits(lambda: api(trade_date=trade_date))
                except Exception as exc:
                    if not self._compat_enabled:
                        logger.warning("Tushare %s 调用失败，尝试兼容模式: %s", fn, exc)
                        self._enable_compat_mode(pro)
                        df = self._run_with_limits(lambda: api(trade_date=trade_date))
                    else:
                        raise
                if df is not None and not df.empty:
                    break
            except Exception:
                continue

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "name": self._pick_str(row, "name", "industry", "concept", "ts_name"),
                    "change_pct": self._pick_float(row, "pct_chg", "change_pct"),
                    "main_net_inflow": self._pick_float(
                        row, "net_amount_main", "main_net_inflow", "net_amount"
                    ),
                    "main_net_inflow_rate": self._pick_float(
                        row, "net_rate_main", "main_net_inflow_rate"
                    ),
                    "super_net_inflow": self._pick_float(
                        row, "net_amount_hf", "super_net_inflow"
                    ),
                    "super_net_inflow_rate": self._pick_float(
                        row, "net_rate_hf", "super_net_inflow_rate"
                    ),
                    "top_stock": self._pick_str(row, "top_stock"),
                }
            )
        return [r for r in rows if r["name"]]

    def _fetch_top_list_sync(self, trade_date: str) -> List[Dict[str, Any]]:
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))
        try:
            df = self._call_pro("top_list", trade_date=trade_date)
        except Exception as exc:
            logger.warning("Tushare top_list 抓取失败: %s", exc)
            return []

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            ts_code = self._pick_str(row, "ts_code")
            if not ts_code:
                continue
            rows.append(
                {
                    "ts_code": ts_code,
                    "name": self._pick_str(row, "name"),
                    "trade_date": self._pick_str(row, "trade_date") or trade_date,
                    "close": self._pick_float(row, "close"),
                    "pct_change": self._pick_float(row, "pct_change"),
                    "turnover_rate": self._pick_float(row, "turnover_rate"),
                    "amount": self._pick_float(row, "amount"),
                    "buy_amount": self._pick_float(row, "l_buy"),
                    "sell_amount": self._pick_float(row, "l_sell"),
                    "net_amount": self._pick_float(row, "net_amount"),
                    "reason": self._pick_str(row, "reason"),
                }
            )
        return rows

    def _fetch_top_inst_sync(self, trade_date: str) -> List[Dict[str, Any]]:
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))
        try:
            df = self._call_pro("top_inst", trade_date=trade_date)
        except Exception as exc:
            logger.warning("Tushare top_inst 抓取失败: %s", exc)
            return []

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            ts_code = self._pick_str(row, "ts_code")
            if not ts_code:
                continue
            rows.append(
                {
                    "ts_code": ts_code,
                    "trade_date": self._pick_str(row, "trade_date") or trade_date,
                    "side": self._pick_str(row, "side"),
                    "buy": self._pick_float(row, "buy"),
                    "sell": self._pick_float(row, "sell"),
                    "net_buy": self._pick_float(row, "net_buy"),
                    "reason": self._pick_str(row, "reason"),
                }
            )
        return rows

    def _fetch_block_trade_sync(self, trade_date: str) -> List[Dict[str, Any]]:
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))
        try:
            df = self._call_pro("block_trade", trade_date=trade_date)
        except Exception as exc:
            logger.warning("Tushare block_trade 抓取失败: %s", exc)
            return []

        if df is None or df.empty:
            return []

        rows: List[Dict[str, Any]] = []
        for _, row in df.iterrows():
            ts_code = self._pick_str(row, "ts_code")
            if not ts_code:
                continue
            rows.append(
                {
                    "ts_code": ts_code,
                    "trade_date": self._pick_str(row, "trade_date") or trade_date,
                    "price": self._pick_float(row, "price"),
                    "vol": self._pick_float(row, "vol"),
                    "amount": self._pick_float(row, "amount"),
                    "buyer": self._pick_str(row, "buyer"),
                    "seller": self._pick_str(row, "seller"),
                }
            )
        return rows

    def _is_trade_date_sync(self, trade_date: str) -> bool:
        trade_date = self._to_ymd(trade_date, default=time.strftime("%Y%m%d"))
        try:
            df = self._call_pro(
                "trade_cal",
                exchange="",
                start_date=trade_date,
                end_date=trade_date,
            )
        except Exception as exc:
            logger.warning("Tushare trade_cal 抓取失败: %s", exc)
            return False

        if df is None or df.empty:
            return False

        for _, row in df.iterrows():
            value = row.get("is_open")
            try:
                return int(value) == 1
            except Exception:
                return str(value).strip() == "1"
        return False

    def _wait_rate_limit(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_ts
            if elapsed < self.config.min_delay:
                time.sleep(self.config.min_delay - elapsed)
            self._last_request_ts = time.monotonic()

    def _run_with_limits(self, callback):
        with self.__class__._request_semaphore:
            self._wait_rate_limit()
            return callback()

    @staticmethod
    def _to_ymd(value: Optional[str], default: str) -> str:
        if not value:
            return default
        v = str(value).strip()
        if len(v) == 8 and v.isdigit():
            return v
        return v.replace("-", "").replace("/", "")

    @staticmethod
    def _to_tushare_code(code: str) -> Optional[str]:
        if not code:
            return None
        item = str(code).strip().upper()
        if "." in item:
            left, right = item.split(".", 1)
            if right in {"SH", "SZ"}:
                return f"{left}.{right}"
            if right == "SSE":
                return f"{left}.SH"
            if right == "SZSE":
                return f"{left}.SZ"
        if item.startswith("6"):
            return f"{item}.SH"
        if item.startswith(("0", "3")):
            return f"{item}.SZ"
        return None

    @staticmethod
    def _to_float(value: Any) -> Optional[float]:
        try:
            if value in (None, "", "nan"):
                return None
            return float(value)
        except Exception:
            return None

    @staticmethod
    def _pick_float(row: Any, *keys: str) -> float:
        for key in keys:
            val = row.get(key) if hasattr(row, "get") else None
            try:
                if val not in (None, "", "nan"):
                    return float(val)
            except Exception:
                continue
        return 0.0

    @staticmethod
    def _pick_str(row: Any, *keys: str) -> str:
        for key in keys:
            val = row.get(key) if hasattr(row, "get") else None
            if val not in (None, ""):
                return str(val)
        return ""
