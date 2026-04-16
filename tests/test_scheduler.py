from datetime import datetime
from zoneinfo import ZoneInfo

from app.jobs.scheduler import (
    FETCH_DAILY_DATA_TIME,
    FETCH_MARKET_REFERENCE_TIME,
    FETCH_STOCK_CLASSIFICATION_TIME,
    should_recover_market_job,
    start_scheduler,
)

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
