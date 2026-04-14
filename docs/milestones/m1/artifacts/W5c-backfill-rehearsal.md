# W5c Backfill Rehearsal

> Owner: Worker F-W5c
> Status: completed for current-stage acceptance; token-dependent follow-up retained as gated planning
> Scope: controlled backfill rehearsal planning for `daily_bars`, local `technical_factors`, and deferred `daily_basic`

## Files Changed

- `app/jobs/tasks/fetch_daily_task.py`
- `app/jobs/tasks/fetch_daily_basic_task.py`
- `app/jobs/tasks/calculate_technical_factors_task.py`
- `scripts/m1_backfill_rehearsal.py`
- `scripts/run_m1_daily_bars_rehearsal.py`
- `scripts/run_m1_daily_basic_backfill.py`
- `scripts/run_m1_technical_factors_backfill.py`
- `tests/test_backfill_rehearsal.py`
- `tests/test_daily_basic_task.py`
- `tests/test_fetch_tasks.py`
- `docs/milestones/m1/artifacts/W5c-backfill-rehearsal.md`

## Rehearsal Policy

- Default mode is dry-run planning only.
- `daily_bars` has a job-layer bounded one-pass rehearsal function: `run_daily_bars_backfill_window(...)`.
- `daily_bars` requires an explicit source policy. Default bounded behavior is `prefer_tushare`, which prefers Tushare but is not blocked by it; the final source used is recorded in the result and audit output.
- The existing `scripts/backfill_2020_2025.py` entrypoint must not be used as a bounded rehearsal command because it loops until `run_historical_backfill()` returns done; `BACKFILL_BATCH_SIZE` is only a per-batch size.
- `daily_basic` has a job-layer writer/backfill task: `app/jobs/tasks/fetch_daily_basic_task.py`, but it remains outside current-stage acceptance until token or source-contract gates are cleared.
- `technical_factors` has a local writer/backfill task: `app/jobs/tasks/calculate_technical_factors_task.py`, with source recorded as `daily_bars_local`.
- Thin scripts call job-layer functions; they do not own backfill business logic.
- No live Tushare calls are made in tests.
- The wrapper dry-run paths are read-only, but they still connect to the configured database; point the environment at a disposable database before running them.

## Planned Commands

### `daily_bars`

```bash
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source prefer_tushare --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source baostock --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source eastmoney --start-date 20240102 --end-date 20240105 --code-limit 5
```

Add `--execute` only after the dry-run target list is inspected and the target DB is disposable.

### `daily_basic` Follow-Up

```bash
.venv/bin/python scripts/run_m1_daily_basic_backfill.py --start-date 20240102 --end-date 20240105 --day-limit 1
```

Add `--execute` only after the dry-run target dates are inspected, the target DB is disposable, and the token/source-contract gate is cleared.

### `technical_factors`

```bash
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5
```

Add `--execute` only after `daily_bars` exists for the requested window and the target DB is disposable or approved.

### `daily_basic` read-path smoke follow-up

Run only after the token/source-contract gate is cleared and sample `daily_basic` rows are present:

```bash
curl -s "http://localhost:8000/api/v1/facts/daily-basic?code=000001&date=2024-01-02&limit=5"
```

## Verification Queries

- `daily_bars`: row count, min/max `trade_date_dt`, duplicate natural keys, null `trade_date_dt` count
- `daily_basic`: row count, min/max `trade_date_dt`, duplicate natural keys, null `trade_date_dt` count
- `technical_factors`: row count, min/max `trade_date_dt`, duplicate natural keys, null `trade_date_dt` count, and `source=daily_bars_local` audit records
- Shared checks:
  - `backfill_daily_state` status counts
  - `daily_bars` null `trade_date_dt` count for the rehearsal window
  - `daily_basic` null `trade_date_dt` count for the rehearsal window

## Validation

```bash
.venv/bin/pytest tests/test_backfill_rehearsal.py -q
.venv/bin/pytest tests/test_fetch_tasks.py::test_daily_bars_backfill_window_dry_run_is_bounded tests/test_daily_basic_task.py tests/test_backfill_rehearsal.py -q
python3 -m py_compile app/jobs/tasks/fetch_daily_basic_task.py scripts/m1_backfill_rehearsal.py scripts/run_m1_daily_bars_rehearsal.py scripts/run_m1_daily_basic_backfill.py
python3 -m py_compile app/jobs/tasks/calculate_technical_factors_task.py scripts/run_m1_technical_factors_backfill.py
.venv/bin/pytest tests/test_fetch_tasks.py::test_daily_bars_backfill_window_dry_run_is_bounded tests/test_fetch_tasks.py::test_daily_bars_backfill_window_uses_explicit_baostock_source tests/test_calculate_technical_factors_task.py -q
git diff --check
```

Result:

```text
2 passed, 1 warning
5 passed, 1 warning
py_compile passed
5 passed, 1 warning
```

## Observed Live Results On Disposable DB

Disposable target:

- PostgreSQL/TimescaleDB on `127.0.0.1:55432`
- existing-schema starting point prepared before Alembic upgrade

`daily_bars` bounded rehearsal with explicit single-source execution:

```bash
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source eastmoney --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source eastmoney --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
```

Observed result:

- dry-run target count: `1`
- target codes: `000001.SZ`
- execute source: `eastmoney`
- saved rows: `4`
- per-symbol result: `000001.SZ -> done, saved_rows=4`

`daily_bars` bounded rehearsal with the default explicit source policy:

```bash
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source prefer_tushare --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source prefer_tushare --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
```

Observed result:

- dry-run target count: `1`
- target codes: `000001.SZ`
- declared policy: `prefer_tushare`
- recorded attempts: `tushare -> baostock`
- actual source used: `baostock`
- saved rows: `4`
- per-symbol result: `000001.SZ -> done, saved_rows=4`

`technical_factors` bounded rehearsal:

```bash
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5 --execute
```

Observed result:

- dry-run target count: `1`
- target codes: `000001.SZ`
- execute source: `daily_bars_local`
- input rows: `4`
- factor rows: `4`
- saved rows: `4`

## Residual Risks

- The plan does not execute live Tushare backfills by default.
- Tushare-backed execution still requires a disposable DB and a valid Tushare token.
- `prefer_tushare` is now the preferred bounded source policy, but it is still explicit and audit-visible; single-source execution remains available when needed.
- `daily_basic` remains documented as follow-up planning, not current-stage acceptance evidence.
- Dry-run wrapper execution should also use a disposable DB connection because target discovery reads the configured database.
- W5 live Timescale and DB validation remains a separate acceptance gate.
