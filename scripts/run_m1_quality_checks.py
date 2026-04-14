#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.database import async_session_factory
from app.jobs.m1_quality_runner import (
    has_quality_failures,
    run_m1_quality_checks,
    summarize_quality_results,
)


async def _run(sample_limit: int) -> dict:
    async with async_session_factory() as session:
        results = await run_m1_quality_checks(session, sample_limit=sample_limit)
    return summarize_quality_results(results)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run M1 data quality checks")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="Maximum number of date buckets / duplicate samples to return per check",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the full structured payload as JSON",
    )
    args = parser.parse_args()

    summary = asyncio.run(_run(args.sample_limit))

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, default=str, indent=2))
    else:
        counts = summary["status_counts"]
        print(
            f"total_checks={summary['total_checks']} ok={counts.get('ok', 0)} "
            f"warn={counts.get('warn', 0)} fail={counts.get('fail', 0)}"
        )
        for item in summary["results"]:
            print(
                f"{item['status']:>4} {item['table']:<32} {item['check']}: {item['value']}"
            )

    return 1 if has_quality_failures(summary["results"]) else 0


if __name__ == "__main__":
    sys.exit(main())
