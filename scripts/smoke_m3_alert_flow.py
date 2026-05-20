#!/usr/bin/env python3
"""Authenticated M3 alert-flow smoke for staging-like environments."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    pass


def _request(
    base_url: str,
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    expected: set[int] | None = None,
) -> tuple[int, Any]:
    expected = expected or {200}
    url = f"{base_url.rstrip('/')}{path}"
    if query:
        url = f"{url}?{urlencode(query)}"

    data = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8")
    except URLError as exc:
        raise SmokeFailure(f"{method} {path} failed to connect: {exc}") from exc

    try:
        body = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        body = raw

    if status not in expected:
        raise SmokeFailure(f"{method} {path} returned {status}, expected {sorted(expected)}: {body}")
    return status, body


def _definition(rule_key: str, params: dict[str, Any], *, limit: int = 5) -> dict[str, Any]:
    return {
        "kind": "saved_screener",
        "scope": {"limit": limit},
        "root": {
            "type": "group",
            "op": "all",
            "children": [{"type": "predicate", "rule_key": rule_key, "params": params}],
        },
    }


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def run(base_url: str) -> dict[str, Any]:
    suffix = str(int(time.time()))
    username = f"m3_stage_{suffix}"
    password = "M3-stage-smoke-123456"

    _request(
        base_url,
        "POST",
        "/api/v1/auth/register",
        json_body={
            "username": username,
            "email": f"{username}@example.test",
            "password": password,
        },
        expected={201},
    )
    _, login = _request(
        base_url,
        "POST",
        "/api/v1/auth/login",
        json_body={"username": username, "password": password},
    )
    token = login["access_token"]

    _, metadata = _request(base_url, "GET", "/api/v1/screening/metadata")
    filter_keys = [field["key"] for field in metadata["data"]["filter_fields"]]
    _assert("rsiMin" in filter_keys and "pattern" in filter_keys, "M3 filter metadata is incomplete")

    rsi_definition = _definition("rsiMin", {"value": 0, "period": 14})
    pattern_definition = _definition("pattern", {"value": "DOJI"})

    _, rsi_screen = _request(
        base_url,
        "POST",
        "/api/v1/screening/run",
        token=token,
        json_body={"definition": rsi_definition, "scope": {"limit": 5}},
    )
    rsi_items = rsi_screen["data"]["items"]
    _assert(len(rsi_items) > 0, "RSI screening returned no hits")

    _, pattern_screen = _request(
        base_url,
        "POST",
        "/api/v1/screening/run",
        token=token,
        json_body={"definition": pattern_definition, "scope": {"limit": 5}},
    )
    pattern_items = pattern_screen["data"]["items"]
    _assert(len(pattern_items) > 0, "Pattern screening returned no hits")

    _, rsi_condition = _request(
        base_url,
        "POST",
        "/api/v1/selection/my-conditions",
        token=token,
        json_body={
            "name": f"M3 RSI smoke {suffix}",
            "category": "technical",
            "description": "M3 staging authenticated smoke",
            "definition": rsi_definition,
        },
    )
    _, pattern_condition = _request(
        base_url,
        "POST",
        "/api/v1/selection/my-conditions",
        token=token,
        json_body={
            "name": f"M3 Pattern smoke {suffix}",
            "category": "pattern",
            "description": "M3 staging authenticated smoke",
            "definition": pattern_definition,
        },
    )

    _, rsi_subscription = _request(
        base_url,
        "POST",
        "/api/v1/alerts/subscriptions",
        token=token,
        json_body={
            "selection_condition_id": rsi_condition["id"],
            "name": f"M3 RSI subscription {suffix}",
            "cooldown_trade_days": 1,
        },
    )
    _, pattern_subscription = _request(
        base_url,
        "POST",
        "/api/v1/alerts/subscriptions",
        token=token,
        json_body={
            "selection_condition_id": pattern_condition["id"],
            "name": f"M3 Pattern subscription {suffix}",
            "cooldown_trade_days": 1,
        },
    )

    rsi_subscription_id = rsi_subscription["data"]["id"]
    pattern_subscription_id = pattern_subscription["data"]["id"]

    _, rsi_run = _request(
        base_url,
        "POST",
        f"/api/v1/alerts/subscriptions/{rsi_subscription_id}/run",
        token=token,
    )
    _, pattern_run = _request(
        base_url,
        "POST",
        f"/api/v1/alerts/subscriptions/{pattern_subscription_id}/run",
        token=token,
    )

    for label, run_payload in {"rsi": rsi_run, "pattern": pattern_run}.items():
        run_item = run_payload["data"]["run"]
        _assert(run_item["status"] == "completed", f"{label} run did not complete")
        _assert(run_item["match_count"] > 0, f"{label} run returned no matches")
        _assert(run_payload["data"]["notification"] is not None, f"{label} run produced no notification")
        _assert(len(run_payload["data"]["hits"]) == run_item["match_count"], f"{label} hit count mismatch")

    rsi_trade_date = rsi_run["data"]["run"]["trade_date"]
    first_run_id = rsi_run["data"]["run"]["id"]
    _, rsi_dedupe = _request(
        base_url,
        "POST",
        f"/api/v1/alerts/subscriptions/{rsi_subscription_id}/run",
        token=token,
        query={"date": rsi_trade_date},
    )
    _assert(rsi_dedupe["data"]["run"]["id"] == first_run_id, "same-day run was not deduped")

    _, notifications = _request(base_url, "GET", "/api/v1/notifications", token=token)
    rsi_notifications = [
        item for item in notifications["data"] if item["subscription_id"] == rsi_subscription_id
    ]
    _assert(len(rsi_notifications) == 1, "RSI subscription produced duplicate notifications")

    changed_definition = _definition("rsiMin", {"value": 1, "period": 14})
    _, updated_condition = _request(
        base_url,
        "PUT",
        f"/api/v1/selection/my-conditions/{rsi_condition['id']}",
        token=token,
        json_body={
            "name": rsi_condition["name"],
            "category": rsi_condition["category"],
            "description": rsi_condition["description"],
            "definition": changed_definition,
        },
    )
    _assert(updated_condition["definition_version"] > rsi_condition["definition_version"], "definition version did not increment")

    _, subscriptions = _request(base_url, "GET", "/api/v1/alerts/subscriptions", token=token)
    stale_rsi = next(item for item in subscriptions["data"] if item["id"] == rsi_subscription_id)
    _assert(stale_rsi["status"] == "stale", "changed screener did not mark subscription stale")

    _request(
        base_url,
        "POST",
        f"/api/v1/alerts/subscriptions/{rsi_subscription_id}/run",
        token=token,
        expected={409},
    )

    return {
        "user": username,
        "rsi_condition_id": rsi_condition["id"],
        "pattern_condition_id": pattern_condition["id"],
        "rsi_subscription_id": rsi_subscription_id,
        "pattern_subscription_id": pattern_subscription_id,
        "trade_date": rsi_trade_date,
        "rsi_match_count": rsi_run["data"]["run"]["match_count"],
        "pattern_match_count": pattern_run["data"]["run"]["match_count"],
        "rsi_notification_id": rsi_run["data"]["notification"]["id"],
        "pattern_notification_id": pattern_run["data"]["notification"]["id"],
        "deduped_run_id": first_run_id,
        "stale_status": stale_rsi["status"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    args = parser.parse_args()

    try:
        result = run(args.base_url)
    except SmokeFailure as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    print("[ok] M3 authenticated alert flow smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
