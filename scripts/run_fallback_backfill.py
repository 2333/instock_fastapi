import asyncio
import logging
import os

from app.jobs.tasks.fetch_daily_task import run_historical_fallback_backfill


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


async def main() -> None:
    round_no = 0
    while True:
        round_no += 1
        print(f"fallback-backfill-round={round_no}", flush=True)
        done = await run_historical_fallback_backfill()
        if done:
            print("fallback-backfill-finished", flush=True)
            return


if __name__ == "__main__":
    asyncio.run(main())
