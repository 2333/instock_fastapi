from datetime import date

from app.services.date_utils import parse_trade_date, trade_date_dt_param


def test_parse_trade_date_accepts_compact_and_iso_inputs():
    assert parse_trade_date("20260421") == date(2026, 4, 21)
    assert parse_trade_date("2026-04-21") == date(2026, 4, 21)
    assert parse_trade_date(date(2026, 4, 21)) == date(2026, 4, 21)


def test_trade_date_dt_param_returns_date_object_for_sql_binding():
    assert trade_date_dt_param("20260421") == date(2026, 4, 21)
    assert trade_date_dt_param("2026-04-21") == date(2026, 4, 21)
    assert trade_date_dt_param(None) is None
