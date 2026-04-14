from pathlib import Path

from app.models.stock_model import DailyBar, FundFlow, Indicator, Pattern
from app.jobs.tasks.fetch_daily_task import DAILY_BAR_UPSERT_CONSTRAINT


MIGRATION_PATH = Path("alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py")


def _unique_constraint_columns(model, name: str) -> tuple[str, ...]:
    for constraint in model.__table__.constraints:
        if constraint.name == name:
            return tuple(column.name for column in constraint.columns)
    raise AssertionError(f"Constraint {name} not found on {model.__tablename__}")


def _index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def test_core_fact_models_use_trade_date_dt_uniqueness():
    assert _unique_constraint_columns(
        DailyBar, "uq_daily_bars_ts_code_trade_date_dt"
    ) == ("ts_code", "trade_date_dt")
    assert _unique_constraint_columns(
        FundFlow, "uq_fund_flows_ts_code_trade_date_dt"
    ) == ("ts_code", "trade_date_dt")
    assert _unique_constraint_columns(
        Indicator, "uq_indicators_ts_code_trade_date_dt_name"
    ) == ("ts_code", "trade_date_dt", "indicator_name")
    assert _unique_constraint_columns(
        Pattern, "uq_patterns_ts_code_date_name"
    ) == ("ts_code", "trade_date_dt", "pattern_name")


def test_daily_bar_writer_targets_m1_unique_constraint():
    assert DAILY_BAR_UPSERT_CONSTRAINT == "uq_daily_bars_ts_code_trade_date_dt"


def test_core_fact_models_keep_compatibility_trade_date_indexes():
    assert {"ix_daily_bars_trade_date", "ix_daily_bars_trade_date_dt"} <= _index_names(DailyBar)
    assert {"ix_fund_flows_trade_date", "ix_fund_flows_trade_date_dt"} <= _index_names(FundFlow)
    assert {"ix_indicators_trade_date", "ix_indicators_trade_date_dt"} <= _index_names(Indicator)
    assert {"ix_patterns_trade_date", "ix_patterns_trade_date_dt"} <= _index_names(Pattern)


def test_core_fact_timescale_migration_contains_required_policy_sql():
    migration = MIGRATION_PATH.read_text()

    assert "CREATE EXTENSION IF NOT EXISTS timescaledb" in migration
    for table in ("daily_bars", "fund_flows", "indicators", "patterns"):
        assert f'"{table}"' in migration

    assert "create_hypertable" in migration
    assert "DROP CONSTRAINT IF EXISTS {table}_pkey" in migration
    assert "PRIMARY KEY (id, trade_date_dt)" in migration
    assert "trade_date_dt" in migration
    assert "add_compression_policy" in migration
    assert "INTERVAL '30 days'" in migration
    assert "INTERVAL '7 days'" in migration
    assert "removes the compression policies only" in migration
