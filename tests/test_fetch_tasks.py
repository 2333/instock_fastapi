from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text
from sqlalchemy import select

from app.jobs.tasks import fetch_daily_task, fetch_fund_flow_task
from app.jobs.tasks.fetch_daily_task import _ensure_backfill_state_table, save_stocks
from app.models.stock_model import Base, DailyBar, Stock
from tests.conftest import async_engine_test, async_session_factory_test


@pytest.mark.asyncio
async def test_fetch_sector_data_uses_fallback_chain(monkeypatch):
    fetch_by_source = AsyncMock()
    fetch_with_fallback = AsyncMock(return_value=([{"name": "AI"}], "20260310"))
    monkeypatch.setattr(fetch_fund_flow_task, "_fetch_sector_by_source", fetch_by_source)
    monkeypatch.setattr(fetch_fund_flow_task, "_fetch_sector_with_fallback", fetch_with_fallback)

    data, trade_date, used_source = await fetch_fund_flow_task._fetch_sector_data(
        tushare_provider=object(),
        baostock_provider=object(),
        crawler=object(),
        sector_type="industry",
        trade_dates=["20260310"],
        source="fallback",
        primary_only=False,
    )

    assert data == [{"name": "AI"}]
    assert trade_date == "20260310"
    assert used_source == "fallback"
    fetch_by_source.assert_not_awaited()
    fetch_with_fallback.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_daily_bars_routes_etf_directly_to_eastmoney(monkeypatch):
    monkeypatch.setenv("INLINE_FALLBACK_ENABLED", "false")
    tushare = AsyncMock()
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock(return_value=[{"date": "2026-03-13", "close": 1}])

    bars, source, status, note = await fetch_daily_task._fetch_bars_with_fallback(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        symbol="159001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="SZ",
        is_etf=True,
    )

    assert bars == [{"date": "2026-03-13", "close": 1}]
    assert source == "eastmoney"
    assert status == "done"
    assert note == ""
    eastmoney.fetch.assert_awaited_once()
    tushare.fetch_kline.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_daily_bars_routes_bj_directly_to_eastmoney(monkeypatch):
    monkeypatch.setenv("INLINE_FALLBACK_ENABLED", "false")
    tushare = AsyncMock()
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock(return_value=[{"date": "2026-03-13", "close": 1}])

    bars, source, status, note = await fetch_daily_task._fetch_bars_with_fallback(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        symbol="920000",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="BJ",
        is_etf=False,
    )

    assert bars == [{"date": "2026-03-13", "close": 1}]
    assert source == "eastmoney"
    assert status == "done"
    assert note == ""
    eastmoney.fetch.assert_awaited_once()
    tushare.fetch_kline.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()


@pytest.mark.asyncio
async def test_save_stocks_migrates_legacy_ts_code_without_duplicates():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000001.SZSE",
                symbol="000001",
                name="平安银行",
                area="深圳",
                industry="银行",
                market="主板",
                exchange="SZSE",
                list_status="L",
                is_etf=False,
            )
        )
        session.add(
            DailyBar(
                ts_code="000001.SZSE",
                trade_date="20240102",
                trade_date_dt=None,
                open=Decimal("10.50"),
                high=Decimal("10.80"),
                low=Decimal("10.30"),
                close=Decimal("10.60"),
                pre_close=Decimal("10.40"),
                change=Decimal("0.20"),
                pct_chg=Decimal("1.92"),
                vol=Decimal("50000000"),
                amount=Decimal("525000000"),
            )
        )
        await session.commit()

        count = await save_stocks(
            session,
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "exchange": "SZ",
                }
            ],
        )

        stocks = (
            await session.execute(select(Stock).where(Stock.symbol == "000001").order_by(Stock.ts_code))
        ).scalars().all()
        bars = (await session.execute(select(DailyBar.ts_code))).scalars().all()

    assert count == 1
    assert len(stocks) == 1
    assert stocks[0].ts_code == "000001.SZ"
    assert stocks[0].exchange == "SZ"
    assert bars == ["000001.SZ"]

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_ensure_backfill_state_table_creates_table():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        await _ensure_backfill_state_table(session)
        await session.execute(
            text(
                """
            INSERT INTO backfill_daily_state (ts_code, status)
            VALUES ('000001.SZ', 'needs_fallback')
            """
            )
        )
        await session.commit()

        result = await session.execute(text("SELECT COUNT(*) FROM backfill_daily_state"))
        assert result.scalar_one() == 1

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
