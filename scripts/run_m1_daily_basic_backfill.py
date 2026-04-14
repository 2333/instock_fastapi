#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.jobs.tasks.fetch_daily_basic_task import run_daily_basic_backfill_window


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a bounded M1 daily_basic backfill")
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--day-limit", type=int, default=1)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--execute", action="store_true", help="write data; default is dry-run")
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> dict:
    return await run_daily_basic_backfill_window(
        start_date=args.start_date,
        end_date=args.end_date,
        day_limit=args.day_limit,
        sleep_seconds=args.sleep_seconds,
        execute=args.execute,
    )


def main() -> int:
    args = parse_args()
    result = asyncio.run(_run(args))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
