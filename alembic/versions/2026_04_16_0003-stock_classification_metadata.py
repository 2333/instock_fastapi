"""stock classification metadata

Revision ID: stock_classification_metadata
Revises: m1_required_fact_tables
Create Date: 2026-04-16 00:03:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "stock_classification_metadata"
down_revision: Union[str, None] = "m1_required_fact_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stocks", sa.Column("industry_label", sa.String(length=50), nullable=True))
    op.add_column("stocks", sa.Column("industry_taxonomy", sa.String(length=80), nullable=True))
    op.add_column("stocks", sa.Column("industry_source", sa.String(length=20), nullable=True))
    op.add_column("stocks", sa.Column("industry_updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("stocks", "industry_updated_at")
    op.drop_column("stocks", "industry_source")
    op.drop_column("stocks", "industry_taxonomy")
    op.drop_column("stocks", "industry_label")
