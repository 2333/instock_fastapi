#!/usr/bin/env python3
"""Non-mutating API contract smoke checks for the current runtime baseline."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any
from urllib import error, parse, request


@dataclass(frozen=True)
class Check:
    method: str
    path: str
    expected_statuses: tuple[int, ...]
    params: dict[str, Any] | None = None
    payload: dict[str, Any] | None = None


PUBLIC_READ_CHECKS = (
    Check("GET", "/health", (200,)),
    Check("GET", "/api/v1/info", (200,)),
    Check("GET", "/api/v1/stocks", (200,), params={"page": 1, "page_size": 3, "date": "20260420"}),
    Check(
        "GET",
        "/api/v1/stocks/000001",
        (200,),
        params={"start_date": "20260401", "end_date": "20260420", "adjust": "bfq"},
    ),
    Check("GET", "/api/v1/etf", (200,), params={"page": 1, "page_size": 3, "date": "20260420"}),
    Check("GET", "/api/v1/etf/510300", (200,)),
    Check(
        "GET",
        "/api/v1/facts/daily-basic",
        (200,),
        params={"page": 1, "page_size": 3, "date": "20260420"},
    ),
    Check(
        "GET",
        "/api/v1/facts/stock-st",
        (200,),
        params={"page": 1, "page_size": 3, "date": "20260420"},
    ),
    Check(
        "GET",
        "/api/v1/facts/technical-factors",
        (200,),
        params={"page": 1, "page_size": 3, "date": "20260420"},
    ),
    Check("GET", "/api/v1/indicators", (200,), params={"code": "000001", "limit": 3}),
    Check("GET", "/api/v1/indicators/latest", (200,), params={"code": "000001"}),
    Check("GET", "/api/v1/patterns", (200,), params={"code": "000001", "limit": 3}),
    Check("GET", "/api/v1/patterns/today", (200,), params={"limit": 3}),
    Check("GET", "/api/v1/fund-flow/000001", (200,), params={"days": 3}),
    Check(
        "GET",
        "/api/v1/fund-flow/sector/industry",
        (200,),
        params={"date": "20260420", "limit": 3},
    ),
    Check(
        "GET",
        "/api/v1/fund-flow/sector/concept",
        (200,),
        params={"date": "20260420", "limit": 3},
    ),
    Check("GET", "/api/v1/market/summary", (200,), params={"date": "20260420"}),
    Check("GET", "/api/v1/market/fund-flow", (200,), params={"date": "20260420", "limit": 3}),
    Check("GET", "/api/v1/market/block-trades", (200,), params={"date": "20260420", "limit": 3}),
    Check("GET", "/api/v1/market/lhb", (200,), params={"date": "20260420", "limit": 3}),
    Check("GET", "/api/v1/market/north-bound", (200,), params={"date": "20260420", "limit": 3}),
    Check("GET", "/api/v1/market/task-health", (200,), params={"alert_limit": 3}),
    Check("GET", "/api/v1/selection/conditions", (200,)),
    Check("GET", "/api/v1/screening/metadata", (200,)),
    Check("GET", "/api/v1/selection/templates", (200,)),
    Check("GET", "/api/v1/strategies", (200,)),
    Check("GET", "/api/v1/strategies/templates", (200,)),
    Check("GET", "/api/v1/strategies/results", (200,), params={"limit": 3}),
)

PROTECTED_CHECKS = (
    Check("GET", "/api/v1/auth/me", (401,)),
    Check("GET", "/api/v1/auth/settings", (401,)),
    Check("GET", "/api/v1/selection/my-conditions", (401,)),
    Check("GET", "/api/v1/selection/history", (401,), params={"limit": 3}),
    Check("GET", "/api/v1/screening/history", (401,), params={"limit": 3}),
    Check("GET", "/api/v1/selection/today-summary", (401,), params={"date": "20260420", "limit": 3}),
    Check("GET", "/api/v1/strategies/my", (401,)),
    Check("GET", "/api/v1/attention", (401,)),
    Check("GET", "/api/v1/backtest/history", (401,), params={"limit": 3}),
    Check("GET", "/api/v1/backtest/bt-1", (401,)),
    Check("GET", "/api/v1/backtest/tasks", (401,), params={"limit": 3}),
    Check("GET", "/api/v1/backtest/tasks/demo-task", (401,)),
    Check("POST", "/api/v1/events/track", (401,), payload={"event_type": "page_view", "page": "/stocks"}),
    Check(
        "POST",
        "/api/v1/backtest",
        (401,),
        payload={
            "strategy": "enter",
            "start_date": "20240101",
            "end_date": "20240131",
            "initial_capital": 100000,
        },
    ),
    Check(
        "POST",
        "/api/v1/backtest/async",
        (401,),
        payload={
            "strategy": "enter",
            "start_date": "20240101",
            "end_date": "20240131",
            "initial_capital": 100000,
        },
    ),
    Check("POST", "/api/v1/selection", (401,), payload={"filters": {}, "scope": {"limit": 10}}),
    Check("POST", "/api/v1/screening/run", (401,), payload={"filters": {}, "scope": {"limit": 10}}),
    Check("POST", "/api/v1/screening/compare", (401,), payload={"history_ids": ["demo"]}),
    Check("POST", "/api/v1/strategies/my", (401,), payload={"name": "demo"}),
    Check(
        "POST",
        "/api/v1/strategies/my/from-selection",
        (401,),
        payload={"name": "demo", "params": {"source": "selection"}},
    ),
    Check("POST", "/api/v1/attention", (401,), payload={"code": "000001"}),
    Check("PUT", "/api/v1/auth/settings", (401,), payload={"language": "zh-CN"}),
    Check(
        "PUT",
        "/api/v1/selection/my-conditions/1",
        (401,),
        payload={"name": "demo", "category": "basic", "params": {}, "is_active": True},
    ),
    Check("PUT", "/api/v1/strategies/my/1", (401,), payload={"name": "demo"}),
    Check("PUT", "/api/v1/attention/1", (401,), payload={"group": "watch"}),
    Check("DELETE", "/api/v1/selection/my-conditions/1", (401,)),
    Check("DELETE", "/api/v1/strategies/my/1", (401,)),
    Check("DELETE", "/api/v1/attention/000001", (401,)),
)

SAFE_POST_CHECKS = (
    Check("POST", "/api/v1/auth/login", (401,), payload={"username": "nobody", "password": "wrong"}),
    Check("POST", "/api/v1/auth/refresh", (401,), payload={"refresh_token": "bad-token"}),
    Check("POST", "/api/v1/strategies/run", (200,), payload={"strategy": "enter", "date": "20260420"}),
)


def run_check(base_url: str, check: Check) -> dict[str, Any]:
    query = parse.urlencode(check.params or {})
    url = f"{base_url}{check.path}"
    if query:
        url = f"{url}?{query}"

    data = None
    headers = {}
    if check.payload is not None:
        data = json.dumps(check.payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, method=check.method, data=data, headers=headers)

    try:
        with request.urlopen(req, timeout=15) as response:
            body = response.read().decode("utf-8", errors="replace")
            status = response.status
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        status = exc.code
    except Exception as exc:  # pragma: no cover - operator-facing fallback
        return {
            "ok": False,
            "method": check.method,
            "path": check.path,
            "status": "ERROR",
            "expected": list(check.expected_statuses),
            "body": str(exc),
        }

    return {
        "ok": status in check.expected_statuses,
        "method": check.method,
        "path": check.path,
        "status": status,
        "expected": list(check.expected_statuses),
        "body": body[:160],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    checks = (*PUBLIC_READ_CHECKS, *PROTECTED_CHECKS, *SAFE_POST_CHECKS)
    results = [run_check(args.base_url.rstrip("/"), check) for check in checks]
    failures = [item for item in results if not item["ok"]]

    print(json.dumps(results, ensure_ascii=False, indent=2))
    if failures:
        print(
            f"[error] {len(failures)} API contract checks failed",
            file=sys.stderr,
        )
        return 1

    print(f"[ok] {len(results)} API contract checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
