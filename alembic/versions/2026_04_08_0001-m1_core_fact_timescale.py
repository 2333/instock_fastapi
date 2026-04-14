"""m1 core fact timescale

Revision ID: m1_core_fact_timescale
Revises: None
Create Date: 2026-04-08 00:01:00
"""

from typing import Sequence, Union

from alembic import op


revision: str = "m1_core_fact_timescale"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CORE_TABLES = {
    "daily_bars": {
        "old_constraints": ["uq_daily_bars_ts_code_trade_date"],
        "new_constraint": "uq_daily_bars_ts_code_trade_date_dt",
        "unique_columns": ["ts_code", "trade_date_dt"],
        "indexes": ["trade_date_dt"],
        "segmentby": "ts_code",
    },
    "fund_flows": {
        "old_constraints": ["uq_fund_flows_ts_code_trade_date"],
        "new_constraint": "uq_fund_flows_ts_code_trade_date_dt",
        "unique_columns": ["ts_code", "trade_date_dt"],
        "indexes": ["trade_date_dt"],
        "segmentby": "ts_code",
    },
    "indicators": {
        "old_constraints": ["uq_indicators_ts_code_date_name"],
        "new_constraint": "uq_indicators_ts_code_trade_date_dt_name",
        "unique_columns": ["ts_code", "trade_date_dt", "indicator_name"],
        "indexes": ["trade_date_dt"],
        "segmentby": "ts_code, indicator_name",
    },
    "patterns": {
        "old_constraints": [],
        "new_constraint": None,
        "unique_columns": [],
        "indexes": ["trade_date_dt"],
        "segmentby": "ts_code, pattern_name",
    },
}


def _quote_list(columns: list[str]) -> str:
    return ", ".join(columns)


def _backfill_trade_date_dt(table: str) -> None:
    op.execute(
        f"""
        UPDATE {table}
        SET trade_date_dt = to_date(trade_date, 'YYYYMMDD')
        WHERE trade_date_dt IS NULL
          AND trade_date IS NOT NULL
          AND trade_date ~ '^[0-9]{{8}}$'
        """
    )


def _ensure_no_null_trade_date_dt(table: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM {table}
                WHERE trade_date_dt IS NULL
                LIMIT 1
            ) THEN
                RAISE EXCEPTION
                    'Cannot convert {table} to Timescale hypertable: trade_date_dt contains NULL values';
            END IF;
        END
        $$;
        """
    )


def _drop_constraint_if_exists(table: str, constraint: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}")


def _add_unique_constraint_if_missing(table: str, constraint: str, columns: list[str]) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = '{table}'::regclass
                  AND conname = '{constraint}'
            ) THEN
                ALTER TABLE {table}
                ADD CONSTRAINT {constraint} UNIQUE ({_quote_list(columns)});
            END IF;
        END
        $$;
        """
    )


def _create_index_if_missing(table: str, column: str) -> None:
    op.execute(
        f"""
        CREATE INDEX IF NOT EXISTS ix_{table}_{column}
        ON {table} ({column})
        """
    )


def _replace_primary_key_with_timescale_key(table: str) -> None:
    op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {table}_pkey")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = '{table}'::regclass
                  AND conname = '{table}_pkey'
            ) THEN
                ALTER TABLE {table}
                ADD CONSTRAINT {table}_pkey PRIMARY KEY (id, trade_date_dt);
            END IF;
        END
        $$;
        """
    )


def _create_hypertable(table: str) -> None:
    op.execute(
        f"""
        SELECT create_hypertable(
            '{table}',
            'trade_date_dt',
            if_not_exists => TRUE,
            migrate_data => TRUE,
            chunk_time_interval => INTERVAL '7 days'
        )
        """
    )


def _enable_compression(table: str, segmentby: str) -> None:
    op.execute(
        f"""
        ALTER TABLE {table} SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = '{segmentby}',
            timescaledb.compress_orderby = 'trade_date_dt DESC'
        )
        """
    )
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM timescaledb_information.jobs
                WHERE hypertable_name = '{table}'
                  AND proc_name = 'policy_compression'
            ) THEN
                PERFORM add_compression_policy('{table}', INTERVAL '30 days');
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    for table, policy in CORE_TABLES.items():
        _backfill_trade_date_dt(table)
        _ensure_no_null_trade_date_dt(table)
        _replace_primary_key_with_timescale_key(table)

        for constraint in policy["old_constraints"]:
            _drop_constraint_if_exists(table, constraint)

        if policy["new_constraint"]:
            _add_unique_constraint_if_missing(
                table,
                policy["new_constraint"],
                policy["unique_columns"],
            )

        for column in policy["indexes"]:
            _create_index_if_missing(table, column)

        _create_hypertable(table)
        _enable_compression(table, policy["segmentby"])


def downgrade() -> None:
    for table in CORE_TABLES:
        op.execute(f"SELECT remove_compression_policy('{table}', if_exists => TRUE)")

    op.execute(
        """
        /*
        TimescaleDB does not provide a safe generic "convert hypertable back to
        plain PostgreSQL table" operation for populated tables. Downgrade
        removes the compression policies only. Hypertable status, Timescale-
        compatible primary keys, and uniqueness changes must be rolled back from
        a database backup or a table-copy procedure approved in the release
        artifact.
        */
        """
    )
