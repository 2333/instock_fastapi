# W1 Backend V1 Review

Date: 2026-05-20

## Scope Reviewed

- Backend parameter optimization schema, migration, service, task runner, API router, focused tests, and W1 artifacts.
- Frontend remains out of scope for this W1 backend slice.

## Cross Review Findings

Reviewer gate initially found three issues:

1. `running` job cancellation could leave a cancelled job with a completed in-flight trial and mismatched counters.
2. Task-level exceptions were logged but did not mark the job as `failed`.
3. `objective_metric` was documented as a frozen schema value set but only enforced at the API schema layer.

## Resolution

- Cancellation semantics are now explicit: once a running job is cancelled, the in-flight trial is persisted as `cancelled`, and no best/counter updates are applied after cancellation.
- `run_optimization_job()` now marks non-terminal jobs as `failed` on task-level exceptions.
- `objective_metric` is enforced by ORM check constraint, Alembic migration, and schema contract tests.

## Evidence

Passed:

```text
./.venv/bin/python -m pytest tests/test_optimization_service.py tests/test_optimization_router.py tests/test_optimization_schema_contract.py -q
14 passed, 1 warning
```

```text
./.venv/bin/ruff check app tests --select E9,F63,F7,F82
All checks passed
```

```text
./.venv/bin/alembic -c alembic.ini heads
m5_parameter_optimization (head)
```

```text
./.venv/bin/python -m pytest -q
308 passed, 1 skipped, 2 warnings
```

## Cross-Slice Handoff

Date: 2026-05-21

Frontend implementation is not part of this W1 backend slice. The follow-on Backtest integration, frontend evidence, and smoke replay are tracked in `W2-frontend-v1-alignment.md`.

## Reviewer Gate

Status: approved after short re-review and completion addendum.

Follow-up from short re-review:

- The reviewer confirmed the P1/P2 findings are closed.
- The remaining observation was that not-yet-created trials were not materialized as `cancelled` rows when cancellation happened during an in-flight trial. The implementation now writes those remaining planned trials as `cancelled`, keeping the design note and runtime behavior aligned.

Residual risk:

- Process restart recovery for `running` jobs is explicitly out of scope and documented in the contract freeze.
