#!/usr/bin/env python3
"""Controlled M1 backfill rehearsal planner.

This script intentionally defaults to dry-run planning only. It produces a
small, auditable rehearsal plan for:

- `daily_bars` using an explicit selected source
- `daily_basic` as the first required M1 fact table rehearsal target
- `technical_factors` calculated locally from `daily_bars`

The plan records execution commands, manual gates, and verification queries
without making any live Tushare calls. It emits dry-run wrapper commands that
call job-layer functions; add `--execute` only after the manual gates pass.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from typing import Any


def _normalize_trade_date(value: str) -> str:
    normalized = value.strip().replace("-", "")
    if len(normalized) != 8 or not normalized.isdigit():
        raise ValueError(f"Invalid trade date: {value!r}")
    return normalized


def _iso_trade_date(value: str) -> str:
    normalized = _normalize_trade_date(value)
    return f"{normalized[:4]}-{normalized[4:6]}-{normalized[6:]}"


def _daily_bars_smoke_command(code: str, start_date: str, end_date: str) -> str:
    return (
        'curl -s "http://localhost:8000/api/v1/stocks/'
        f"{code}?start_date={start_date}&end_date={end_date}\""
    )


def _daily_basic_smoke_command(code: str, date: str) -> str:
    return (
        'curl -s "http://localhost:8000/api/v1/facts/daily-basic?'
        f"code={code}&date={date}&limit=5\""
    )


def _technical_factors_smoke_command(code: str, date: str) -> str:
    return (
        'curl -s "http://localhost:8000/api/v1/facts/technical-factors?'
        f"code={code}&date={date}&limit=5\""
    )


@dataclass(slots=True)
class VerificationQuery:
    name: str
    sql: str


@dataclass(slots=True)
class RehearsalStep:
    table: str
    mode: str
    command: str | None
    manual_gate: str
    verification_queries: list[VerificationQuery] = field(default_factory=list)
    smoke_command: str | None = None
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RehearsalPlan:
    dry_run: bool
    start_date: str
    end_date: str
    code_limit: int
    steps: list[RehearsalStep]
    manual_gates: list[str]
    shared_verification_queries: list[VerificationQuery]


def build_rehearsal_plan(
    start_date: str,
    end_date: str,
    code_limit: int = 20,
    dry_run: bool = True,
) -> RehearsalPlan:
    start = _normalize_trade_date(start_date)
    end = _normalize_trade_date(end_date)
    if start > end:
        raise ValueError("start_date must be <= end_date")
    if code_limit < 1:
        raise ValueError("code_limit must be >= 1")

    daily_bars_queries = [
        VerificationQuery(
            name="row_count",
            sql=(
                "SELECT COUNT(*) AS row_count "
                "FROM daily_bars "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}';"
            ),
        ),
        VerificationQuery(
            name="date_range",
            sql=(
                "SELECT MIN(trade_date_dt) AS min_trade_date_dt, "
                "MAX(trade_date_dt) AS max_trade_date_dt "
                "FROM daily_bars "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}';"
            ),
        ),
        VerificationQuery(
            name="duplicate_keys",
            sql=(
                "SELECT ts_code, trade_date_dt, COUNT(*) AS dup_count "
                "FROM daily_bars "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' "
                "GROUP BY ts_code, trade_date_dt "
                "HAVING COUNT(*) > 1 "
                "ORDER BY dup_count DESC, ts_code, trade_date_dt;"
            ),
        ),
    ]

    daily_basic_queries = [
        VerificationQuery(
            name="row_count",
            sql=(
                "SELECT COUNT(*) AS row_count "
                "FROM daily_basic "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}';"
            ),
        ),
        VerificationQuery(
            name="date_range",
            sql=(
                "SELECT MIN(trade_date_dt) AS min_trade_date_dt, "
                "MAX(trade_date_dt) AS max_trade_date_dt "
                "FROM daily_basic "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}';"
            ),
        ),
        VerificationQuery(
            name="duplicate_keys",
            sql=(
                "SELECT ts_code, trade_date_dt, COUNT(*) AS dup_count "
                "FROM daily_basic "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' "
                "GROUP BY ts_code, trade_date_dt "
                "HAVING COUNT(*) > 1 "
                "ORDER BY dup_count DESC, ts_code, trade_date_dt;"
            ),
        ),
    ]

    technical_factor_queries = [
        VerificationQuery(
            name="row_count",
            sql=(
                "SELECT COUNT(*) AS row_count "
                "FROM technical_factors "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}';"
            ),
        ),
        VerificationQuery(
            name="source_count",
            sql=(
                "SELECT factors ->> 'source' AS source, COUNT(*) AS row_count "
                "FROM technical_factors "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' "
                "GROUP BY factors ->> 'source' "
                "ORDER BY source;"
            ),
        ),
        VerificationQuery(
            name="duplicate_keys",
            sql=(
                "SELECT ts_code, trade_date_dt, COUNT(*) AS dup_count "
                "FROM technical_factors "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' "
                "GROUP BY ts_code, trade_date_dt "
                "HAVING COUNT(*) > 1 "
                "ORDER BY dup_count DESC, ts_code, trade_date_dt;"
            ),
        ),
    ]

    bars_step = RehearsalStep(
        table="daily_bars",
        mode="bounded-job-dry-run",
        command=(
            ".venv/bin/python scripts/run_m1_daily_bars_rehearsal.py "
            f"--start-date {start} --end-date {end} --code-limit {code_limit} --source baostock"
        ),
        manual_gate=(
            "Run without --execute first and inspect the target list. Add --execute "
            "only on a disposable database after confirming the selected source."
        ),
        verification_queries=daily_bars_queries,
        smoke_command=_daily_bars_smoke_command("000001.SZ", start, end),
        notes=[
            "Uses the job-layer run_daily_bars_backfill_window function.",
            "Uses an explicit single-source policy; rerun manually with another source if the configured source returns empty.",
            "Does not call scripts/backfill_2020_2025.py because that wrapper loops until complete.",
        ],
    )

    daily_basic_step = RehearsalStep(
        table="daily_basic",
        mode="bounded-job-dry-run",
        command=(
            ".venv/bin/python scripts/run_m1_daily_basic_backfill.py "
            f"--start-date {start} --end-date {end} --day-limit 1"
        ),
        manual_gate=(
            "Run without --execute first and inspect the target dates. Add --execute "
            "only on a disposable database after confirming Tushare token/permission access."
        ),
        verification_queries=daily_basic_queries,
        smoke_command=_daily_basic_smoke_command("000001", _iso_trade_date(start)),
        notes=[
            "Covers the required new M1 fact table in the rehearsal plan.",
            "Uses the job-layer run_daily_basic_backfill_window function.",
        ],
    )

    technical_factors_step = RehearsalStep(
        table="technical_factors",
        mode="bounded-local-calculation-dry-run",
        command=(
            ".venv/bin/python scripts/run_m1_technical_factors_backfill.py "
            f"--start-date {start} --end-date {end} --code-limit {code_limit}"
        ),
        manual_gate=(
            "Run after daily_bars exists for the same window. This step does not require "
            "Tushare token access because it calculates from local daily_bars."
        ),
        verification_queries=technical_factor_queries,
        smoke_command=_technical_factors_smoke_command("000001", _iso_trade_date(start)),
        notes=[
            "Covers the required M1 technical_factors table without external source dependency.",
            "Writes factors.source=daily_bars_local.",
        ],
    )

    shared_queries = [
        VerificationQuery(
            name="backfill_state",
            sql=(
                "SELECT status, COUNT(*) AS count "
                "FROM backfill_daily_state "
                "GROUP BY status "
                "ORDER BY status;"
            ),
        ),
        VerificationQuery(
            name="daily_bars_null_trade_date_dt",
            sql=(
                "SELECT COUNT(*) AS null_trade_date_dt "
                "FROM daily_bars "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' AND trade_date_dt IS NULL;"
            ),
        ),
        VerificationQuery(
            name="daily_basic_null_trade_date_dt",
            sql=(
                "SELECT COUNT(*) AS null_trade_date_dt "
                "FROM daily_basic "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' AND trade_date_dt IS NULL;"
            ),
        ),
        VerificationQuery(
            name="technical_factors_null_trade_date_dt",
            sql=(
                "SELECT COUNT(*) AS null_trade_date_dt "
                "FROM technical_factors "
                f"WHERE trade_date BETWEEN '{start}' AND '{end}' AND trade_date_dt IS NULL;"
            ),
        ),
    ]

    manual_gates = [
        "Confirm the target database is disposable or otherwise safe to write.",
        "Confirm Tushare token/point tier before any Tushare-sourced live backfill execution.",
        "Confirm each command runs with one explicit source only; switch sources by rerunning the job, not by inline fallback.",
        "Do not use scripts/backfill_2020_2025.py as the bounded daily_bars rehearsal command; it loops until complete.",
        "Do not widen the date window beyond the rehearsed range without re-running the duplicate-key checks.",
        "Run the rehearsal wrapper commands without --execute before running them with --execute.",
    ]

    return RehearsalPlan(
        dry_run=dry_run,
        start_date=start,
        end_date=end,
        code_limit=code_limit,
        steps=[bars_step, daily_basic_step, technical_factors_step],
        manual_gates=manual_gates,
        shared_verification_queries=shared_queries,
    )


def plan_to_dict(plan: RehearsalPlan) -> dict[str, Any]:
    return {
        "dry_run": plan.dry_run,
        "start_date": plan.start_date,
        "end_date": plan.end_date,
        "code_limit": plan.code_limit,
        "manual_gates": plan.manual_gates,
        "shared_verification_queries": [asdict(item) for item in plan.shared_verification_queries],
        "steps": [
            {
                "table": step.table,
                "mode": step.mode,
                "command": step.command,
                "manual_gate": step.manual_gate,
                "verification_queries": [asdict(item) for item in step.verification_queries],
                "smoke_command": step.smoke_command,
                "notes": step.notes,
            }
            for step in plan.steps
        ],
    }


def render_plan(plan: RehearsalPlan) -> str:
    data = plan_to_dict(plan)
    lines = [
        "# M1 Backfill Rehearsal Plan",
        "",
        f"- Dry run: `{data['dry_run']}`",
        f"- Date window: `{data['start_date']}` to `{data['end_date']}`",
        f"- Code limit: `{data['code_limit']}`",
        "",
        "## Manual Gates",
    ]
    lines.extend(f"- {item}" for item in data["manual_gates"])
    lines.append("")
    lines.append("## Steps")
    for step in data["steps"]:
        lines.append(f"### {step['table']}")
        lines.append(f"- Mode: `{step['mode']}`")
        if step["command"]:
            lines.append(f"- Command: `{step['command']}`")
        lines.append(f"- Manual gate: {step['manual_gate']}")
        if step["smoke_command"]:
            lines.append(f"- Smoke command: `{step['smoke_command']}`")
        if step["notes"]:
            lines.append("- Notes:")
            lines.extend(f"  - {note}" for note in step["notes"])
        lines.append("- Verification queries:")
        for query in step["verification_queries"]:
            lines.append(f"  - {query['name']}:")
            lines.append(f"    ```sql\n    {query['sql']}\n    ```")
    lines.append("")
    lines.append("## Shared Verification Queries")
    for query in data["shared_verification_queries"]:
        lines.append(f"- {query['name']}:")
        lines.append(f"  ```sql\n  {query['sql']}\n  ```")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the M1 backfill rehearsal plan")
    parser.add_argument("--start-date", required=True, help="Start date in YYYYMMDD or YYYY-MM-DD")
    parser.add_argument("--end-date", required=True, help="End date in YYYYMMDD or YYYY-MM-DD")
    parser.add_argument(
        "--code-limit",
        type=int,
        default=20,
        help="Target maximum number of codes for a future bounded rehearsal command",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the plan as JSON instead of markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    plan = build_rehearsal_plan(
        start_date=args.start_date,
        end_date=args.end_date,
        code_limit=args.code_limit,
        dry_run=True,
    )

    if args.json:
        print(json.dumps(plan_to_dict(plan), ensure_ascii=False, indent=2))
    else:
        print(render_plan(plan))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
