#!/usr/bin/env python3
import asyncio
import os

from app.jobs.tasks.fetch_daily_task import run_historical_backfill


async def main() -> None:
    # 默认覆盖 2020-01-01 到 2025-12-31，可通过环境变量覆盖
    os.environ.setdefault("BACKFILL_START_DATE", "20200101")
    os.environ.setdefault("BACKFILL_END_DATE", "20251231")
    os.environ.setdefault("BACKFILL_BATCH_SIZE", "200")
    os.environ.setdefault("BACKFILL_ITEM_SLEEP", "0.03")

    # 连续执行，直到完整回补完成后自动退出。
    while True:
        done = await run_historical_backfill()
        if done:
            break
        await asyncio.sleep(10)


if __name__ == "__main__":
    asyncio.run(main())
