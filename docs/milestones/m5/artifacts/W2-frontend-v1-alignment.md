# W2 Frontend V1 Alignment And Review

Date: 2026-05-21

## Scope

Connect the frozen `M5 v1` optimization API contract to the existing Backtest workflow:

```text
Backtest config
  -> select bounded strategy parameters
  -> create optimization job
  -> poll job / trial / best state
  -> cancel running job
  -> apply best parameters back into Backtest config
```

This slice exists to close the `M5 v1` user-facing loop without restoring the removed standalone optimization page.

## Write Set

- `web/src/api/index.ts`
- `web/src/views/Backtest.vue`
- `tests/test_optimization_smoke.py`
- `docs/milestones/phase3/PHASE3_P3-05_PARAM_OPTIMIZATION_FRONTEND.md`
- `docs/milestones/m5/M5_P3-05_RESIDUE_DECISIONS.md`
- `docs/milestones/m5/M5_P3-05_REVIEW_CHECKLIST.md`
- `docs/milestones/m5/README.md`
- `docs/milestones/m5/artifacts/W2-frontend-v1-alignment.md`

## Dependencies

- W1 backend schema/service/API/task runtime is frozen.
- `web/src/api/index.ts` remains the frontend API facade.
- `web/src/views/Backtest.vue` remains the existing strategy/backtest work surface.
- No standalone `Optimization.vue` route is present.

## Non-Goals

- No standalone optimization page.
- No new frontend store, router branch, dashboard, or background-job framework.
- No Bayesian optimization UI.
- No live staging or production release execution in this local code gate.

## Acceptance

- Backtest page can create an optimization job from the current strategy config.
- User can select bounded numeric parameters and an objective metric.
- UI shows job progress, completed/failed counters, recent trials, and best score.
- UI can cancel pending/running jobs through the frozen API contract.
- UI can apply best parameters back to `strategyParams`.
- API smoke covers create -> run -> job/trials/best -> best backtest replay.
- Frontend `typecheck` and production `build` pass.
- Backend focused tests and full pytest pass.
- Alembic `current` equals `head` locally.

## Rollback Boundary

- Remove `optimizationApi` from `web/src/api/index.ts` and the `optimization-section` block/state from `Backtest.vue`.
- Backend W1 tables and API can remain independently deployable.
- Existing Backtest run/history/result behavior is unchanged.

## Evidence

Passed:

```text
./.venv/bin/python -m pytest tests/test_optimization_smoke.py tests/test_optimization_service.py tests/test_optimization_router.py tests/test_optimization_schema_contract.py -q
17 passed, 1 warning
```

```text
./.venv/bin/python -m pytest -q
311 passed, 1 skipped, 2 warnings
```

```text
./.venv/bin/ruff check app tests --select E9,F63,F7,F82
All checks passed
```

```text
npm run typecheck
passed
```

```text
npm run build
passed
```

```text
./.venv/bin/alembic -c alembic.ini current
m5_parameter_optimization (head)
```

## Review Result

Status: approved after NO-GO correction.

Cross-review corrections:

- A terminalization race could overwrite a last-moment cancellation; `run_job()` now preserves `cancelled` after the final refresh, with a regression test.
- W2 frontend scope is recorded separately from W1 backend scope.
- Local Alembic runtime has been upgraded so `current` matches `head`.

Residual release activity:

- live staging smoke covering real job creation, progress, trial results, best parameters, and cancellation.
- production backup, schema-contract gate, and release smoke plan.
