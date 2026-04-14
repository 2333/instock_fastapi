from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.jobs.tasks.calculate_technical_factors_task import (
    TECHNICAL_FACTOR_SOURCE,
    build_technical_factor_rows,
    run_technical_factors_backfill_window,
)
from app.models.stock_model import Base, DailyBar, Stock, TechnicalFactor
from tests.conftest import async_engine_test, async_session_factory_test


def _bar(ts_code: str, trade_date: date, close: str) -> DailyBar:
    close_value = Decimal(close)
    return DailyBar(
        ts_code=ts_code,
        trade_date=trade_date.strftime("%Y%m%d"),
        trade_date_dt=trade_date,
        open=close_value - Decimal("0.20"),
        high=close_value + Decimal("0.50"),
        low=close_value - Decimal("0.50"),
        close=close_value,
        pre_close=close_value - Decimal("0.10"),
        change=Decimal("0.10"),
        pct_chg=Decimal("1.00"),
        vol=Decimal("1000"),
        amount=Decimal("10000"),
    )


def test_build_technical_factor_rows_uses_daily_bars_only():
    rows = build_technical_factor_rows(
        [
            _bar("000001.SZ", date(2024, 1, 2), "10"),
            _bar("000001.SZ", date(2024, 1, 3), "11"),
            _bar("000001.SZ", date(2024, 1, 4), "12"),
            _bar("000001.SZ", date(2024, 1, 5), "13"),
            _bar("000001.SZ", date(2024, 1, 8), "14"),
        ],
        start_date="20240108",
    )

    assert len(rows) == 1
    factors = rows[0]["factors"]
    assert factors["source"] == TECHNICAL_FACTOR_SOURCE
    assert factors["close"] == 14.0
    assert factors["ma5"] == 12.0
    assert factors["window_count"] == 5


@pytest.mark.asyncio
async def test_technical_factors_backfill_window_writes_local_factors():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                exchange="SZ",
                list_status="L",
                is_etf=False,
            )
        )
        session.add_all(
            [
                _bar("000001.SZ", date(2024, 1, 2), "10"),
                _bar("000001.SZ", date(2024, 1, 3), "11"),
                _bar("000001.SZ", date(2024, 1, 4), "12"),
                _bar("000001.SZ", date(2024, 1, 5), "13"),
                _bar("000001.SZ", date(2024, 1, 8), "14"),
            ]
        )
        await session.commit()

    result = await run_technical_factors_backfill_window(
        start_date="2024-01-08",
        end_date="2024-01-08",
        code_limit=1,
        execute=True,
        session_factory=async_session_factory_test,
    )

    async with async_session_factory_test() as session:
        factors = (await session.execute(select(TechnicalFactor))).scalars().all()

    assert result["source"] == TECHNICAL_FACTOR_SOURCE
    assert result["saved_rows"] == 1
    assert len(factors) == 1
    assert factors[0].factors["source"] == TECHNICAL_FACTOR_SOURCE
    assert factors[0].factors["ma5"] == 12.0

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
