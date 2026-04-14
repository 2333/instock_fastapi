#!/usr/bin/env python3
"""Timescale health checks for M1.

Checks:
- Timescale extension availability
- hypertable registration for core fact tables
- chunk existence
- compression enabled
- compression policy presence
- representative EXPLAIN plans for core fact reads

Manual live execution:
  .venv/bin/python scripts/timescale_health_check.py
  .venv/bin/python scripts/timescale_health_check.py --json

The script is intentionally lightweight. If the connected database is not
PostgreSQL/Timescale, every check is returned with status ``skipped``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy import text

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

CORE_TABLES = ("daily_bars", "fund_flows", "indicators", "patterns")
PLAN_CHECKS = (
    (
        "daily_bars_window",
        """
        EXPLAIN
        SELECT *
        FROM daily_bars
        WHERE ts_code = :ts_code
          AND trade_date_dt BETWEEN :start_date_dt AND :end_date_dt
        ORDER BY trade_date_dt DESC
        LIMIT 5
        """,
        {
            "ts_code": "000001.SZ",
            "start_date_dt": date(2024, 1, 1),
            "end_date_dt": date(2024, 1, 31),
        },
    ),
    (
        "fund_flows_rank",
        """
        EXPLAIN
        SELECT *
        FROM fund_flows
        WHERE trade_date_dt = :trade_date_dt
        ORDER BY net_amount_main DESC NULLS LAST
        LIMIT 5
        """,
        {"trade_date_dt": date(2024, 1, 2)},
    ),
)


@dataclass(frozen=True)
class CheckResult:
    check: str
    status: str
    table: str | None = None
    value: Any = None
    details: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "table": self.table,
            "value": self.value,
            "details": self.details,
        }


def _dialect_name(session: Any) -> str | None:
    bind = getattr(session, "bind", None)
    dialect = getattr(bind, "dialect", None)
    return getattr(dialect, "name", None)


def _skip_results() -> list[CheckResult]:
    results: list[CheckResult] = [
        CheckResult(
            check="extension.timescaledb",
            status="skipped",
            details="non_postgresql_dialect",
        )
    ]
    for table in CORE_TABLES:
        results.extend(
            [
                CheckResult(
                    check="hypertable.registered",
                    table=table,
                    status="skipped",
                    details="non_postgresql_dialect",
                ),
                CheckResult(
                    check="hypertable.chunk_count",
                    table=table,
                    status="skipped",
                    details="non_postgresql_dialect",
                ),
                CheckResult(
                    check="hypertable.compression_enabled",
                    table=table,
                    status="skipped",
                    details="non_postgresql_dialect",
                ),
                CheckResult(
                    check="hypertable.compression_policy",
                    table=table,
                    status="skipped",
                    details="non_postgresql_dialect",
                ),
            ]
        )
    for plan_name, _, _ in PLAN_CHECKS:
        results.append(
            CheckResult(
                check=f"plan.{plan_name}",
                status="skipped",
                details="non_postgresql_dialect",
            )
        )
    return results


def _rows_to_plan_text(rows: list[Any]) -> list[str]:
    plan_lines: list[str] = []
    for row in rows:
        if isinstance(row, tuple):
            plan_lines.append(str(row[0]))
        else:
            plan_lines.append(str(row))
    return plan_lines


async def _scalar(session: Any, sql: str, params: dict[str, Any] | None = None) -> Any:
    result = await session.execute(text(sql), params or {})
    if hasattr(result, "scalar_one_or_none"):
        return result.scalar_one_or_none()
    if hasattr(result, "scalar_one"):
        return result.scalar_one()
    if hasattr(result, "scalar"):
        return result.scalar()
    return None


async def _fetch_rows(session: Any, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
    result = await session.execute(text(sql), params or {})
    if hasattr(result, "fetchall"):
        return result.fetchall()
    if hasattr(result, "all"):
        return result.all()
    return []


async def run_timescale_health_checks(session: Any) -> list[dict[str, Any]]:
    dialect_name = _dialect_name(session)
    if dialect_name not in {"postgresql", "postgres"}:
        return [result.as_dict() for result in _skip_results()]

    results: list[CheckResult] = []

    extension_enabled = bool(
        await _scalar(
            session,
            """
            SELECT EXISTS(
                SELECT 1
                FROM pg_extension
                WHERE extname = 'timescaledb'
            )
            """,
        )
    )
    results.append(
        CheckResult(
            check="extension.timescaledb",
            status="ok" if extension_enabled else "fail",
            value=extension_enabled,
            details="pg_extension",
        )
    )

    for table in CORE_TABLES:
        hypertable_registered = bool(
            await _scalar(
                session,
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = :table
                )
                """,
                {"table": table},
            )
        )
        chunk_count = await _scalar(
            session,
            """
            SELECT COUNT(*)
            FROM timescaledb_information.chunks
            WHERE hypertable_name = :table
            """,
            {"table": table},
        )
        compression_enabled = bool(
            await _scalar(
                session,
                """
                SELECT COALESCE(compression_enabled, false)
                FROM timescaledb_information.hypertables
                WHERE hypertable_name = :table
                """,
                {"table": table},
            )
        )
        compression_policy = bool(
            await _scalar(
                session,
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM timescaledb_information.jobs
                    WHERE hypertable_name = :table
                      AND proc_name = 'policy_compression'
                )
                """,
                {"table": table},
            )
        )

        results.extend(
            [
                CheckResult(
                    check="hypertable.registered",
                    table=table,
                    status="ok" if hypertable_registered else "fail",
                    value=hypertable_registered,
                    details="timescaledb_information.hypertables",
                ),
                CheckResult(
                    check="hypertable.chunk_count",
                    table=table,
                    status="ok" if (chunk_count or 0) > 0 else "fail",
                    value=int(chunk_count or 0),
                    details="timescaledb_information.chunks",
                ),
                CheckResult(
                    check="hypertable.compression_enabled",
                    table=table,
                    status="ok" if compression_enabled else "fail",
                    value=compression_enabled,
                    details="timescaledb_information.hypertables",
                ),
                CheckResult(
                    check="hypertable.compression_policy",
                    table=table,
                    status="ok" if compression_policy else "fail",
                    value=compression_policy,
                    details="timescaledb_information.jobs",
                ),
            ]
        )

    for plan_name, sql, params in PLAN_CHECKS:
        plan_rows = await _fetch_rows(session, sql, params)
        plan_lines = _rows_to_plan_text(plan_rows)
        results.append(
            CheckResult(
                check=f"plan.{plan_name}",
                status="ok" if plan_lines else "fail",
                value=plan_lines,
                details="representative explain output",
            )
        )

    return [result.as_dict() for result in results]


async def _run_cli(json_output: bool = False) -> int:
    from app.database import async_session_factory

    async with async_session_factory() as session:
        results = await run_timescale_health_checks(session)

    if json_output:
        print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
    else:
        for item in results:
            table = f" table={item['table']}" if item.get("table") else ""
            print(f"{item['status']:<8} {item['check']}{table} value={item.get('value')!r}")

    failed = any(item["status"] == "fail" for item in results)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M1 Timescale health checks")
    parser.add_argument("--json", action="store_true", help="print JSON results")
    args = parser.parse_args()
    return asyncio.run(_run_cli(json_output=args.json))


if __name__ == "__main__":
    raise SystemExit(main())
