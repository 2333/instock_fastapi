"""Reconcile M3 alert run definition snapshot column.

Revision ID: m3_alert_run_definition_snapshot
Revises: m3_alert_subscription_baseline
Create Date: 2026-05-20 10:35:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "m3_alert_run_definition_snapshot"
down_revision = "m3_alert_subscription_baseline"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def _column_names(bind, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "alert_runs") and "definition_snapshot" not in _column_names(
        bind, "alert_runs"
    ):
        op.add_column(
            "alert_runs",
            sa.Column("definition_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "alert_runs") and "definition_snapshot" in _column_names(
        bind, "alert_runs"
    ):
        op.drop_column("alert_runs", "definition_snapshot")
