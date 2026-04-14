from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text

from app.jobs import market_calendar
from app.jobs.tasks import fetch_daily_task, fetch_fund_flow_task
from app.jobs.tasks.fetch_daily_task import (
    _ensure_backfill_state_table,
    run_daily_bars_backfill_window,
    save_stocks,
)
from app.jobs.tasks.fetch_market_reference_task import summarize_block_trades, summarize_top_list
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
async def test_fetch_daily_bars_uses_tushare_pro_bar_before_fallback(monkeypatch):
    monkeypatch.setenv("INLINE_FALLBACK_ENABLED", "true")
    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock(return_value=[{"date": "2026-03-13", "close": 1}])
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    bars, source, status, note = await fetch_daily_task._fetch_bars_with_fallback(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        symbol="000001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="SZ",
        is_etf=False,
    )

    assert bars == [{"date": "2026-03-13", "close": 1}]
    assert source == "tushare"
    assert status == "done"
    assert note == ""
    tushare.fetch_pro_bar.assert_awaited_once_with(
        ts_code="000001.SZ",
        asset="E",
        freq="D",
        adj=fetch_daily_task.AdjustType.NO_ADJUST,
        start_date="2026-03-10",
        end_date="2026-03-13",
    )
    tushare.fetch_kline.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()
    eastmoney.fetch.assert_not_awaited()


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
            (
                await session.execute(
                    select(Stock).where(Stock.symbol == "000001").order_by(Stock.ts_code)
                )
            )
            .scalars()
            .all()
        )
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
        await session.execute(text("""
            INSERT INTO backfill_daily_state (ts_code, status)
            VALUES ('000001.SZ', 'needs_fallback')
            """))
        await session.commit()

        result = await session.execute(text("SELECT COUNT(*) FROM backfill_daily_state"))
        assert result.scalar_one() == 1

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_resolve_candidate_trade_dates_only_prepends_today_when_requested():
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
                DailyBar(
                    ts_code="000001.SZ",
                    trade_date="20260320",
                    trade_date_dt=None,
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=Decimal("10"),
                    pre_close=Decimal("10"),
                    change=Decimal("0"),
                    pct_chg=Decimal("0"),
                    vol=Decimal("1"),
                    amount=Decimal("1"),
                ),
                DailyBar(
                    ts_code="000001.SZ",
                    trade_date="20260319",
                    trade_date_dt=None,
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=Decimal("10"),
                    pre_close=Decimal("10"),
                    change=Decimal("0"),
                    pct_chg=Decimal("0"),
                    vol=Decimal("1"),
                    amount=Decimal("1"),
                ),
            ]
        )
        await session.commit()

        with_today = await fetch_fund_flow_task._resolve_candidate_trade_dates(
            session,
            include_today=True,
        )
        without_today = await fetch_fund_flow_task._resolve_candidate_trade_dates(
            session,
            include_today=False,
        )

    assert with_today[0] == market_calendar.format_trade_date(market_calendar.current_market_date())
    assert without_today == ["20260320", "20260319"]

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_daily_bars_backfill_window_dry_run_is_bounded(monkeypatch):
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS backfill_daily_state"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        session.add_all(
            [
                Stock(
                    ts_code="000001.SZ",
                    symbol="000001",
                    name="平安银行",
                    exchange="SZ",
                    list_status="L",
                    is_etf=False,
                ),
                Stock(
                    ts_code="000002.SZ",
                    symbol="000002",
                    name="万科A",
                    exchange="SZ",
                    list_status="L",
                    is_etf=False,
                ),
            ]
        )
        await session.commit()

    async def fail_if_called(session):
        raise AssertionError("dry-run must not create or commit backfill state")

    monkeypatch.setattr(fetch_daily_task, "_ensure_backfill_state_table", fail_if_called)

    result = await run_daily_bars_backfill_window(
        start_date="2024-01-02",
        end_date="2024-01-05",
        code_limit=1,
        source="eastmoney",
        execute=False,
        session_factory=async_session_factory_test,
    )

    assert result["dry_run"] is True
    assert result["source"] == "eastmoney"
    assert result["target_count"] == 1
    assert set(result["targets"]) <= {"000001.SZ", "000002.SZ"}
    assert result["saved_rows"] == 0

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_daily_bars_backfill_window_uses_explicit_baostock_source():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS backfill_daily_state"))
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
        await session.commit()

    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(
        return_value=[
            {
                "date": "2024-01-02",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "pre_close": 10,
                "change": 0.5,
                "change_pct": 5,
                "volume": 1000,
                "amount": 10000,
            }
        ]
    )
    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    result = await run_daily_bars_backfill_window(
        start_date="2024-01-02",
        end_date="2024-01-05",
        code_limit=1,
        source="baostock",
        execute=True,
        provider=tushare,
        baostock_provider=baostock,
        eastmoney_crawler=eastmoney,
        session_factory=async_session_factory_test,
    )

    async with async_session_factory_test() as session:
        rows = (await session.execute(select(DailyBar))).scalars().all()

    assert result["source"] == "baostock"
    assert result["saved_rows"] == 1
    assert result["items"] == [
        {
            "ts_code": "000001.SZ",
            "status": "done",
            "source": "baostock",
            "source_policy": "baostock",
            "saved_rows": 1,
            "attempts": [{"source": "baostock", "rows": 1}],
        }
    ]
    baostock.fetch_kline.assert_awaited_once_with(
        code="000001",
        start_date="2024-01-02",
        end_date="2024-01-05",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        period="daily",
    )
    tushare.fetch_pro_bar.assert_not_awaited()
    eastmoney.fetch.assert_not_awaited()
    assert len(rows) == 1
    assert rows[0].ts_code == "000001.SZ"

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_daily_bars_backfill_window_prefers_tushare_but_uses_baostock_when_needed():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS backfill_daily_state"))
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
        await session.commit()

    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock(return_value=[])
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(
        return_value=[
            {
                "date": "2024-01-02",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "pre_close": 10,
                "change": 0.5,
                "change_pct": 5,
                "volume": 1000,
                "amount": 10000,
            }
        ]
    )
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    result = await run_daily_bars_backfill_window(
        start_date="2024-01-02",
        end_date="2024-01-05",
        code_limit=1,
        source="prefer_tushare",
        execute=True,
        provider=tushare,
        baostock_provider=baostock,
        eastmoney_crawler=eastmoney,
        session_factory=async_session_factory_test,
    )

    assert result["source"] == "prefer_tushare"
    assert result["saved_rows"] == 1
    assert result["items"] == [
        {
            "ts_code": "000001.SZ",
            "status": "done",
            "source": "baostock",
            "source_policy": "prefer_tushare",
            "saved_rows": 1,
            "attempts": [
                {"source": "tushare", "rows": 0},
                {"source": "baostock", "rows": 1},
            ],
        }
    ]
    tushare.fetch_pro_bar.assert_awaited_once()
    baostock.fetch_kline.assert_awaited_once()
    eastmoney.fetch.assert_not_awaited()

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_is_trading_day_returns_false_on_weekend_without_calendar_call():
    crawler = AsyncMock()

    result = await market_calendar.is_trading_day(date(2026, 3, 22), crawler=crawler)

    assert result is False
    crawler.fetch_trade_calendar.assert_not_called()


def test_should_skip_market_task_respects_force_run(monkeypatch):
    monkeypatch.setenv("MARKET_TASK_FORCE_RUN", "true")

    assert (
        market_calendar.should_skip_market_task("资金流向抓取任务", today_is_trading_day=False)
        is False
    )


def test_summarize_top_list_aggregates_by_ts_code():
    rows = [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260320",
            "name": "平安银行",
            "buy_amount": 100.0,
            "sell_amount": 40.0,
            "net_amount": 60.0,
        },
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260320",
            "name": "平安银行",
            "buy_amount": 30.0,
            "sell_amount": 10.0,
            "net_amount": 20.0,
        },
    ]
    inst_rows = [
        {"ts_code": "000001.SZ", "side": "buy"},
        {"ts_code": "000001.SZ", "side": "sell"},
        {"ts_code": "000001.SZ", "side": "0"},
    ]

    summarized = summarize_top_list(rows, inst_rows)

    assert summarized == [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260320",
            "name": "平安银行",
            "sum_buy": 130.0,
            "sum_sell": 50.0,
            "net_amount": 80.0,
            "ranking_times": 2,
            "buy_seat": 2,
            "sell_seat": 1,
        }
    ]


def test_summarize_block_trades_groups_and_calculates_premium_rate():
    rows = [
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260320",
            "price": 10.0,
            "vol": 100.0,
            "amount": 1000.0,
        },
        {
            "ts_code": "000001.SZ",
            "trade_date": "20260320",
            "price": 12.0,
            "vol": 50.0,
            "amount": 600.0,
        },
    ]

    summarized = summarize_block_trades(rows, {"000001.SZ": 11.0})

    assert len(summarized) == 1
    assert summarized[0]["ts_code"] == "000001.SZ"
    assert summarized[0]["trade_count"] == 2
    assert summarized[0]["total_volume"] == 150.0
    assert summarized[0]["total_amount"] == 1600.0
    assert summarized[0]["avg_price"] == pytest.approx(10.6666667)
    assert summarized[0]["premium_rate"] == pytest.approx(-3.0303030)
