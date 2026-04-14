# W6 Integration Review

> Owner: Reviewer
> Status: go for current-stage M1 acceptance; token-dependent follow-up remains gated
> Scope: W0-W5 integration review for the `m1/data-layer-restart` branch

## Review Result

The current-stage M1 restart work is ready for acceptance on the narrowed token-independent scope. Token-independent live validation is in place on a disposable database, the source policy is explicit, and the remaining Tushare-dependent items are now clearly documented as gated follow-up rather than hidden blockers.

## Findings Addressed

- W5 backfill rehearsal previously emitted `scripts/backfill_2020_2025.py` as if it were bounded by `BACKFILL_BATCH_SIZE`; this was corrected.
- `daily_bars` now has a job-layer bounded one-pass function and thin wrapper script.
- `daily_basic` now has a job-layer writer/backfill task and thin wrapper script.
- Alembic wording previously overstated the current state as a full canonical schema path. The accepted current-stage strategy is now the existing-schema `stamp/document` path recorded in `docs/milestones/m1/artifacts/W1-alembic-baseline.md`.

## Current Alembic Boundary

- `alembic/` is initialized and wired to `app.models.stock_model.Base`.
- Current revision chain:
  - `<base> -> m1_core_fact_timescale`
  - `m1_core_fact_timescale -> m1_required_fact_tables`
- `m1_core_fact_timescale` assumes the pre-M1 tables already exist; it is not an empty-database baseline.
- This boundary was confirmed on 2026-04-09 by running `alembic upgrade head` against a disposable TimescaleDB on `127.0.0.1:55432`; the upgrade failed immediately with `relation "daily_bars" does not exist`.
- The accepted current-stage baseline strategy is the existing-schema `stamp/document` path recorded in `docs/milestones/m1/artifacts/W1-alembic-baseline.md`.
- A true empty-database baseline revision remains optional follow-up work; it is not required for current-stage M1 merge readiness.

## Residual External Gates

- Live PostgreSQL/Timescale validation has now run:
  - empty-database `alembic upgrade head` failed and confirmed the current chain does not support empty-database bootstrapping
  - after preparing an existing-schema start, `alembic upgrade head` succeeded to `m1_required_fact_tables`
  - `daily_bars` bounded rehearsal ran successfully with explicit `prefer_tushare` policy and recorded `baostock` as the actual source used after Tushare was unavailable
  - `technical_factors` bounded local rehearsal ran successfully with `source=daily_bars_local`
  - Timescale health now shows `daily_bars` chunk count `2` and `ChunkAppend` in the representative `EXPLAIN`
- Disposable infrastructure is available; the existing production database must still not be used for this gate.
- Live Tushare validation was executed and failed with upstream authentication error `您的token不对，请确认。`; point tier and endpoint permissions therefore remain unverified.
- `daily_basic` and `stock_st` live backfill rehearsals still remain blocked by Tushare token state.
- W3 new fact tables are regular PostgreSQL tables for now; if promoted to hypertables later, their unique constraints must include the time partition column.
- W4 intentionally defers screening integration for new fact tables.

## Local Validation

```bash
.venv/bin/pytest -q
git diff --check
python3 -m py_compile scripts/run_m1_quality_checks.py scripts/timescale_health_check.py scripts/m1_backfill_rehearsal.py
python3 -m py_compile app/jobs/tasks/fetch_daily_basic_task.py scripts/run_m1_daily_bars_rehearsal.py scripts/run_m1_daily_basic_backfill.py
.venv/bin/alembic -c alembic.ini history
```

Current local result:

- `162 passed, 1 warning`
- `git diff --check` passed
- W5 script `py_compile` passed
- Alembic history passed and shows `m1_required_fact_tables` as head

Verified live result:

- Disposable DB connection to `127.0.0.1:55432` succeeded.
- Empty-database `alembic upgrade head` failed in `m1_core_fact_timescale` because `daily_bars` does not exist.
- Live Tushare checks for `daily_basic`, `stock_st`, `technical_factors`, and `pro_bar` all returned zero rows after upstream token rejection.
- Existing-schema-start `alembic upgrade head` succeeded to `m1_required_fact_tables`.
- `daily_bars` live rehearsal with explicit `prefer_tushare` policy wrote `4` rows for `000001.SZ`, with `baostock` recorded as the actual source after the Tushare attempt returned no data.
- `technical_factors` local live rehearsal wrote `4` rows for `000001.SZ`.
- Quality runner on the disposable DB returned `0 fail`, `11 warn`, `18 ok`.
- Timescale health on the disposable DB shows `daily_bars` chunk count `2` and `ChunkAppend` in the representative `EXPLAIN` plan.

## Go/No-Go

- Current-stage M1 acceptance: go.
- Token-dependent follow-up: `daily_basic` / `stock_st` live gates remain pending until a valid Tushare token exists or a separately approved source contract is added.
