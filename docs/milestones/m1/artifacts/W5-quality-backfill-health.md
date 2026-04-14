# W5 Quality, Backfill, And Timescale Health

> Owner: Agent F
> Status: token-independent acceptance path complete; token-dependent follow-up still gated
> Scope: M1 quality runner, Timescale health checks, and controlled backfill rehearsal plan

## Sub-Artifacts

- `docs/milestones/m1/artifacts/W5a-quality-runner.md`
- `docs/milestones/m1/artifacts/W5b-timescale-health.md`
- `docs/milestones/m1/artifacts/W5c-backfill-rehearsal.md`

## Files Added

- `app/jobs/m1_quality_runner.py`
- `scripts/run_m1_quality_checks.py`
- `scripts/timescale_health_check.py`
- `scripts/m1_backfill_rehearsal.py`
- `scripts/run_m1_daily_bars_rehearsal.py`
- `scripts/run_m1_daily_basic_backfill.py`
- `scripts/run_m1_technical_factors_backfill.py`
- `app/jobs/tasks/fetch_daily_basic_task.py`
- `app/jobs/tasks/calculate_technical_factors_task.py`
- `tests/test_m1_quality_runner.py`
- `tests/test_timescale_health_check.py`
- `tests/test_backfill_rehearsal.py`
- `tests/test_daily_basic_task.py`

## Acceptance Coverage

- Quality runner covers `daily_bars`, `fund_flows`, `indicators`, `patterns`, `daily_basic`, `stock_st`, and `technical_factors`.
- Quality checks include row counts by date, date range, null `trade_date_dt`, duplicate natural keys, and `daily_bars` / `daily_basic` overlap.
- Timescale health runner covers extension availability, core hypertable registration, chunks, compression enabled, compression policy, and representative `EXPLAIN` checks.
- Backfill rehearsal planner covers `daily_bars`, local `technical_factors`, and the deferred `daily_basic` token-dependent path with explicit execution limits.
- `daily_bars` uses the job-layer `run_daily_bars_backfill_window(...)` bounded one-pass function.
- `daily_bars` bounded rehearsal now requires explicit source policy selection. Default bounded policy is `prefer_tushare`, which tries `tushare -> baostock -> eastmoney` and records the actual source used.
- `daily_basic` uses the job-layer `run_daily_basic_backfill_window(...)` writer/backfill function.
- `technical_factors` can be computed locally from `daily_bars` using `run_technical_factors_backfill_window(...)`, with source recorded as `daily_bars_local`.
- Rehearsal wrapper scripts default to dry-run and require `--execute` before writing.
- Dry-run wrappers are read-only but still connect to the configured database; run them only after the environment points at a disposable database.

## Commands Run

```bash
.venv/bin/pytest tests/test_m1_quality_runner.py -q
.venv/bin/pytest tests/test_timescale_health_check.py -q
.venv/bin/pytest tests/test_backfill_rehearsal.py -q
.venv/bin/pytest tests/test_fetch_tasks.py::test_daily_bars_backfill_window_dry_run_is_bounded tests/test_daily_basic_task.py tests/test_backfill_rehearsal.py -q
.venv/bin/pytest tests/test_fetch_tasks.py::test_daily_bars_backfill_window_dry_run_is_bounded tests/test_fetch_tasks.py::test_daily_bars_backfill_window_uses_explicit_baostock_source tests/test_calculate_technical_factors_task.py -q
.venv/bin/pytest -q
.venv/bin/alembic -c alembic.ini history
python3 - <<'PY'
import psycopg2
conn = psycopg2.connect(host='127.0.0.1', port=55432, user='instock_m1', password='instock_m1_pass', dbname='instock_m1', connect_timeout=5)
cur = conn.cursor()
cur.execute('select current_database(), current_user, version()')
print(cur.fetchone())
conn.close()
PY
DB_HOST=127.0.0.1 DB_PORT=55432 DB_USER=instock_m1 DB_PASSWORD=instock_m1_pass DB_NAME=instock_m1 .venv/bin/alembic -c alembic.ini upgrade head
git diff --check
```

## Current Results

- Focused W5 unit tests passed in the worker runs.
- Full backend regression passed in the latest main-thread run: `162 passed, 1 warning`.
- `git diff --check` passed in the worker run.
- W5 script `py_compile` passed in the main-thread run.
- Focused explicit-source/local-factor tests passed: `5 passed, 1 warning`.
- Disposable database connectivity was verified on `127.0.0.1:55432`.
- Live `alembic upgrade head` against the empty disposable database failed in `m1_core_fact_timescale` because relation `daily_bars` does not exist.
- Because the first revision requires pre-existing core tables, Timescale health checks and live rehearsal commands remain blocked until an approved starting-schema strategy is applied to the disposable database.
- After preparing a minimal existing-schema start, `alembic upgrade head` completed successfully and the disposable database reached `m1_required_fact_tables`.
- `daily_bars` bounded rehearsal executed successfully with default explicit policy `prefer_tushare`; Tushare was unavailable, BaoStock was selected as the recorded actual source, and `4` rows were written for `000001.SZ`.
- `technical_factors` local bounded rehearsal executed and wrote `4` rows for `000001.SZ` with `source=daily_bars_local`.
- Quality runner result after those writes: `0 fail`, `11 warn`, `18 ok`.
- `daily_bars` quality checks are now `ok` for row counts, date range, null `trade_date_dt`, and duplicate keys.
- `technical_factors` quality checks are now `ok` for row counts, date range, null `trade_date_dt`, and duplicate keys.
- Timescale health result after those writes shows:
  - `daily_bars` hypertable chunk count: `2`
  - `daily_bars` representative `EXPLAIN` includes `ChunkAppend`
  - `fund_flows`, `indicators`, and `patterns` still report `chunk_count=0` because no sample rows were loaded

## Current-Stage Acceptance Result

Current-stage W5 acceptance is satisfied on a disposable PostgreSQL/Timescale database whose starting schema matches the accepted existing-schema path:

```bash
.venv/bin/alembic -c alembic.ini upgrade head
.venv/bin/python scripts/run_m1_quality_checks.py --json
.venv/bin/python scripts/timescale_health_check.py --json
.venv/bin/python scripts/m1_backfill_rehearsal.py --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source prefer_tushare --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
```

Recorded live outputs after the starting schema was prepared:

- Alembic upgrade result for `m1_core_fact_timescale` and `m1_required_fact_tables`.
- Quality runner status counts and any failed checks.
- Timescale hypertable registration, chunk counts, compression policy state, and representative `EXPLAIN` output.
- Dry-run and `--execute` output for the bounded `daily_bars` rehearsal on a disposable DB, including the declared source policy and the selected actual source.
- Dry-run and `--execute` output for the local `technical_factors` rehearsal after `daily_bars` is present.

## Token-Dependent Follow-Up

The following work is explicitly outside current-stage acceptance and remains gated:

```bash
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source tushare --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
.venv/bin/python scripts/run_m1_daily_basic_backfill.py --start-date 20240102 --end-date 20240105 --day-limit 1
```

These follow-up commands should run only after:

- a valid Tushare token is available, or
- a separately approved source contract exists for reduced-semantics replacements

## Residual Risks

- Live Tushare validation now shows authentication failure for the current token, so any Tushare-backed `--execute` rehearsal is blocked until a valid token is configured.
- `daily_bars` remains explicit-policy only. `prefer_tushare` is acceptable because the policy is declared up front and the actual source used is recorded.
- `technical_factors` can proceed from local `daily_bars`, but only for windows with sufficient bar history.
- Live empty-database `alembic upgrade head` was attempted and failed as expected for an existing-schema migration path; the accepted route is the prepared existing-schema start.
- Backfill rehearsals should not be executed against the existing production database.
- Backfill dry-runs should also use a disposable DB connection to avoid reading production by mistake.
- Do not use `scripts/backfill_2020_2025.py` as a bounded rehearsal command.
- `fund_flows`, `indicators`, and `patterns` still have no sample rows in the disposable database, so their Timescale chunk checks remain red even though hypertable registration and compression policy are present.
- `daily_basic` and `stock_st` remain empty on the disposable database because they are now explicit gated follow-up work.
