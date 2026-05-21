# W1 Backend V1 Alignment

Date: 2026-05-20

## Scope

Deliver the backend `M5 / P3-05` v1 closed loop:

```text
backtest config
  -> create parameter optimization job
  -> run bounded random-search trials
  -> persist trial status and metrics
  -> compute best parameters
  -> expose best parameters for Backtest reuse
```

## Write Set

- `app/models/stock_model.py`
- `app/models/__init__.py`
- `app/schemas/optimization_schema.py`
- `app/services/optimization_service.py`
- `app/jobs/tasks/optimization_task.py`
- `app/api/routers/optimization_router.py`
- `app/api/routers/__init__.py`
- `app/main.py`
- `alembic/versions/2026_05_20_0011_m5_parameter_optimization.py`
- `tests/test_optimization_service.py`
- `tests/test_optimization_router.py`
- `tests/test_optimization_schema_contract.py`
- `docs/milestones/m5/artifacts/W1-backend-v1-alignment.md`
- `docs/milestones/m5/artifacts/W1-backend-v1-contract.md`
- `docs/milestones/m5/artifacts/W1-backend-v1-review.md`

## Dependencies

- Reuse `BacktestService.run_backtest()` as the trial objective.
- Reuse the current FastAPI dependency pattern and asyncio task style.
- The current Alembic head is `m3_notification_legacy_type_nullable`.

## Non-Goals

- No Celery/RQ or new queue system.
- No frontend implementation in this slice.
- No Bayesian optimization runtime.
- No direct runtime wiring to `app/optimization/algorithms.py`.
- No changes to `backtest_results` or existing backtest API semantics.

## Acceptance

- New job and trial ORM models match the migration contract.
- Job creation validates parameter space and trial bounds before persistence.
- Random search is deterministic when `random_seed` is supplied.
- A completed job stores `completed_trials`, `best_parameters`, `best_score`, and per-trial metrics.
- A failed trial is recorded without failing the whole job unless no trial succeeds or a task-level error occurs.
- Owner isolation is enforced by service/API lookups.
- Cancelling a pending/running job writes a clear cancelled state.
- Focused backend tests pass.

## Rollback Boundary

- Remove the optimization router registration to disable the API entry point.
- The new optimization tables are independent and can be dropped by the migration downgrade.
- Existing backtest tables and runtime behavior remain unchanged.

## Evidence Plan

- `./.venv/bin/python -m pytest tests/test_optimization_service.py tests/test_optimization_router.py tests/test_optimization_schema_contract.py -q`
- `./.venv/bin/python -m pytest tests/test_backtest_service.py tests/test_router_endpoints.py -q`
- `./.venv/bin/ruff check app tests --select E9,F63,F7,F82`
- `./.venv/bin/alembic -c alembic.ini heads`

## Owner / Review

- Owner: controller backend implementation.
- Reviewers: planner/explorer findings before implementation, reviewer gate after focused tests.
