"""Relax legacy notification type column for M3 notification writes.

Revision ID: m3_notification_legacy_type_nullable
Revises: m3_notification_schema_reconcile
Create Date: 2026-05-20 10:51:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "m3_notification_legacy_type_nullable"
down_revision = "m3_notification_schema_reconcile"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def _columns(bind, table_name: str) -> dict[str, dict]:
    if not _table_exists(bind, table_name):
        return {}
    return {column["name"]: column for column in inspect(bind).get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "notifications")
    if "type" in columns and not columns["type"].get("nullable", True):
        op.alter_column(
            "notifications",
            "type",
            existing_type=sa.String(length=50),
            nullable=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "notifications")
    if "type" in columns and columns["type"].get("nullable", True):
        op.alter_column(
            "notifications",
            "type",
            existing_type=sa.String(length=50),
            nullable=False,
        )
