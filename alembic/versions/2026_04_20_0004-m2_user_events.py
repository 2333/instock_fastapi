"""m2 user events

Revision ID: m2_user_events
Revises: stock_classification_metadata
Create Date: 2026-04-20 00:04:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "m2_user_events"
down_revision: Union[str, None] = "stock_classification_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("event_version", sa.Integer(), nullable=False),
        sa.Column("page", sa.String(length=120), nullable=False),
        sa.Column("referrer", sa.String(length=255), nullable=True),
        sa.Column("event_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_events_user_created", "user_events", ["user_id", "created_at"])
    op.create_index(
        "ix_user_events_event_type_created",
        "user_events",
        ["event_type", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_events_event_type_created", table_name="user_events")
    op.drop_index("ix_user_events_user_created", table_name="user_events")
    op.drop_table("user_events")
