from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.jobs.tasks.fetch_daily_basic_task import (
    run_daily_basic_backfill_window,
    save_daily_basic,
)
from app.models.stock_model import Base, DailyBasic
from tests.conftest import async_engine_test, async_session_factory_test


@pytest.mark.asyncio
async def test_save_daily_basic_inserts_and_updates_by_ts_code_trade_date_dt():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        inserted = await save_daily_basic(
            session,
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20240102",
                    "trade_date_dt": date(2024, 1, 2),
                    "turnover_rate": 1.23,
                    "pe": 12.34,
                }
            ],
        )
        await session.commit()

        updated = await save_daily_basic(
            session,
            [
                {
                    "ts_code": "000001.SZ",
                    "trade_date": "20240102",
                    "trade_date_dt": date(2024, 1, 2),
                    "turnover_rate": 2.34,
                    "pe": 10.5,
                }
            ],
        )
        await session.commit()

        rows = (await session.execute(select(DailyBasic))).scalars().all()

    assert inserted == 1
    assert updated == 1
    assert len(rows) == 1
    assert rows[0].turnover_rate == Decimal("2.340000")
    assert rows[0].pe == Decimal("10.500000")

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_daily_basic_backfill_window_dry_run_plans_weekdays_only():
    result = await run_daily_basic_backfill_window(
        start_date="2024-01-05",
        end_date="2024-01-09",
        day_limit=2,
        execute=False,
        session_factory=async_session_factory_test,
    )

    assert result["dry_run"] is True
    assert result["target_dates"] == ["20240105", "20240108"]
    assert result["fetched_rows"] == 0
    assert result["saved_rows"] == 0
