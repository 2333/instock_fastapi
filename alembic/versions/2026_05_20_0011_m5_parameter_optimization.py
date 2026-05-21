"""Add M5 parameter optimization job and trial tables.

Revision ID: m5_parameter_optimization
Revises: m3_notification_legacy_type_nullable
Create Date: 2026-05-20 18:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "m5_parameter_optimization"
down_revision = "m3_notification_legacy_type_nullable"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "parameter_optimization_jobs"):
        op.create_table(
            "parameter_optimization_jobs",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=True),
            sa.Column("method", sa.String(length=30), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False),
            sa.Column("base_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("parameter_space", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("objective_metric", sa.String(length=40), nullable=False),
            sa.Column("objective_direction", sa.String(length=10), nullable=False),
            sa.Column("trial_count", sa.Integer(), nullable=False),
            sa.Column("completed_trials", sa.Integer(), nullable=False),
            sa.Column("failed_trials", sa.Integer(), nullable=False),
            sa.Column("random_seed", sa.Integer(), nullable=True),
            sa.Column("best_trial_id", sa.Integer(), nullable=True),
            sa.Column("best_parameters", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("best_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("best_score", sa.Float(), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
                name="ck_parameter_optimization_jobs_status",
            ),
            sa.CheckConstraint(
                "method IN ('random_search')",
                name="ck_parameter_optimization_jobs_method",
            ),
            sa.CheckConstraint(
                "objective_direction IN ('maximize', 'minimize')",
                name="ck_parameter_optimization_jobs_objective_direction",
            ),
            sa.CheckConstraint(
                "objective_metric IN ('sharpe_ratio', 'total_return', 'max_drawdown')",
                name="ck_parameter_optimization_jobs_objective_metric",
            ),
            sa.CheckConstraint(
                "trial_count >= 1 AND trial_count <= 50",
                name="ck_parameter_optimization_jobs_trial_count",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_parameter_optimization_jobs_user_created",
            "parameter_optimization_jobs",
            ["user_id", "created_at"],
        )
        op.create_index(
            "ix_parameter_optimization_jobs_status",
            "parameter_optimization_jobs",
            ["status"],
        )

    if not _table_exists(bind, "parameter_optimization_trials"):
        op.create_table(
            "parameter_optimization_trials",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("job_id", sa.Integer(), nullable=False),
            sa.Column("trial_index", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
            sa.Column("metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("score", sa.Float(), nullable=True),
            sa.Column("backtest_result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.CheckConstraint(
                "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')",
                name="ck_parameter_optimization_trials_status",
            ),
            sa.ForeignKeyConstraint(["job_id"], ["parameter_optimization_jobs.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "job_id",
                "trial_index",
                name="uq_parameter_optimization_trials_job_index",
            ),
        )
        op.create_index(
            "ix_parameter_optimization_trials_job_id",
            "parameter_optimization_trials",
            ["job_id"],
        )
        op.create_index(
            "ix_parameter_optimization_trials_status",
            "parameter_optimization_trials",
            ["status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "parameter_optimization_trials"):
        op.drop_index(
            "ix_parameter_optimization_trials_status",
            table_name="parameter_optimization_trials",
        )
        op.drop_index(
            "ix_parameter_optimization_trials_job_id",
            table_name="parameter_optimization_trials",
        )
        op.drop_table("parameter_optimization_trials")
    if _table_exists(bind, "parameter_optimization_jobs"):
        op.drop_index(
            "ix_parameter_optimization_jobs_status",
            table_name="parameter_optimization_jobs",
        )
        op.drop_index(
            "ix_parameter_optimization_jobs_user_created",
            table_name="parameter_optimization_jobs",
        )
        op.drop_table("parameter_optimization_jobs")
