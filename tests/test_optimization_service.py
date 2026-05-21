from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.jobs.tasks import optimization_task
from app.models.stock_model import Base, ParameterOptimizationJob, ParameterOptimizationTrial
from app.schemas.optimization_schema import ParameterOptimizationJobCreate
from app.services.optimization_service import OptimizationService, OptimizationValidationError


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def make_payload(**overrides):
    payload = {
        "name": "ma crossover tuning",
        "base_params": {
            "stock_code": "000001",
            "start_date": "20240101",
            "end_date": "20240131",
            "strategy": "ma_crossover",
            "strategy_params": {"fast_ma": 5, "slow_ma": 20},
        },
        "parameter_space": {
            "fast_ma": {"type": "int", "min": 3, "max": 5},
            "slow_ma": {"type": "int", "min": 10, "max": 12},
        },
        "objective_metric": "sharpe_ratio",
        "trial_count": 3,
        "random_seed": 11,
    }
    payload.update(overrides)
    return ParameterOptimizationJobCreate(**payload)


@pytest.mark.asyncio
async def test_run_job_persists_trials_and_best_parameters(db_session):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload())

    results = [
        {
            "status": "completed",
            "summary": {"sharpe_ratio": 0.7, "total_return": 3.1, "max_drawdown": -2.0},
            "meta": {"strategy": "ma_crossover"},
            "backtest_id": None,
        },
        {
            "status": "completed",
            "summary": {"sharpe_ratio": 1.4, "total_return": 6.2, "max_drawdown": -3.0},
            "meta": {"strategy": "ma_crossover"},
            "backtest_id": None,
        },
        {
            "status": "completed",
            "summary": {"sharpe_ratio": 0.2, "total_return": 1.1, "max_drawdown": -1.0},
            "meta": {"strategy": "ma_crossover"},
            "backtest_id": None,
        },
    ]

    with patch(
        "app.services.optimization_service.BacktestService.run_backtest",
        new=AsyncMock(side_effect=results),
    ):
        completed = await service.run_job(job_id=job.id)

    assert completed.status == "completed"
    assert completed.progress == 100
    assert completed.completed_trials == 3
    assert completed.failed_trials == 0
    assert completed.best_score == 1.4
    assert completed.best_parameters is not None

    trials = (
        await db_session.execute(
            select(ParameterOptimizationTrial)
            .where(ParameterOptimizationTrial.job_id == job.id)
            .order_by(ParameterOptimizationTrial.trial_index)
        )
    ).scalars().all()
    assert [trial.status for trial in trials] == ["completed", "completed", "completed"]
    assert trials[1].score == 1.4

    best = await service.get_best(job_id=job.id, user_id=7)
    assert best["best_score"] == 1.4
    assert best["backtest_params"]["strategy_params"] == {
        **make_payload().base_params["strategy_params"],
        **completed.best_parameters,
    }


@pytest.mark.asyncio
async def test_run_job_records_failed_trial_without_failing_successful_job(db_session):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload(trial_count=2))

    with patch(
        "app.services.optimization_service.BacktestService.run_backtest",
        new=AsyncMock(
            side_effect=[
                {"status": "failed", "error": "not_enough_data"},
                {
                    "status": "completed",
                    "summary": {
                        "sharpe_ratio": 0.8,
                        "total_return": 2.5,
                        "max_drawdown": -1.5,
                    },
                    "meta": {},
                    "backtest_id": None,
                },
            ]
        ),
    ):
        completed = await service.run_job(job_id=job.id)

    assert completed.status == "completed"
    assert completed.completed_trials == 1
    assert completed.failed_trials == 1
    failed_trials = (
        await db_session.execute(
            select(ParameterOptimizationTrial).where(
                ParameterOptimizationTrial.job_id == job.id,
                ParameterOptimizationTrial.status == "failed",
            )
        )
    ).scalars().all()
    assert failed_trials[0].error_message == "not_enough_data"


@pytest.mark.asyncio
async def test_cancel_job_marks_pending_job_terminal(db_session):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload(trial_count=1))

    cancelled = await service.cancel_job(job_id=job.id, user_id=7)

    assert cancelled.status == "cancelled"
    assert cancelled.progress == 100
    assert cancelled.completed_at is not None


@pytest.mark.asyncio
async def test_run_job_keeps_cancelled_state_when_cancelled_during_trial(db_session):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload(trial_count=2))

    async def cancel_during_backtest(*_args, **_kwargs):
        job_row = await db_session.get(ParameterOptimizationJob, job.id)
        job_row.status = "cancelled"
        job_row.progress = 100
        await db_session.commit()
        return {
            "status": "completed",
            "summary": {"sharpe_ratio": 0.7, "total_return": 3.1, "max_drawdown": -2.0},
            "meta": {},
            "backtest_id": None,
        }

    with patch(
        "app.services.optimization_service.BacktestService.run_backtest",
        new=AsyncMock(side_effect=cancel_during_backtest),
    ):
        cancelled = await service.run_job(job_id=job.id)

    assert cancelled.status == "cancelled"
    assert cancelled.progress == 100
    assert cancelled.completed_trials == 0
    assert cancelled.best_parameters is None
    trials = (
        await db_session.execute(
            select(ParameterOptimizationTrial)
            .where(ParameterOptimizationTrial.job_id == job.id)
            .order_by(ParameterOptimizationTrial.trial_index)
        )
    ).scalars().all()
    assert [trial.status for trial in trials] == ["cancelled", "cancelled"]


@pytest.mark.asyncio
async def test_run_job_keeps_cancelled_state_when_cancelled_before_terminal_update(db_session):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload(trial_count=1))
    original_refresh = db_session.refresh
    job_refresh_count = 0

    async def refresh_with_late_cancel(instance, *args, **kwargs):
        nonlocal job_refresh_count
        await original_refresh(instance, *args, **kwargs)
        if isinstance(instance, ParameterOptimizationJob) and instance.id == job.id:
            job_refresh_count += 1
            if job_refresh_count == 4:
                instance.status = "cancelled"
                instance.progress = 100
                instance.completed_at = instance.completed_at or instance.updated_at
                await db_session.commit()
                await original_refresh(instance, *args, **kwargs)

    with (
        patch.object(db_session, "refresh", side_effect=refresh_with_late_cancel),
        patch(
            "app.services.optimization_service.BacktestService.run_backtest",
            new=AsyncMock(
                return_value={
                    "status": "completed",
                    "summary": {"sharpe_ratio": 0.7, "total_return": 3.1, "max_drawdown": -2.0},
                    "meta": {},
                    "backtest_id": None,
                }
            ),
        ),
    ):
        cancelled = await service.run_job(job_id=job.id)

    assert cancelled.status == "cancelled"
    assert cancelled.progress == 100
    await db_session.refresh(job)
    assert job.status == "cancelled"


@pytest.mark.asyncio
async def test_create_job_rejects_impossible_finite_space(db_session):
    service = OptimizationService(db_session)

    with pytest.raises(OptimizationValidationError, match="trial_count exceeds"):
        await service.create_job(
            user_id=7,
            payload=make_payload(
                parameter_space={"fast_ma": [3]},
                trial_count=2,
            ),
        )


def test_random_search_is_deterministic_for_seed():
    service = OptimizationService(db=object())
    space = {
        "fast_ma": {"type": "int", "min": 3, "max": 8},
        "slow_ma": {"type": "int", "min": 10, "max": 20},
    }

    first = service._generate_candidates(space, trial_count=5, random_seed=42)
    second = service._generate_candidates(space, trial_count=5, random_seed=42)

    assert first == second


def test_int_range_rejects_non_integer_step():
    service = OptimizationService(db=object())

    with pytest.raises(OptimizationValidationError, match="integer for int ranges"):
        service._validate_parameter_space(
            {"fast_ma": {"type": "int", "min": 3, "max": 8, "step": 0.5}},
            trial_count=2,
        )


@pytest.mark.asyncio
async def test_task_runner_marks_job_failed_on_task_level_exception(db_session, monkeypatch):
    service = OptimizationService(db_session)
    job = await service.create_job(user_id=7, payload=make_payload(trial_count=1))

    class SessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, *_args):
            return False

    async def raise_task_error(self, *, job_id: int):
        raise RuntimeError(f"task exploded: {job_id}")

    monkeypatch.setattr(optimization_task, "async_session_factory", lambda: SessionContext())
    monkeypatch.setattr(OptimizationService, "run_job", raise_task_error)

    await optimization_task.run_optimization_job(job.id)

    failed = await db_session.get(ParameterOptimizationJob, job.id)
    assert failed.status == "failed"
    assert failed.progress == 100
    assert "task exploded" in failed.error_message
