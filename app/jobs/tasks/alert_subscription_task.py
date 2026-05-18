"""Post-close alert subscription runner for M3-B."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import async_session_factory
from app.jobs.market_calendar import (
    current_market_date,
    format_trade_date,
    is_trading_day,
    should_skip_market_task,
)
from app.jobs.scheduler import _get_daily_bar_coverage_status
from app.models.stock_model import AlertRun, AlertSubscription, SelectionCondition
from app.services.alert_subscription_service import AlertSubscriptionService
from app.services.screener_registry import get_rule_registry_map

logger = logging.getLogger(__name__)


def _normalize_trade_date(trade_date: str) -> str:
    return trade_date.replace("-", "").strip()


async def _load_due_subscription_targets(
    *,
    trade_date: str,
    limit: int | None = None,
) -> list[tuple[int, int]]:
    existing_run = (
        select(AlertRun.id)
        .where(
            AlertRun.subscription_id == AlertSubscription.id,
            AlertRun.definition_hash == AlertSubscription.definition_hash,
            func.replace(AlertRun.trade_date, "-", "") == _normalize_trade_date(trade_date),
        )
        .exists()
    )
    stmt = (
        select(AlertSubscription.id, AlertSubscription.user_id)
        .where(
            AlertSubscription.status == "active",
            AlertSubscription.schedule_type == "post_close",
            ~existing_run,
        )
        .order_by(AlertSubscription.id.asc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)

    async with async_session_factory() as session:
        rows = (await session.execute(stmt)).all()
    return [(int(subscription_id), int(user_id)) for subscription_id, user_id in rows]


async def has_due_post_close_runs(trade_date: str) -> bool:
    return bool(await _load_due_subscription_targets(trade_date=trade_date, limit=1))


def _pattern_rule_keys() -> set[str]:
    return {
        rule_key
        for rule_key, rule in get_rule_registry_map().items()
        if rule.get("status") == "active" and rule.get("maps_to_filter_key") == "pattern"
    }


def _definition_uses_pattern_rule(definition: Any) -> bool:
    pattern_rule_keys = _pattern_rule_keys()
    if not pattern_rule_keys:
        return False

    def walk(value: Any) -> bool:
        if isinstance(value, dict):
            rule_key = value.get("rule_key")
            if isinstance(rule_key, str) and rule_key in pattern_rule_keys:
                return True
            if value.get("pattern") is not None:
                return True
            return any(walk(child) for child in value.values())
        if isinstance(value, (list, tuple)):
            return any(walk(item) for item in value)
        return False

    return walk(definition)


async def _due_subscriptions_require_pattern_readiness(trade_date: str) -> bool:
    existing_run = (
        select(AlertRun.id)
        .where(
            AlertRun.subscription_id == AlertSubscription.id,
            AlertRun.definition_hash == AlertSubscription.definition_hash,
            func.replace(AlertRun.trade_date, "-", "") == _normalize_trade_date(trade_date),
        )
        .exists()
    )
    stmt = (
        select(SelectionCondition.params)
        .select_from(AlertSubscription)
        .join(
            SelectionCondition,
            SelectionCondition.id == AlertSubscription.selection_condition_id,
        )
        .where(
            AlertSubscription.status == "active",
            AlertSubscription.schedule_type == "post_close",
            SelectionCondition.is_active.is_(True),
            SelectionCondition.definition_version == AlertSubscription.definition_version,
            SelectionCondition.definition_hash == AlertSubscription.definition_hash,
            ~existing_run,
        )
    )

    async with async_session_factory() as session:
        definitions = (await session.execute(stmt)).scalars().all()
    return any(_definition_uses_pattern_rule(definition or {}) for definition in definitions)


async def _has_daily_data_for_trade_date(trade_date: str) -> bool:
    async with async_session_factory() as session:
        count = (
            await session.execute(
                text("""
                    SELECT COUNT(*) AS row_count
                    FROM daily_bars
                    WHERE REPLACE(COALESCE(trade_date, ''), '-', '') = REPLACE(:trade_date, '-', '')
                    """),
                {"trade_date": trade_date},
            )
        ).scalar_one()
    return int(count or 0) > 0


def _parse_pattern_audit_note(note: str | None) -> dict[str, int]:
    values: dict[str, int] = {}
    if not note:
        return values

    for part in note.split(";"):
        key, separator, value = part.strip().partition("=")
        if not separator:
            continue
        try:
            values[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return values


def _validate_pattern_audit_note(note: str | None) -> tuple[bool, str, dict[str, int]]:
    metrics = _parse_pattern_audit_note(note)
    required_keys = {
        "expected",
        "evaluated",
        "skipped_insufficient_history",
        "failed",
        "matched_stocks",
        "patterns",
    }
    if not required_keys <= metrics.keys():
        return False, "patterns_audit_incomplete", metrics

    expected = metrics["expected"]
    evaluated = metrics["evaluated"]
    skipped = metrics["skipped_insufficient_history"]
    failed = metrics["failed"]
    matched_stocks = metrics["matched_stocks"]
    patterns = metrics["patterns"]
    if expected <= 0:
        return False, "patterns_audit_empty", metrics
    if min(evaluated, skipped, failed, matched_stocks, patterns) < 0:
        return False, "patterns_audit_invalid", metrics
    if failed > 0:
        return False, "patterns_not_ready", metrics
    if evaluated + skipped < expected:
        return False, "patterns_audit_incomplete", metrics
    return True, "patterns_ready", metrics


async def _get_pattern_evaluation_status(trade_date: str) -> dict[str, Any]:
    query = text("""
        SELECT status, note
        FROM data_fetch_audit
        WHERE task_name = 'pattern_recognition'
          AND entity_type = 'trade_date'
          AND entity_key = 'ALL'
          AND REPLACE(COALESCE(trade_date, ''), '-', '') = REPLACE(:trade_date, '-', '')
        ORDER BY updated_at DESC
        LIMIT 1
        """)

    async with async_session_factory() as session:
        try:
            row = (
                (await session.execute(query, {"trade_date": trade_date})).mappings().one_or_none()
            )
        except SQLAlchemyError:
            return {"ready": False, "reason": "patterns_audit_missing"}

    if row is None:
        return {"ready": False, "reason": "patterns_not_evaluated"}
    status = str(row["status"] or "")
    if status != "done":
        return {
            "ready": False,
            "reason": "patterns_not_ready",
            "status": status,
            "note": row.get("note"),
            "metrics": _parse_pattern_audit_note(row.get("note")),
        }

    ready, reason, metrics = _validate_pattern_audit_note(row.get("note"))
    return {
        "ready": ready,
        "reason": reason,
        "status": status,
        "note": row.get("note"),
        "metrics": metrics,
    }


async def _get_trade_date_readiness(
    trade_date: str,
    *,
    require_patterns: bool = False,
) -> dict[str, Any]:
    if not await _has_daily_data_for_trade_date(trade_date):
        return {"ready": False, "reason": "trade_date_not_ready"}

    coverage = await _get_daily_bar_coverage_status(trade_date)
    if int(coverage["expected_count"] or 0) <= 0:
        return {"ready": False, "reason": "market_universe_not_ready", "coverage": coverage}
    if bool(coverage["has_partial_gap"]):
        return {"ready": False, "reason": "trade_date_partial_gap", "coverage": coverage}
    if require_patterns:
        patterns_status = await _get_pattern_evaluation_status(trade_date)
        if not patterns_status["ready"]:
            return {
                "ready": False,
                "reason": patterns_status["reason"],
                "coverage": coverage,
                "patterns_status": patterns_status,
            }
    return {"ready": True, "coverage": coverage}


async def run(date: str | None = None, limit: int | None = None) -> dict[str, Any]:
    """Run active post-close subscriptions for a trade date.

    The task binds to existing AlertSubscription rows and delegates rule
    evaluation to AlertSubscriptionService so scheduler and manual runs share
    one authored truth and one dedupe contract.
    """

    target_date = date or format_trade_date(current_market_date())
    if date is None and should_skip_market_task(
        "告警订阅盘后检查任务",
        today_is_trading_day=await is_trading_day(target_date=current_market_date()),
    ):
        return {
            "status": "skipped",
            "trade_date": target_date,
            "reason": "non_trading_day",
            "attempted": 0,
            "completed": 0,
            "stale": 0,
            "failed": 0,
        }

    requires_pattern_readiness = await _due_subscriptions_require_pattern_readiness(target_date)
    readiness = await _get_trade_date_readiness(
        target_date,
        require_patterns=requires_pattern_readiness,
    )
    if not readiness["ready"]:
        logger.warning("告警订阅盘后检查跳过: %s readiness=%s", target_date, readiness)
        return {
            "status": "skipped",
            "trade_date": target_date,
            "reason": readiness["reason"],
            "coverage": readiness.get("coverage"),
            "patterns_status": readiness.get("patterns_status"),
            "attempted": 0,
            "completed": 0,
            "stale": 0,
            "failed": 0,
        }

    targets = await _load_due_subscription_targets(trade_date=target_date, limit=limit)
    summary: dict[str, Any] = {
        "status": "completed",
        "trade_date": target_date,
        "attempted": len(targets),
        "completed": 0,
        "stale": 0,
        "failed": 0,
        "errors": [],
        "started_at": datetime.utcnow().isoformat(),
    }

    for subscription_id, user_id in targets:
        async with async_session_factory() as session:
            service = AlertSubscriptionService(session)
            try:
                await service.run_subscription(
                    user_id=user_id,
                    subscription_id=subscription_id,
                    date=target_date,
                )
                summary["completed"] += 1
            except HTTPException as exc:
                if exc.status_code == 409:
                    summary["stale"] += 1
                    continue
                summary["failed"] += 1
                summary["errors"].append(
                    {
                        "subscription_id": subscription_id,
                        "status_code": exc.status_code,
                        "detail": exc.detail,
                    }
                )
                logger.warning(
                    "Alert subscription run failed: subscription_id=%s status=%s detail=%s",
                    subscription_id,
                    exc.status_code,
                    exc.detail,
                )
            except Exception as exc:  # pragma: no cover - defensive task boundary
                summary["failed"] += 1
                summary["errors"].append(
                    {
                        "subscription_id": subscription_id,
                        "detail": str(exc),
                    }
                )
                logger.exception(
                    "Unexpected alert subscription task failure: subscription_id=%s",
                    subscription_id,
                )

    summary["completed_at"] = datetime.utcnow().isoformat()
    if summary["failed"]:
        summary["status"] = "completed_with_errors"
    return summary
