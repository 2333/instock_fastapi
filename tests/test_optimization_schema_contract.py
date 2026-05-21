from pathlib import Path

from app.models.stock_model import ParameterOptimizationJob, ParameterOptimizationTrial

MIGRATION_PATH = Path("alembic/versions/2026_05_20_0011_m5_parameter_optimization.py")


def _constraint_names(model) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints}


def _index_names(model) -> set[str]:
    return {index.name for index in model.__table__.indexes}


def test_parameter_optimization_job_model_contract():
    assert ParameterOptimizationJob.__table__.name == "parameter_optimization_jobs"
    for column in (
        "id",
        "user_id",
        "method",
        "status",
        "progress",
        "base_params",
        "parameter_space",
        "objective_metric",
        "objective_direction",
        "trial_count",
        "completed_trials",
        "failed_trials",
        "random_seed",
        "best_trial_id",
        "best_parameters",
        "best_metrics",
        "best_score",
        "error_message",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
    ):
        assert column in ParameterOptimizationJob.__table__.columns

    assert {
        "ix_parameter_optimization_jobs_user_created",
        "ix_parameter_optimization_jobs_status",
    } <= _index_names(ParameterOptimizationJob)
    assert {
        "ck_parameter_optimization_jobs_status",
        "ck_parameter_optimization_jobs_method",
        "ck_parameter_optimization_jobs_objective_direction",
        "ck_parameter_optimization_jobs_objective_metric",
        "ck_parameter_optimization_jobs_trial_count",
    } <= _constraint_names(ParameterOptimizationJob)


def test_parameter_optimization_trial_model_contract():
    assert ParameterOptimizationTrial.__table__.name == "parameter_optimization_trials"
    for column in (
        "id",
        "job_id",
        "trial_index",
        "status",
        "params",
        "metrics",
        "score",
        "backtest_result",
        "error_message",
        "created_at",
        "started_at",
        "completed_at",
    ):
        assert column in ParameterOptimizationTrial.__table__.columns

    assert {
        "ix_parameter_optimization_trials_job_id",
        "ix_parameter_optimization_trials_status",
    } <= _index_names(ParameterOptimizationTrial)
    assert {
        "ck_parameter_optimization_trials_status",
        "uq_parameter_optimization_trials_job_index",
    } <= _constraint_names(ParameterOptimizationTrial)


def test_parameter_optimization_migration_contract():
    migration = MIGRATION_PATH.read_text()

    assert 'down_revision = "m3_notification_legacy_type_nullable"' in migration
    assert 'op.create_table(\n            "parameter_optimization_jobs"' in migration
    assert 'op.create_table(\n            "parameter_optimization_trials"' in migration
    assert '"base_params", postgresql.JSONB' in migration
    assert '"parameter_space", postgresql.JSONB' in migration
    assert '"params", postgresql.JSONB' in migration
    assert '"metrics", postgresql.JSONB' in migration
    assert '"backtest_result", postgresql.JSONB' in migration
    assert "ck_parameter_optimization_jobs_status" in migration
    assert "ck_parameter_optimization_jobs_objective_metric" in migration
    assert "ck_parameter_optimization_trials_status" in migration
    assert "ix_parameter_optimization_jobs_user_created" in migration
    assert "ix_parameter_optimization_trials_job_id" in migration
    assert 'op.drop_table("parameter_optimization_trials")' in migration
    assert 'op.drop_table("parameter_optimization_jobs")' in migration
