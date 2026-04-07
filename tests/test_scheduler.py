from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.jobs.scheduler import should_recover_market_job

MARKET_TZ = ZoneInfo("Asia/Shanghai")


def test_should_recover_market_job_after_schedule_when_data_is_stale():
    now = datetime(2026, 3, 23, 16, 35, tzinfo=MARKET_TZ)

    assert should_recover_market_job(
        now=now,
        scheduled_time=time(hour=15, minute=30),
        today_trade_date="20260323",
        latest_trade_dates=["20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_before_schedule():
    now = datetime(2026, 3, 23, 15, 20, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=time(hour=15, minute=30),
        today_trade_date="20260323",
        latest_trade_dates=["20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_when_data_is_current():
    now = datetime(2026, 3, 23, 16, 35, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=time(hour=15, minute=30),
        today_trade_date="20260323",
        latest_trade_dates=["20260323"],
        today_is_trading_day=True,
    )


def test_should_recover_market_job_when_any_required_table_is_stale():
    now = datetime(2026, 3, 23, 21, 30, tzinfo=MARKET_TZ)

    assert should_recover_market_job(
        now=now,
        scheduled_time=time(hour=21, minute=15),
        today_trade_date="20260323",
        latest_trade_dates=["20260323", "20260320"],
        today_is_trading_day=True,
    )


def test_should_not_recover_market_job_on_non_trading_day():
    now = datetime(2026, 3, 22, 16, 35, tzinfo=MARKET_TZ)

    assert not should_recover_market_job(
        now=now,
        scheduled_time=time(hour=15, minute=30),
        today_trade_date="20260322",
        latest_trade_dates=["20260321"],
        today_is_trading_day=False,
    )
