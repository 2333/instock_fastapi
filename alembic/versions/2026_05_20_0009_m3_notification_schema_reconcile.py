"""Reconcile M3 notification columns for existing databases.

Revision ID: m3_notification_schema_reconcile
Revises: m3_alert_run_definition_snapshot
Create Date: 2026-05-20 10:42:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "m3_notification_schema_reconcile"
down_revision = "m3_alert_run_definition_snapshot"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def _column_names(bind, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()
    return {column["name"] for column in inspect(bind).get_columns(table_name)}


def _index_names(bind, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()
    return {index["name"] for index in inspect(bind).get_indexes(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "notifications"):
        return

    columns = _column_names(bind, "notifications")
    if "alert_condition_id" not in columns:
        op.add_column("notifications", sa.Column("alert_condition_id", sa.Integer(), nullable=True))
    if "notification_type" not in columns:
        op.add_column(
            "notifications", sa.Column("notification_type", sa.String(length=40), nullable=True)
        )
    if "dedupe_key" not in columns:
        op.add_column("notifications", sa.Column("dedupe_key", sa.String(length=128), nullable=True))
    if "ts_code" not in columns:
        op.add_column(
            "notifications",
            sa.Column("ts_code", sa.String(length=20), nullable=False, server_default=""),
        )
        op.alter_column("notifications", "ts_code", server_default=None)

    indexes = _index_names(bind, "notifications")
    columns = _column_names(bind, "notifications")
    if "alert_condition_id" in columns and "ix_notifications_alert_condition_id" not in indexes:
        op.create_index(
            "ix_notifications_alert_condition_id", "notifications", ["alert_condition_id"]
        )
    if "notification_type" in columns and "ix_notifications_notification_type" not in indexes:
        op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    if "dedupe_key" in columns and "uq_notifications_dedupe_key" not in indexes:
        op.create_index(
            "uq_notifications_dedupe_key",
            "notifications",
            ["dedupe_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "notifications"):
        return

    indexes = _index_names(bind, "notifications")
    if "ix_notifications_notification_type" in indexes:
        op.drop_index("ix_notifications_notification_type", table_name="notifications")
    if "ix_notifications_alert_condition_id" in indexes:
        op.drop_index("ix_notifications_alert_condition_id", table_name="notifications")
    if "uq_notifications_dedupe_key" in indexes:
        op.drop_index("uq_notifications_dedupe_key", table_name="notifications")

    columns = _column_names(bind, "notifications")
    for column_name in ("ts_code", "dedupe_key", "notification_type", "alert_condition_id"):
        if column_name in columns:
            op.drop_column("notifications", column_name)
