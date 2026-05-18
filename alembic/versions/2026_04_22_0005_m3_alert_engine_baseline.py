"""m3 alert engine baseline

Revision ID: m3_alert_engine_baseline
Revises: m2_user_events
Create Date: 2026-04-22 00:05:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "m3_alert_engine_baseline"
down_revision: Union[str, None] = "m2_user_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(bind: sa.Connection, table_name: str) -> bool:
    return sa.inspect(bind).has_table(table_name)


def _index_names(bind: sa.Connection, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()
    return {index["name"] for index in sa.inspect(bind).get_indexes(table_name)}


def _column_names(bind: sa.Connection, table_name: str) -> set[str]:
    if not _table_exists(bind, table_name):
        return set()
    return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}


_ALERT_BASELINE_COLUMNS = {
    "id",
    "user_id",
    "ts_code",
    "rule_type",
    "threshold",
    "cooldown_minutes",
    "is_active",
    "created_at",
    "updated_at",
}
_NOTIFICATION_BASELINE_COLUMNS = {
    "id",
    "user_id",
    "alert_condition_id",
    "ts_code",
    "title",
    "message",
    "payload",
    "is_read",
    "read_at",
    "created_at",
}


def upgrade() -> None:
    bind = op.get_bind()

    if not _table_exists(bind, "alert_conditions"):
        op.create_table(
            "alert_conditions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("ts_code", sa.String(length=20), nullable=False),
            sa.Column("rule_type", sa.String(length=20), nullable=False),
            sa.Column("threshold", sa.Numeric(20, 6), nullable=False),
            sa.Column("cooldown_minutes", sa.Integer(), nullable=False, server_default=sa.text("60")),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.CheckConstraint(
                "rule_type IN ('price_above', 'price_below', 'change_above', 'change_below')",
                name="ck_alert_conditions_rule_type",
            ),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.UniqueConstraint(
                "user_id",
                "ts_code",
                "rule_type",
                "threshold",
                name="uq_alert_conditions_user_ts_code_rule_type_threshold",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
    alert_indexes = _index_names(bind, "alert_conditions")
    alert_columns = _column_names(bind, "alert_conditions")
    if "user_id" in alert_columns and "ix_alert_conditions_user_id" not in alert_indexes:
        op.create_index("ix_alert_conditions_user_id", "alert_conditions", ["user_id"])
    if "ts_code" in alert_columns and "ix_alert_conditions_ts_code" not in alert_indexes:
        op.create_index("ix_alert_conditions_ts_code", "alert_conditions", ["ts_code"])

    if not _table_exists(bind, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("alert_condition_id", sa.Integer(), nullable=True),
            sa.Column("ts_code", sa.String(length=20), nullable=False),
            sa.Column("title", sa.String(length=120), nullable=True),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["alert_condition_id"], ["alert_conditions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    notification_indexes = _index_names(bind, "notifications")
    notification_columns = _column_names(bind, "notifications")
    if "user_id" in notification_columns and "ix_notifications_user_id" not in notification_indexes:
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    if (
        {"user_id", "is_read"} <= notification_columns
        and "ix_notifications_user_unread" not in notification_indexes
    ):
        op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])
    if (
        "alert_condition_id" in notification_columns
        and "ix_notifications_alert_condition_id" not in notification_indexes
    ):
        op.create_index(
            "ix_notifications_alert_condition_id", "notifications", ["alert_condition_id"]
        )


def downgrade() -> None:
    bind = op.get_bind()

    if _table_exists(bind, "notifications"):
        notification_indexes = _index_names(bind, "notifications")
        notification_columns = _column_names(bind, "notifications")
        if "ix_notifications_alert_condition_id" in notification_indexes:
            op.drop_index("ix_notifications_alert_condition_id", table_name="notifications")
        if "ix_notifications_user_unread" in notification_indexes:
            op.drop_index("ix_notifications_user_unread", table_name="notifications")
        if "ix_notifications_user_id" in notification_indexes:
            op.drop_index("ix_notifications_user_id", table_name="notifications")
        if _NOTIFICATION_BASELINE_COLUMNS <= notification_columns:
            op.drop_table("notifications")

    if _table_exists(bind, "alert_conditions"):
        alert_indexes = _index_names(bind, "alert_conditions")
        alert_columns = _column_names(bind, "alert_conditions")
        if "ix_alert_conditions_ts_code" in alert_indexes:
            op.drop_index("ix_alert_conditions_ts_code", table_name="alert_conditions")
        if "ix_alert_conditions_user_id" in alert_indexes:
            op.drop_index("ix_alert_conditions_user_id", table_name="alert_conditions")
        if _ALERT_BASELINE_COLUMNS <= alert_columns:
            op.drop_table("alert_conditions")
