"""M3-B alert subscription baseline.

Revision ID: m3_alert_subscription_baseline
Revises: m3_saved_screener_condition_versioning
Create Date: 2026-04-24 10:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "m3_alert_subscription_baseline"
down_revision = "m3_saved_screener_condition_versioning"
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

    if not _table_exists(bind, "alert_subscriptions"):
        op.create_table(
            "alert_subscriptions",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("selection_condition_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=True),
            sa.Column("schedule_type", sa.String(length=20), nullable=False, server_default="post_close"),
            sa.Column("cooldown_trade_days", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("definition_version", sa.Integer(), nullable=False),
            sa.Column("definition_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("last_run_trade_date", sa.String(length=10), nullable=True),
            sa.Column("last_run_at", sa.DateTime(), nullable=True),
            sa.Column("last_notified_trade_date", sa.String(length=10), nullable=True),
            sa.Column("stale_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "user_id",
                "selection_condition_id",
                "definition_hash",
                "schedule_type",
                name="uq_alert_subscriptions_user_condition_hash_schedule",
            ),
        )

    subscription_indexes = _index_names(bind, "alert_subscriptions")
    if "ix_alert_subscriptions_user_id" not in subscription_indexes:
        op.create_index("ix_alert_subscriptions_user_id", "alert_subscriptions", ["user_id"])
    if "ix_alert_subscriptions_selection_condition_id" not in subscription_indexes:
        op.create_index(
            "ix_alert_subscriptions_selection_condition_id",
            "alert_subscriptions",
            ["selection_condition_id"],
        )
    if "ix_alert_subscriptions_status" not in subscription_indexes:
        op.create_index("ix_alert_subscriptions_status", "alert_subscriptions", ["status"])

    if not _table_exists(bind, "alert_runs"):
        op.create_table(
            "alert_runs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("subscription_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("selection_condition_id", sa.Integer(), nullable=False),
            sa.Column("trade_date", sa.String(length=10), nullable=False),
            sa.Column("definition_version", sa.Integer(), nullable=False),
            sa.Column("definition_hash", sa.String(length=64), nullable=False),
            sa.Column("definition_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="completed"),
            sa.Column("match_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("new_match_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("notification_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "subscription_id",
                "trade_date",
                "definition_hash",
                name="uq_alert_runs_subscription_trade_date_definition_hash",
            ),
        )

    run_indexes = _index_names(bind, "alert_runs")
    if "ix_alert_runs_subscription_id" not in run_indexes:
        op.create_index("ix_alert_runs_subscription_id", "alert_runs", ["subscription_id"])
    if "ix_alert_runs_trade_date" not in run_indexes:
        op.create_index("ix_alert_runs_trade_date", "alert_runs", ["trade_date"])
    if "ix_alert_runs_user_id" not in run_indexes:
        op.create_index("ix_alert_runs_user_id", "alert_runs", ["user_id"])

    if not _table_exists(bind, "alert_run_hits"):
        op.create_table(
            "alert_run_hits",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("run_id", sa.Integer(), nullable=False),
            sa.Column("ts_code", sa.String(length=20), nullable=False),
            sa.Column("trade_date", sa.String(length=10), nullable=False),
            sa.Column("rank", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("score", sa.Numeric(precision=10, scale=4), nullable=True),
            sa.Column("signal", sa.String(length=20), nullable=True),
            sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("run_id", "ts_code", name="uq_alert_run_hits_run_ts_code"),
        )

    hit_indexes = _index_names(bind, "alert_run_hits")
    if "ix_alert_run_hits_run_id" not in hit_indexes:
        op.create_index("ix_alert_run_hits_run_id", "alert_run_hits", ["run_id"])
    if "ix_alert_run_hits_ts_code" not in hit_indexes:
        op.create_index("ix_alert_run_hits_ts_code", "alert_run_hits", ["ts_code"])

    notification_columns = _column_names(bind, "notifications")
    if "subscription_id" not in notification_columns:
        op.add_column("notifications", sa.Column("subscription_id", sa.Integer(), nullable=True))
    if "alert_run_id" not in notification_columns:
        op.add_column("notifications", sa.Column("alert_run_id", sa.Integer(), nullable=True))
    if "notification_type" not in notification_columns:
        op.add_column("notifications", sa.Column("notification_type", sa.String(length=40), nullable=True))
    if "dedupe_key" not in notification_columns:
        op.add_column("notifications", sa.Column("dedupe_key", sa.String(length=128), nullable=True))

    notification_indexes = _index_names(bind, "notifications")
    if (
        "subscription_id" in _column_names(bind, "notifications")
        and "ix_notifications_subscription_id" not in notification_indexes
    ):
        op.create_index("ix_notifications_subscription_id", "notifications", ["subscription_id"])
    if (
        "alert_run_id" in _column_names(bind, "notifications")
        and "ix_notifications_alert_run_id" not in notification_indexes
    ):
        op.create_index("ix_notifications_alert_run_id", "notifications", ["alert_run_id"])
    if (
        "dedupe_key" in _column_names(bind, "notifications")
        and "uq_notifications_dedupe_key" not in notification_indexes
    ):
        op.create_index(
            "uq_notifications_dedupe_key",
            "notifications",
            ["dedupe_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()

    notification_columns = _column_names(bind, "notifications")
    notification_indexes = _index_names(bind, "notifications")
    if "ix_notifications_subscription_id" in notification_indexes:
        op.drop_index("ix_notifications_subscription_id", table_name="notifications")
    if "ix_notifications_alert_run_id" in notification_indexes:
        op.drop_index("ix_notifications_alert_run_id", table_name="notifications")
    if "uq_notifications_dedupe_key" in notification_indexes:
        op.drop_index("uq_notifications_dedupe_key", table_name="notifications")
    if "subscription_id" in notification_columns:
        op.drop_column("notifications", "subscription_id")
    if "alert_run_id" in notification_columns:
        op.drop_column("notifications", "alert_run_id")
    if "notification_type" in notification_columns:
        op.drop_column("notifications", "notification_type")
    if "dedupe_key" in notification_columns:
        op.drop_column("notifications", "dedupe_key")

    hit_indexes = _index_names(bind, "alert_run_hits")
    if "ix_alert_run_hits_run_id" in hit_indexes:
        op.drop_index("ix_alert_run_hits_run_id", table_name="alert_run_hits")
    if "ix_alert_run_hits_ts_code" in hit_indexes:
        op.drop_index("ix_alert_run_hits_ts_code", table_name="alert_run_hits")
    if _table_exists(bind, "alert_run_hits"):
        op.drop_table("alert_run_hits")

    run_indexes = _index_names(bind, "alert_runs")
    if "ix_alert_runs_subscription_id" in run_indexes:
        op.drop_index("ix_alert_runs_subscription_id", table_name="alert_runs")
    if "ix_alert_runs_trade_date" in run_indexes:
        op.drop_index("ix_alert_runs_trade_date", table_name="alert_runs")
    if "ix_alert_runs_user_id" in run_indexes:
        op.drop_index("ix_alert_runs_user_id", table_name="alert_runs")
    if _table_exists(bind, "alert_runs"):
        op.drop_table("alert_runs")

    subscription_indexes = _index_names(bind, "alert_subscriptions")
    if "ix_alert_subscriptions_user_id" in subscription_indexes:
        op.drop_index("ix_alert_subscriptions_user_id", table_name="alert_subscriptions")
    if "ix_alert_subscriptions_selection_condition_id" in subscription_indexes:
        op.drop_index(
            "ix_alert_subscriptions_selection_condition_id",
            table_name="alert_subscriptions",
        )
    if "ix_alert_subscriptions_status" in subscription_indexes:
        op.drop_index("ix_alert_subscriptions_status", table_name="alert_subscriptions")
    if _table_exists(bind, "alert_subscriptions"):
        op.drop_table("alert_subscriptions")
