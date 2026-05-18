import sys
from datetime import date, datetime
from decimal import Decimal
from types import ModuleType
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.jobs import scheduler as scheduler_module
from app.jobs.scheduler import (
    FETCH_DAILY_DATA_TIME,
    FETCH_MARKET_REFERENCE_TIME,
    FETCH_STOCK_CLASSIFICATION_TIME,
    RUN_POST_CLOSE_ALERTS_TIME,
    _get_daily_bar_coverage_status,
    recover_missed_alert_subscriptions,
    recover_missed_jobs,
    recover_missed_market_jobs,
    should_recover_market_job,
    start_scheduler,
)
from app.models.stock_model import DailyBar, Stock

MARKET_TZ = ZoneInfo("Asia/Shanghai")


def test_start_scheduler_registers_monday_classification_job(monkeypatch):
    class DummyScheduler:
        def __init__(self):
            self.running = False
            self.jobs = []

        def add_job(self, *args, **kwargs):
            self.jobs.append(kwargs)

        def start(self):
            self.running = True

    dummy = DummyScheduler()

    monkeypatch.setattr("app.jobs.scheduler.scheduler", dummy)
    monkeypatch.setattr("app.jobs.scheduler._acquire_scheduler_lock", lambda: True)

    start_scheduler()

    captured = [job for job in dummy.jobs if job.get("id") == "fetch_stock_classification"]
    assert len(captured) == 1
    trigger = captured[0]["trigger"]
    trigger_repr = str(trigger)
    assert "day_of_week='mon'" in trigger_repr
    assert f"hour='{FETCH_STOCK_CLASSIFICATION_TIME.hour}'" in trigger_repr
    assert f"minute='{FETCH_STOCK_CLASSIFICATION_TIME.minute}'" in trigger_repr


def test_start_scheduler_registers_post_close_alert_subscription_job(monkeypatch):
    class DummyScheduler:
        def __init__(self):
            self.running = False
            self.jobs = []

        def add_job(self, *args, **kwargs):
            self.jobs.append(kwargs)

        def start(self):
            self.running = True

    dummy = DummyScheduler()

    monkeypatch.setattr("app.jobs.scheduler.scheduler", dummy)
    monkeypatch.setattr("app.jobs.scheduler._acquire_scheduler_lock", lambda: True)

    start_scheduler()

    captured = [job for job in dummy.jobs if job.get("id") == "run_post_close_alerts"]
    assert len(captured) == 1
    assert captured[0]["func"] == "app.jobs.tasks.alert_subscription_task:run"
    trigger_repr = str(captured[0]["trigger"])
    assert "day_of_week='mon-fri'" in trigger_repr
    assert f"hour='{RUN_POST_CLOSE_ALERTS_TIME.hour}'" in trigger_repr
    assert f"minute='{RUN_POST_CLOSE_ALERTS_TIME.minute}'" in trigger_repr


def test_fetch_stock_classification_time_is_afternoon():
    assert FETCH_STOCK_CLASSIFICATION_TIME.hour >= 12


def test_should_recover_market_job_after_schedule_when_data_is_stale():
    now = datetime(2026, 3, 23, 19, 35, tzinfo=MARKET_TZ)

    assert should_recover_market_job(
        now=now,
        scheduled_time=FETCH_DAILY_DATA_TIME,
        today_trade_date="20260323",
        latest_trade_dates=["20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_before_schedule():
    now = datetime(2026, 3, 23, 17, 30, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=FETCH_DAILY_DATA_TIME,
        today_trade_date="20260323",
        latest_trade_dates=["20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_when_data_is_current():
    now = datetime(2026, 3, 23, 19, 35, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=FETCH_DAILY_DATA_TIME,
        today_trade_date="20260323",
        latest_trade_dates=["20260323"],
        today_is_trading_day=True,
    )


def test_should_recover_market_job_when_any_required_table_is_stale():
    now = datetime(2026, 3, 23, 22, 0, tzinfo=MARKET_TZ)

    assert should_recover_market_job(
        now=now,
        scheduled_time=FETCH_MARKET_REFERENCE_TIME,
        today_trade_date="20260323",
        latest_trade_dates=["20260323", "20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_on_non_trading_day():
    now = datetime(2026, 3, 22, 19, 35, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=FETCH_DAILY_DATA_TIME,
        today_trade_date="20260322",
        latest_trade_dates=["20260321"],
        today_is_trading_day=False,
    )


@pytest.mark.asyncio
async def test_recover_missed_market_jobs_when_daily_latest_is_today_but_coverage_incomplete(
    monkeypatch,
):
    calls: list[str] = []

    async def record_daily_run():
        calls.append("fetch_daily_data")

    async def record_fund_flow_run():
        calls.append("fetch_fund_flow")

    async def record_market_reference_run():
        calls.append("fetch_market_reference")

    fetch_daily_module = ModuleType("app.jobs.tasks.fetch_daily_task")
    fetch_daily_module.run = record_daily_run
    fund_flow_module = ModuleType("app.jobs.tasks.fetch_fund_flow_task")
    fund_flow_module.run = record_fund_flow_run
    market_reference_module = ModuleType("app.jobs.tasks.fetch_market_reference_task")
    market_reference_module.run = record_market_reference_run

    monkeypatch.setitem(sys.modules, "app.jobs.tasks.fetch_daily_task", fetch_daily_module)
    monkeypatch.setitem(sys.modules, "app.jobs.tasks.fetch_fund_flow_task", fund_flow_module)
    monkeypatch.setitem(
        sys.modules,
        "app.jobs.tasks.fetch_market_reference_task",
        market_reference_module,
    )

    fixed_now = datetime(2026, 3, 23, 19, 45, tzinfo=MARKET_TZ)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    async def fake_latest_trade_dates(table_names: tuple[str, ...]) -> dict[str, str | None]:
        return {table_name: "20260323" for table_name in table_names}

    async def fake_daily_bar_coverage_status(trade_date: str) -> dict[str, int | bool]:
        assert trade_date == "20260323"
        return {"expected_count": 2, "covered_count": 1, "has_partial_gap": True}

    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduler_module, "_get_latest_trade_dates", fake_latest_trade_dates)
    monkeypatch.setattr(
        scheduler_module,
        "_get_daily_bar_coverage_status",
        fake_daily_bar_coverage_status,
    )
    monkeypatch.setattr(scheduler_module, "current_market_date", lambda now: now.date())
    monkeypatch.setattr(scheduler_module, "format_trade_date", lambda target_date: "20260323")

    async def fake_is_trading_day(*, target_date):
        assert target_date == date(2026, 3, 23)
        return True

    monkeypatch.setattr(scheduler_module, "is_trading_day", fake_is_trading_day)

    await recover_missed_market_jobs()

    assert calls == ["fetch_daily_data"]


@pytest.mark.asyncio
async def test_recover_missed_market_jobs_does_not_run_when_latest_daily_date_uses_hyphenated_format(
    monkeypatch,
):
    calls: list[str] = []
    coverage_checks: list[str] = []

    async def record_daily_run():
        calls.append("fetch_daily_data")

    async def record_fund_flow_run():
        calls.append("fetch_fund_flow")

    async def record_market_reference_run():
        calls.append("fetch_market_reference")

    fetch_daily_module = ModuleType("app.jobs.tasks.fetch_daily_task")
    fetch_daily_module.run = record_daily_run
    fund_flow_module = ModuleType("app.jobs.tasks.fetch_fund_flow_task")
    fund_flow_module.run = record_fund_flow_run
    market_reference_module = ModuleType("app.jobs.tasks.fetch_market_reference_task")
    market_reference_module.run = record_market_reference_run

    monkeypatch.setitem(sys.modules, "app.jobs.tasks.fetch_daily_task", fetch_daily_module)
    monkeypatch.setitem(sys.modules, "app.jobs.tasks.fetch_fund_flow_task", fund_flow_module)
    monkeypatch.setitem(
        sys.modules,
        "app.jobs.tasks.fetch_market_reference_task",
        market_reference_module,
    )

    fixed_now = datetime(2026, 3, 23, 19, 45, tzinfo=MARKET_TZ)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    async def fake_latest_trade_dates(table_names: tuple[str, ...]) -> dict[str, str | None]:
        latest_dates = {table_name: "20260323" for table_name in table_names}
        if "daily_bars" in latest_dates:
            latest_dates["daily_bars"] = "2026-03-23"
        return latest_dates

    async def fake_daily_bar_coverage_status(trade_date: str) -> dict[str, int | bool]:
        coverage_checks.append(trade_date)
        assert trade_date == "20260323"
        return {"expected_count": 2, "covered_count": 2, "has_partial_gap": False}

    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduler_module, "_get_latest_trade_dates", fake_latest_trade_dates)
    monkeypatch.setattr(
        scheduler_module,
        "_get_daily_bar_coverage_status",
        fake_daily_bar_coverage_status,
    )
    monkeypatch.setattr(scheduler_module, "current_market_date", lambda now: now.date())
    monkeypatch.setattr(scheduler_module, "format_trade_date", lambda target_date: "20260323")

    async def fake_is_trading_day(*, target_date):
        assert target_date == date(2026, 3, 23)
        return True

    monkeypatch.setattr(scheduler_module, "is_trading_day", fake_is_trading_day)

    await recover_missed_market_jobs()

    assert calls == []
    assert coverage_checks == ["20260323"]


@pytest.mark.asyncio
async def test_recover_missed_alert_subscriptions_runs_after_schedule_when_due(monkeypatch):
    from app.jobs.tasks import alert_subscription_task

    calls: list[tuple[str, str]] = []
    fixed_now = datetime(2026, 3, 23, 20, 40, tzinfo=MARKET_TZ)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    async def fake_is_trading_day(*, target_date):
        assert target_date == date(2026, 3, 23)
        return True

    async def fake_has_due_post_close_runs(trade_date: str) -> bool:
        calls.append(("due", trade_date))
        return True

    async def fake_run_alert_subscriptions(*, date: str):
        calls.append(("run", date))
        return {"status": "completed"}

    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduler_module, "current_market_date", lambda now: now.date())
    monkeypatch.setattr(scheduler_module, "format_trade_date", lambda target_date: "20260323")
    monkeypatch.setattr(scheduler_module, "is_trading_day", fake_is_trading_day)
    monkeypatch.setattr(
        alert_subscription_task, "has_due_post_close_runs", fake_has_due_post_close_runs
    )
    monkeypatch.setattr(alert_subscription_task, "run", fake_run_alert_subscriptions)

    await recover_missed_alert_subscriptions()

    assert calls == [("due", "20260323"), ("run", "20260323")]


@pytest.mark.asyncio
async def test_recover_missed_alert_subscriptions_noops_before_schedule(monkeypatch):
    from app.jobs.tasks import alert_subscription_task

    calls: list[str] = []
    fixed_now = datetime(2026, 3, 23, 20, 0, tzinfo=MARKET_TZ)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now

    async def fake_is_trading_day(*, target_date):
        return True

    async def fake_has_due_post_close_runs(trade_date: str) -> bool:
        calls.append("due")
        return True

    monkeypatch.setattr(scheduler_module, "datetime", FixedDateTime)
    monkeypatch.setattr(scheduler_module, "current_market_date", lambda now: now.date())
    monkeypatch.setattr(scheduler_module, "is_trading_day", fake_is_trading_day)
    monkeypatch.setattr(
        alert_subscription_task, "has_due_post_close_runs", fake_has_due_post_close_runs
    )

    await recover_missed_alert_subscriptions()

    assert calls == []


@pytest.mark.asyncio
async def test_recover_missed_jobs_runs_market_before_alert(monkeypatch):
    calls: list[str] = []

    async def fake_recover_market():
        calls.append("market")

    async def fake_recover_alerts():
        calls.append("alerts")

    monkeypatch.setattr(scheduler_module, "recover_missed_market_jobs", fake_recover_market)
    monkeypatch.setattr(scheduler_module, "recover_missed_alert_subscriptions", fake_recover_alerts)

    await recover_missed_jobs()

    assert calls == ["market", "alerts"]


@pytest.mark.asyncio
async def test_daily_bar_coverage_status_counts_only_active_supported_sh_sz(monkeypatch):
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Stock.__table__.create)
        await conn.run_sync(DailyBar.__table__.create)

    async with session_factory() as session:
        session.add_all(
            [
                Stock(
                    ts_code="000001.SZ",
                    symbol="000001",
                    name="平安银行",
                    exchange="SZ",
                    list_status="L",
                    list_date="19910403",
                    is_etf=False,
                ),
                Stock(
                    ts_code="600000.SH",
                    symbol="600000",
                    name="浦发银行",
                    exchange="SH",
                    list_status="L",
                    list_date="19991110",
                    is_etf=False,
                ),
                Stock(
                    ts_code="600001.SSE",
                    symbol="600001",
                    name="上交所 legacy 样本",
                    exchange="LEGACY",
                    list_status="L",
                    list_date="2026-03-23",
                    is_etf=False,
                ),
                Stock(
                    ts_code="000002.SZSE",
                    symbol="000002",
                    name="深交所 legacy 边界样本",
                    exchange="LEGACY",
                    list_status="L",
                    list_date="20200101",
                    delist_date="2026-03-23",
                    is_etf=False,
                ),
                Stock(
                    ts_code="830001.BJ",
                    symbol="830001",
                    name="北交所样本",
                    exchange="BJ",
                    list_status="L",
                    list_date="20200101",
                    is_etf=False,
                ),
                Stock(
                    ts_code="510300.SH",
                    symbol="510300",
                    name="沪深300ETF",
                    exchange="SH",
                    list_status="L",
                    list_date="20120401",
                    is_etf=True,
                ),
                Stock(
                    ts_code="000003.SZ",
                    symbol="000003",
                    name="未上市样本",
                    exchange="SZ",
                    list_status="L",
                    list_date="20260324",
                    is_etf=False,
                ),
            ]
        )
        session.add_all(
            [
                DailyBar(
                    ts_code="000001.SZ",
                    trade_date="20260323",
                    trade_date_dt=date(2026, 3, 23),
                    open=Decimal("10.00"),
                    high=Decimal("10.50"),
                    low=Decimal("9.90"),
                    close=Decimal("10.20"),
                    pre_close=Decimal("10.00"),
                    change=Decimal("0.20"),
                    pct_chg=Decimal("2.00"),
                    vol=Decimal("100000"),
                    amount=Decimal("1020000"),
                ),
                DailyBar(
                    ts_code="830001.BJ",
                    trade_date="20260323",
                    trade_date_dt=date(2026, 3, 23),
                    open=Decimal("8.00"),
                    high=Decimal("8.30"),
                    low=Decimal("7.90"),
                    close=Decimal("8.10"),
                    pre_close=Decimal("8.00"),
                    change=Decimal("0.10"),
                    pct_chg=Decimal("1.25"),
                    vol=Decimal("50000"),
                    amount=Decimal("405000"),
                ),
                DailyBar(
                    ts_code="600001.SSE",
                    trade_date="2026-03-23",
                    trade_date_dt=date(2026, 3, 23),
                    open=Decimal("12.00"),
                    high=Decimal("12.40"),
                    low=Decimal("11.90"),
                    close=Decimal("12.10"),
                    pre_close=Decimal("12.00"),
                    change=Decimal("0.10"),
                    pct_chg=Decimal("0.83"),
                    vol=Decimal("88000"),
                    amount=Decimal("1064800"),
                ),
                DailyBar(
                    ts_code="510300.SH",
                    trade_date="20260323",
                    trade_date_dt=date(2026, 3, 23),
                    open=Decimal("4.00"),
                    high=Decimal("4.10"),
                    low=Decimal("3.98"),
                    close=Decimal("4.05"),
                    pre_close=Decimal("4.00"),
                    change=Decimal("0.05"),
                    pct_chg=Decimal("1.25"),
                    vol=Decimal("200000"),
                    amount=Decimal("810000"),
                ),
            ]
        )
        await session.commit()

    monkeypatch.setattr(scheduler_module, "async_session_factory", session_factory)

    status = await _get_daily_bar_coverage_status("20260323")

    assert status == {"expected_count": 4, "covered_count": 2, "has_partial_gap": True}

    await engine.dispose()
