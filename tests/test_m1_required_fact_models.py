from pathlib import Path

from app.models.stock_model import DailyBasic, StockST, TechnicalFactor

MIGRATION_PATH = Path("alembic/versions/2026_04_08_0002-m1_required_fact_tables.py")


def _unique_constraint_columns(model, name: str) -> tuple[str, ...]:
    for constraint in model.__table__.constraints:
        if constraint.name == name:
            return tuple(column.name for column in constraint.columns)
    raise AssertionError(f"Constraint {name} not found on {model.__tablename__}")


def _index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def test_required_fact_models_use_trade_date_dt_uniqueness():
    assert _unique_constraint_columns(DailyBasic, "uq_daily_basic_ts_code_trade_date_dt") == (
        "ts_code",
        "trade_date_dt",
    )
    assert _unique_constraint_columns(StockST, "uq_stock_st_ts_code_trade_date_dt") == (
        "ts_code",
        "trade_date_dt",
    )
    assert _unique_constraint_columns(
        TechnicalFactor, "uq_technical_factors_ts_code_trade_date_dt"
    ) == ("ts_code", "trade_date_dt")


def test_required_fact_models_keep_trade_date_compatibility_indexes():
    assert {
        "ix_daily_basic_ts_code",
        "ix_daily_basic_trade_date",
        "ix_daily_basic_trade_date_dt",
    } <= _index_names(DailyBasic)
    assert {
        "ix_stock_st_ts_code",
        "ix_stock_st_trade_date",
        "ix_stock_st_trade_date_dt",
    } <= _index_names(StockST)
    assert {
        "ix_technical_factors_ts_code",
        "ix_technical_factors_trade_date",
        "ix_technical_factors_trade_date_dt",
    } <= _index_names(TechnicalFactor)


def test_required_fact_migration_chain_and_tables():
    migration = MIGRATION_PATH.read_text()

    assert 'down_revision: Union[str, None] = "m1_core_fact_timescale"' in migration
    for table in ("daily_basic", "stock_st", "technical_factors"):
        assert f'"{table}"' in migration
        assert f'op.drop_table("{table}")' in migration


def test_technical_factors_uses_jsonb_factor_bag():
    migration = MIGRATION_PATH.read_text()

    assert "postgresql.JSONB" in migration
    assert "factors" in TechnicalFactor.__table__.columns
    assert "factors" in migration
