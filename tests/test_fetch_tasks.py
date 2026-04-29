import asyncio
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text

from app.jobs import market_calendar
from app.jobs.tasks import fetch_daily_task, fetch_fund_flow_task
from app.jobs.tasks.fetch_daily_task import (
    _ensure_backfill_state_table,
    fetch_and_save_stock_classifications,
    fetch_and_save_stock_universe,
    run_daily_bars_backfill_window,
    save_stock_classifications,
    save_stocks,
)
from app.jobs.tasks.fetch_market_reference_task import summarize_block_trades, summarize_top_list
from app.models.stock_model import Base, DailyBar, Stock
from core.crawling.baostock_provider import BaoStockProvider
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
async def test_fetch_daily_bars_marks_etf_as_unsupported_for_baostock():
    tushare = AsyncMock()
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    bars, source, status, note = await fetch_daily_task._fetch_bars_by_source(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        source="baostock",
        symbol="159001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="SZ",
        is_etf=True,
    )

    assert bars == []
    assert source == "baostock"
    assert status == "needs_fallback"
    assert "does not support ETF/BJ contract" in note
    eastmoney.fetch.assert_not_awaited()
    tushare.fetch_kline.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_daily_bars_rejects_tushare_source():
    tushare = AsyncMock()
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock()
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    with pytest.raises(ValueError, match="source must be one of: baostock, eastmoney"):
        await fetch_daily_task._fetch_bars_by_source(
            tushare_provider=tushare,
            baostock_provider=baostock,
            em_crawler=eastmoney,
            source="tushare",
            symbol="920000",
            start_date="2026-03-10",
            end_date="2026-03-13",
            adjust=fetch_daily_task.AdjustType.NO_ADJUST,
            exchange="BJ",
            is_etf=False,
        )

    eastmoney.fetch.assert_not_awaited()
    tushare.fetch_kline.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_daily_bars_uses_explicit_baostock_source():
    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock()
    tushare.fetch_kline = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(return_value=[{"date": "2026-03-13", "close": 1}])
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    bars, source, status, note = await fetch_daily_task._fetch_bars_by_source(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        source="baostock",
        symbol="000001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="SZ",
        is_etf=False,
    )

    assert bars == [{"date": "2026-03-13", "close": 1}]
    assert source == "baostock"
    assert status == "done"
    assert note == ""
    baostock.fetch_kline.assert_awaited_once_with(
        code="000001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        period="daily",
    )
    tushare.fetch_kline.assert_not_awaited()
    tushare.fetch_pro_bar.assert_not_awaited()
    eastmoney.fetch.assert_not_awaited()


def test_selected_daily_bar_source_rejects_legacy_tushare_env(monkeypatch):
    monkeypatch.setenv("DAILY_BARS_SOURCE", "tushare")

    with pytest.raises(
        ValueError,
        match="DAILY_BARS_SOURCE must be one of: baostock, eastmoney",
    ):
        fetch_daily_task._selected_daily_bar_source()


def test_selected_security_master_source_rejects_legacy_tushare_env(monkeypatch):
    monkeypatch.setenv("SECURITY_MASTER_SOURCE", "tushare")

    with pytest.raises(
        ValueError,
        match="SECURITY_MASTER_SOURCE must be one of: baostock, eastmoney",
    ):
        fetch_daily_task._selected_security_master_source()


@pytest.mark.asyncio
async def test_fetch_daily_bars_rejects_explicit_tushare_source():
    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(return_value=[{"date": "2026-03-13", "close": 1}])
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    with pytest.raises(ValueError, match="source must be one of: baostock, eastmoney"):
        await fetch_daily_task._fetch_bars_by_source(
            tushare_provider=tushare,
            baostock_provider=baostock,
            em_crawler=eastmoney,
            source="tushare",
            symbol="000001",
            start_date="2026-03-10",
            end_date="2026-03-13",
            adjust=fetch_daily_task.AdjustType.NO_ADJUST,
            exchange="SZ",
            is_etf=False,
        )

    tushare.fetch_pro_bar.assert_not_awaited()
    baostock.fetch_kline.assert_not_awaited()
    eastmoney.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_daily_bars_does_not_fallback_when_baostock_returns_empty():
    tushare = AsyncMock()
    tushare.fetch_pro_bar = AsyncMock()
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(return_value=[])
    eastmoney = AsyncMock()
    eastmoney.fetch = AsyncMock()

    bars, source, status, note = await fetch_daily_task._fetch_bars_by_source(
        tushare_provider=tushare,
        baostock_provider=baostock,
        em_crawler=eastmoney,
        source="baostock",
        symbol="000001",
        start_date="2026-03-10",
        end_date="2026-03-13",
        adjust=fetch_daily_task.AdjustType.NO_ADJUST,
        exchange="SZ",
        is_etf=False,
    )

    assert bars == []
    assert source == "baostock"
    assert status == "needs_fallback"
    assert note == "explicit source returned empty"
    assert baostock.fetch_kline.await_count == 3
    tushare.fetch_pro_bar.assert_not_awaited()
    eastmoney.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_and_save_daily_bars_uses_calendar_trading_days(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, *_args, **_kwargs):
            return datetime(2026, 3, 22, 10, 0, 0)

    class _DummySessionManager:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    trade_dates = []

    async def _get_targets(_session, trade_date):
        trade_dates.append(trade_date)
        return []

    crawler = AsyncMock()
    crawler.fetch_trade_calendar = AsyncMock(
        return_value=[
            {"trade_date": "2026-03-18", "is_trading": False},
            {"trade_date": "2026-03-19", "is_trading": True},
            {"trade_date": "2026-03-20", "is_trading": True},
            {"trade_date": "2026-03-21", "is_trading": False},
            {"trade_date": "2026-03-22", "is_trading": False},
        ]
    )
    crawler.close = AsyncMock()

    monkeypatch.setattr(fetch_daily_task, "datetime", FrozenDateTime)
    monkeypatch.setattr(fetch_daily_task, "EastMoneyCrawler", lambda proxy_pool=None: crawler)
    monkeypatch.setattr(fetch_daily_task, "_get_daily_sync_targets", _get_targets)
    monkeypatch.setattr(fetch_daily_task, "async_session_factory", lambda: _DummySessionManager())

    await fetch_daily_task.fetch_and_save_daily_bars(days=4, concurrency=1)

    assert trade_dates == ["2026-03-19", "2026-03-20"]
    crawler.fetch_trade_calendar.assert_awaited_once_with(
        start_date="2026-03-18",
        end_date="2026-03-22",
    )


@pytest.mark.asyncio
async def test_fetch_and_save_daily_bars_skips_when_calendar_unavailable(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, *_args, **_kwargs):
            return datetime(2026, 3, 22, 10, 0, 0)

    class _DummySessionManager:
        async def __aenter__(self):
            return AsyncMock()

        async def __aexit__(self, exc_type, exc, tb):
            return False

    get_targets = AsyncMock(return_value=[])
    crawler = AsyncMock()
    crawler.fetch_trade_calendar = AsyncMock(return_value=[])
    crawler.close = AsyncMock()

    monkeypatch.setattr(fetch_daily_task, "datetime", FrozenDateTime)
    monkeypatch.setattr(fetch_daily_task, "EastMoneyCrawler", lambda proxy_pool=None: crawler)
    monkeypatch.setattr(fetch_daily_task, "_get_daily_sync_targets", get_targets)
    monkeypatch.setattr(fetch_daily_task, "async_session_factory", lambda: _DummySessionManager())

    await fetch_daily_task.fetch_and_save_daily_bars(days=4, concurrency=1)

    get_targets.assert_not_awaited()


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
async def test_save_stocks_accepts_baostock_normalized_fields():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        count = await save_stocks(
            session,
            [
                {
                    "ts_code": "510300.SH",
                    "symbol": "510300",
                    "exchange": "SH",
                    "name": "沪深300ETF",
                    "industry": "ETF",
                    "market": "ETF",
                    "list_date": "20120405",
                }
            ],
            is_etf=True,
            include_industry=True,
        )

        saved = await session.scalar(select(Stock).where(Stock.ts_code == "510300.SH"))

    assert count == 1
    assert saved is not None
    assert saved.symbol == "510300"
    assert saved.name == "沪深300ETF"
    assert saved.industry == "ETF"
    assert saved.market == "ETF"
    assert saved.list_date == "20120405"
    assert saved.is_etf is True

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_save_stocks_default_does_not_overwrite_legacy_industry():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                area="深圳",
                industry="银行",
                market="主板",
                exchange="SZ",
                list_status="L",
                is_etf=False,
            )
        )
        await session.commit()

        await save_stocks(
            session,
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol": "000001",
                    "name": "平安银行",
                    "industry": "新能源",
                    "exchange": "SZ",
                }
            ],
        )
        stock = await session.scalar(select(Stock).where(Stock.ts_code == "000001.SZ"))

    assert stock is not None
    assert stock.industry == "银行"

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_save_stock_classifications_persists_provenance_without_mutating_legacy_industry():
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                area="深圳",
                industry="银行",
                market="主板",
                exchange="SZ",
                list_status="L",
                is_etf=False,
            )
        )
        await session.commit()

        count = await save_stock_classifications(
            session,
            [
                {
                    "ts_code": "sz.000001",
                    "industry_label": "金融",
                    "industry_taxonomy": "银行",
                    "industry_source": "baostock",
                    "update_date": "2026-03-01",
                }
            ],
        )
        stock = await session.scalar(select(Stock).where(Stock.ts_code == "000001.SZ"))

    assert count == 1
    assert stock is not None
    assert stock.industry == "银行"
    assert stock.industry_label == "金融"
    assert stock.industry_taxonomy == "银行"
    assert stock.industry_source == "baostock"
    assert stock.industry_updated_at == datetime(2026, 3, 1, 0, 0, 0)

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_fetch_and_save_stock_classifications_commits_audit_row(monkeypatch):
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    provider = type(
        "BaoStockProvider",
        (),
        {
            "fetch_stock_classifications": AsyncMock(
                return_value=[
                    {
                        "ts_code": "sz.000001",
                        "industry_label": "金融",
                        "industry_taxonomy": "银行",
                        "industry_source": "baostock",
                        "update_date": "2026-03-01",
                    }
                ]
            )
        },
    )()
    monkeypatch.setattr(fetch_daily_task, "BaoStockProvider", lambda: provider)
    monkeypatch.setattr(fetch_daily_task, "async_session_factory", async_session_factory_test)

    async with async_session_factory_test() as session:
        session.add(
            Stock(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                area="深圳",
                industry="银行",
                market="主板",
                exchange="SZ",
                list_status="L",
                is_etf=False,
            )
        )
        await session.commit()

    saved = await fetch_and_save_stock_classifications()

    assert saved == 1

    async with async_session_factory_test() as session:
        result = await session.execute(text("""
                SELECT status, source, note
                FROM data_fetch_audit
                WHERE task_name = 'fetch_stock_classification'
                  AND entity_type = 'stock_classification'
                  AND entity_key = 'baostock'
            """))
        audit_row = result.one()

    assert audit_row == ("done", "baostock", "rows=1")

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP TABLE IF EXISTS data_fetch_audit"))


@pytest.mark.asyncio
async def test_run_only_executes_daily_bars(monkeypatch):
    run_called = {}

    async def fake_fetch_daily_bars(*, days):
        run_called["daily_bars"] = days

    monkeypatch.setattr(
        fetch_daily_task, "should_skip_market_task", lambda *_args, **_kwargs: False
    )
    monkeypatch.setattr(fetch_daily_task, "is_trading_day", AsyncMock(return_value=True))
    monkeypatch.setattr(fetch_daily_task, "fetch_and_save_stocks", AsyncMock())
    monkeypatch.setattr(fetch_daily_task, "fetch_and_save_daily_bars", fake_fetch_daily_bars)

    await fetch_daily_task.run()

    assert run_called["daily_bars"] == 1
    fetch_daily_task.fetch_and_save_stocks.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_and_save_stock_universe_uses_stable_fields_only(monkeypatch):
    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def stock_side_effect(*, include_industry: bool = False):
        assert include_industry is False
        return [
            {
                "ts_code": "000001.SZ",
                "symbol": "000001",
                "name": "平安银行",
                "exchange": "SZ",
                "area": "深圳",
                "industry": "银行",
                "market": "主板",
            }
        ]

    async def etf_side_effect(*, include_industry: bool = False):
        assert include_industry is False
        return []

    fetcher = type(
        "BaoStockProvider",
        (),
        {
            "fetch_stock_list": AsyncMock(side_effect=stock_side_effect),
            "fetch_etf_list": AsyncMock(side_effect=etf_side_effect),
        },
    )()
    monkeypatch.setattr(fetch_daily_task, "BaoStockProvider", lambda: fetcher)
    monkeypatch.setattr(fetch_daily_task, "async_session_factory", async_session_factory_test)
    monkeypatch.setattr(fetch_daily_task, "record_fetch_audit", AsyncMock())
    monkeypatch.setenv("SECURITY_MASTER_SOURCE", "baostock")
    await fetch_and_save_stock_universe()

    async with async_session_factory_test() as session:
        stock = await session.scalar(select(Stock).where(Stock.ts_code == "000001.SZ"))

    assert stock is not None
    assert stock.industry is None

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
async def test_daily_bars_backfill_window_does_not_fallback_from_baostock():
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
    tushare.fetch_pro_bar = AsyncMock(
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
    baostock = AsyncMock()
    baostock.fetch_kline = AsyncMock(return_value=[])
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

    assert result["source"] == "baostock"
    assert result["saved_rows"] == 0
    assert result["items"] == [
        {
            "ts_code": "000001.SZ",
            "status": "nodata",
            "source": "baostock",
            "source_policy": "baostock",
            "saved_rows": 0,
            "attempts": [{"source": "baostock", "rows": 0}],
        }
    ]
    tushare.fetch_pro_bar.assert_not_awaited()
    baostock.fetch_kline.assert_awaited_once()
    eastmoney.fetch.assert_not_awaited()

    async with async_engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_baostock_provider_fetch_trade_calendar(monkeypatch):
    class FakeResult:
        error_code = "0"
        error_msg = ""

        def __init__(self):
            self._rows = [["2026-04-27", "1"], ["2026-04-28", "0"]]
            self._idx = -1

        def next(self):
            self._idx += 1
            return self._idx < len(self._rows)

        def get_row_data(self):
            return self._rows[self._idx]

    calls = []

    def query_trade_dates(*, start_date, end_date):
        calls.append((start_date, end_date))
        return FakeResult()

    fake_bs = SimpleNamespace(
        login=lambda: SimpleNamespace(error_code="0", error_msg=""),
        query_trade_dates=query_trade_dates,
    )
    monkeypatch.setitem(__import__("sys").modules, "baostock", fake_bs)
    provider = BaoStockProvider()
    monkeypatch.setattr(provider, "_record_request_usage", lambda: None)

    calendar = await provider.fetch_trade_calendar("2026-04-27", "2026-04-28")

    assert calls == [("2026-04-27", "2026-04-28")]
    assert calendar == [
        {"trade_date": "2026-04-27", "is_trading": True},
        {"trade_date": "2026-04-28", "is_trading": False},
    ]


@pytest.mark.asyncio
async def test_is_trading_day_returns_false_on_weekend_without_calendar_call():
    provider = AsyncMock()

    result = await market_calendar.is_trading_day(date(2026, 3, 22), provider=provider)

    assert result is False
    provider.fetch_trade_calendar.assert_not_called()


@pytest.mark.asyncio
async def test_is_trading_day_uses_baostock_calendar_without_tushare(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "invalid-token")
    provider = AsyncMock()
    provider.fetch_trade_calendar = AsyncMock(
        return_value=[{"trade_date": "2026-04-27", "is_trading": True}]
    )

    result = await market_calendar.is_trading_day(date(2026, 4, 27), provider=provider)

    assert result is True
    provider.fetch_trade_calendar.assert_awaited_once_with(
        start_date="2026-04-27",
        end_date="2026-04-27",
    )


@pytest.mark.asyncio
async def test_is_trading_day_returns_calendar_closed_day(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "invalid-token")
    provider = AsyncMock()
    provider.fetch_trade_calendar = AsyncMock(
        return_value=[{"trade_date": "2026-04-27", "is_trading": False}]
    )

    result = await market_calendar.is_trading_day(date(2026, 4, 27), provider=provider)

    assert result is False


@pytest.mark.asyncio
async def test_is_trading_day_returns_false_when_calendar_unavailable(monkeypatch):
    monkeypatch.setenv("TUSHARE_TOKEN", "invalid-token")
    provider = AsyncMock()
    provider.fetch_trade_calendar = AsyncMock(return_value=[])

    result = await market_calendar.is_trading_day(date(2026, 4, 27), provider=provider)

    assert result is False


@pytest.mark.asyncio
async def test_is_trading_day_returns_false_when_baostock_calendar_times_out(monkeypatch):
    monkeypatch.setenv("MARKET_CALENDAR_TIMEOUT_SECONDS", "0.01")
    provider = AsyncMock()

    async def _slow_calendar(*_args, **_kwargs):
        await asyncio.sleep(1)
        return [{"trade_date": "2026-04-27", "is_trading": True}]

    provider.fetch_trade_calendar = AsyncMock(side_effect=_slow_calendar)

    result = await market_calendar.is_trading_day(date(2026, 4, 27), provider=provider)

    assert result is False


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
