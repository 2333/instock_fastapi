"""m1 required fact tables

Revision ID: m1_required_fact_tables
Revises: m1_core_fact_timescale
Create Date: 2026-04-08 00:02:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m1_required_fact_tables"
down_revision: Union[str, None] = "m1_core_fact_timescale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_basic",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=10), nullable=False),
        sa.Column("trade_date_dt", sa.Date(), nullable=False),
        sa.Column("turnover_rate", sa.Numeric(20, 6), nullable=True),
        sa.Column("turnover_rate_f", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume_ratio", sa.Numeric(20, 6), nullable=True),
        sa.Column("pe", sa.Numeric(20, 6), nullable=True),
        sa.Column("pe_ttm", sa.Numeric(20, 6), nullable=True),
        sa.Column("pb", sa.Numeric(20, 6), nullable=True),
        sa.Column("ps", sa.Numeric(20, 6), nullable=True),
        sa.Column("ps_ttm", sa.Numeric(20, 6), nullable=True),
        sa.Column("dv_ratio", sa.Numeric(20, 6), nullable=True),
        sa.Column("dv_ttm", sa.Numeric(20, 6), nullable=True),
        sa.Column("total_share", sa.Numeric(30, 6), nullable=True),
        sa.Column("float_share", sa.Numeric(30, 6), nullable=True),
        sa.Column("free_share", sa.Numeric(30, 6), nullable=True),
        sa.Column("total_mv", sa.Numeric(30, 6), nullable=True),
        sa.Column("circ_mv", sa.Numeric(30, 6), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            name="uq_daily_basic_ts_code_trade_date_dt",
        ),
    )
    op.create_index("ix_daily_basic_ts_code", "daily_basic", ["ts_code"])
    op.create_index("ix_daily_basic_trade_date", "daily_basic", ["trade_date"])
    op.create_index("ix_daily_basic_trade_date_dt", "daily_basic", ["trade_date_dt"])

    op.create_table(
        "stock_st",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=10), nullable=False),
        sa.Column("trade_date_dt", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("st_type", sa.String(length=50), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("begin_date", sa.String(length=10), nullable=True),
        sa.Column("end_date", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            name="uq_stock_st_ts_code_trade_date_dt",
        ),
    )
    op.create_index("ix_stock_st_ts_code", "stock_st", ["ts_code"])
    op.create_index("ix_stock_st_trade_date", "stock_st", ["trade_date"])
    op.create_index("ix_stock_st_trade_date_dt", "stock_st", ["trade_date_dt"])

    op.create_table(
        "technical_factors",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ts_code", sa.String(length=20), nullable=False),
        sa.Column("trade_date", sa.String(length=10), nullable=False),
        sa.Column("trade_date_dt", sa.Date(), nullable=False),
        sa.Column("factors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ts_code",
            "trade_date_dt",
            name="uq_technical_factors_ts_code_trade_date_dt",
        ),
    )
    op.create_index("ix_technical_factors_ts_code", "technical_factors", ["ts_code"])
    op.create_index("ix_technical_factors_trade_date", "technical_factors", ["trade_date"])
    op.create_index(
        "ix_technical_factors_trade_date_dt",
        "technical_factors",
        ["trade_date_dt"],
    )


def downgrade() -> None:
    op.drop_index("ix_technical_factors_trade_date_dt", table_name="technical_factors")
    op.drop_index("ix_technical_factors_trade_date", table_name="technical_factors")
    op.drop_index("ix_technical_factors_ts_code", table_name="technical_factors")
    op.drop_table("technical_factors")

    op.drop_index("ix_stock_st_trade_date_dt", table_name="stock_st")
    op.drop_index("ix_stock_st_trade_date", table_name="stock_st")
    op.drop_index("ix_stock_st_ts_code", table_name="stock_st")
    op.drop_table("stock_st")

    op.drop_index("ix_daily_basic_trade_date_dt", table_name="daily_basic")
    op.drop_index("ix_daily_basic_trade_date", table_name="daily_basic")
    op.drop_index("ix_daily_basic_ts_code", table_name="daily_basic")
    op.drop_table("daily_basic")
