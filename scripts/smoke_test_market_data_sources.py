#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


@dataclass
class SmokeCase:
    name: str
    run: Callable[[], dict[str, Any]]


def _result(name: str, started_at: float, ok: bool, **details: Any) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 2),
        **details,
    }


def _run_case(case: SmokeCase) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        payload = case.run()
        return _result(case.name, started_at, True, **payload)
    except Exception as exc:  # pragma: no cover - manual smoke script
        return _result(case.name, started_at, False, error=repr(exc))


def _baostock_cases() -> list[SmokeCase]:
    import baostock as bs  # type: ignore

    login_result = bs.login()
    if getattr(login_result, "error_code", "-1") != "0":
        raise RuntimeError(f"BaoStock login failed: {login_result.error_msg}")

    def query_rows(query_result: Any, limit: int | None = None) -> list[list[str]]:
        rows: list[list[str]] = []
        while query_result.error_code == "0" and query_result.next():
            rows.append(query_result.get_row_data())
            if limit is not None and len(rows) >= limit:
                break
        return rows

    return [
        SmokeCase(
            "baostock.trade_dates",
            lambda: {
                "fields": ["calendar_date", "is_trading_day"],
                "rows": len(
                    rows := query_rows(
                        bs.query_trade_dates(
                            start_date="2024-01-01",
                            end_date="2024-01-10",
                        )
                    )
                ),
                "sample": rows[:3],
            },
        ),
        SmokeCase(
            "baostock.stock_basic",
            lambda: {
                "fields": ["code", "code_name", "ipoDate", "outDate", "type", "status"],
                "rows": len(rows := query_rows(bs.query_stock_basic(code="sh.600000"))),
                "sample": rows[:3],
            },
        ),
        SmokeCase(
            "baostock.etf_basic",
            lambda: {
                "fields": ["code", "code_name", "ipoDate", "outDate", "type", "status"],
                "rows": len(rows := query_rows(bs.query_stock_basic(code="sh.510300"))),
                "sample": rows[:3],
            },
        ),
        SmokeCase(
            "baostock.industry",
            lambda: {
                "fields": ["updateDate", "code", "code_name", "industry", "industryClassification"],
                "rows": len(rows := query_rows(bs.query_stock_industry(), limit=5)),
                "sample": rows[:5],
            },
        ),
        SmokeCase(
            "baostock.all_stock",
            lambda: {
                "fields": ["code", "tradeStatus", "code_name"],
                "rows": len(rows := query_rows(bs.query_all_stock(day="2024-10-25"), limit=5)),
                "sample": rows[:5],
            },
        ),
        SmokeCase(
            "baostock.daily_kline_qfq",
            lambda: {
                "fields": [
                    "date",
                    "code",
                    "open",
                    "high",
                    "low",
                    "close",
                    "preclose",
                    "volume",
                    "amount",
                    "adjustflag",
                    "turn",
                    "tradestatus",
                    "pctChg",
                    "peTTM",
                    "pbMRQ",
                    "psTTM",
                    "pcfNcfTTM",
                    "isST",
                ],
                "rows": len(
                    rows := query_rows(
                        bs.query_history_k_data_plus(
                            "sz.000001",
                            "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,peTTM,pbMRQ,psTTM,pcfNcfTTM,isST",
                            start_date="2024-01-02",
                            end_date="2024-01-05",
                            frequency="d",
                            adjustflag="2",
                        )
                    )
                ),
                "sample": rows[:2],
            },
        ),
    ]


def _akshare_cases() -> list[SmokeCase]:
    import akshare as ak  # type: ignore

    return [
        SmokeCase(
            "akshare.trade_calendar",
            lambda: {
                "rows": len(df := ak.tool_trade_date_hist_sina()),
                "columns": list(df.columns),
                "sample": df.tail(2).astype(str).to_dict(orient="records"),
            },
        ),
        SmokeCase(
            "akshare.stock_list",
            lambda: {
                "rows": len(df := ak.stock_info_a_code_name()),
                "columns": list(df.columns),
                "sample": df.head(3).to_dict(orient="records"),
            },
        ),
        SmokeCase(
            "akshare.daily_hist_qfq",
            lambda: {
                "rows": len(
                    df := ak.stock_zh_a_hist(
                        symbol="000001",
                        period="daily",
                        start_date="20240102",
                        end_date="20240105",
                        adjust="qfq",
                    )
                ),
                "columns": list(df.columns),
                "sample": df.head(2).to_dict(orient="records"),
            },
        ),
        SmokeCase(
            "akshare.fund_flow_rank",
            lambda: {
                "rows": len(df := ak.stock_individual_fund_flow_rank(indicator="今日")),
                "columns": list(df.columns),
                "sample": df.head(2).to_dict(orient="records"),
            },
        ),
        SmokeCase(
            "akshare.lhb_detail",
            lambda: {
                "rows": len(df := ak.stock_lhb_detail_em(start_date="20240401", end_date="20240403")),
                "columns": list(df.columns),
                "sample": df.head(2).to_dict(orient="records"),
            },
        ),
        SmokeCase(
            "akshare.block_trade_daily",
            lambda: {
                "rows": len(df := ak.stock_dzjy_mrtj(start_date="20240401", end_date="20240401")),
                "columns": list(df.columns),
                "sample": df.head(2).to_dict(orient="records"),
            },
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run live smoke checks for market data sources used by this project"
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        choices=("baostock", "akshare"),
        default=("baostock", "akshare"),
        help="providers to check",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report: dict[str, Any] = {"providers": {}, "all_ok": True}

    for provider in args.providers:
        started_at = time.perf_counter()
        provider_report: dict[str, Any] = {
            "installed": False,
            "elapsed_ms": 0.0,
            "cases": [],
            "all_ok": False,
        }
        try:
            cases = _baostock_cases() if provider == "baostock" else _akshare_cases()
            provider_report["installed"] = True
            provider_report["cases"] = [_run_case(case) for case in cases]
            provider_report["all_ok"] = all(item["ok"] for item in provider_report["cases"])
        except Exception as exc:  # pragma: no cover - manual smoke script
            provider_report["error"] = repr(exc)
        provider_report["elapsed_ms"] = round(
            (time.perf_counter() - started_at) * 1000, 2
        )
        report["providers"][provider] = provider_report
        report["all_ok"] = report["all_ok"] and provider_report["all_ok"]

    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0 if report["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
