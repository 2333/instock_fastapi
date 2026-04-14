# W5a Quality Runner

> Owner: Worker F-W5a
> Status: implementation complete, live DB rehearsal still required
> Scope: M1 data quality runner and summary

## Files Changed

- `app/jobs/m1_quality_runner.py`
- `scripts/run_m1_quality_checks.py`
- `tests/test_m1_quality_runner.py`
- `docs/milestones/m1/artifacts/W5a-quality-runner.md`

## Checks Implemented

- Row counts by date for:
  - `daily_bars`
  - `fund_flows`
  - `indicators`
  - `patterns`
  - `daily_basic`
  - `stock_st`
  - `technical_factors`
- Date-range min/max snapshot for each table
- Null `trade_date_dt` counts
- Duplicate natural-key group detection
- Cross-source overlap sanity between `daily_bars` and `daily_basic`

## Runner Behavior

- Returns a structured list of dictionaries with:
  - `check`
  - `table`
  - `status`
  - `value`
  - `details`
- `summarize_quality_results(...)` rolls the raw checks into status counts and failed-check summaries.
- `has_quality_failures(...)` returns `True` when any check is `fail`.
- The CLI script prints either a human-readable summary or JSON when `--json` is supplied.

## Validation

```bash
.venv/bin/pytest tests/test_m1_quality_runner.py -q
git diff --check -- app/jobs/m1_quality_runner.py scripts/run_m1_quality_checks.py tests/test_m1_quality_runner.py docs/milestones/m1/artifacts/W5a-quality-runner.md
.venv/bin/pytest -q
```

Result:

- `2 passed, 1 warning`
- diff check passed
- full regression: `154 passed, 1 warning`

## Live Gate

Required before W5 acceptance:

```bash
.venv/bin/python scripts/run_m1_quality_checks.py --json
```

Run this against the target disposable PostgreSQL/Timescale database after W2/W3/W4 are deployed and record:

- row-count snapshots
- date ranges
- null counts
- duplicate-key groups
- cross-source overlap result
- total row counts per table

## Residual Risks

- The quality runner is SQL-driven but this artifact has not yet recorded a live database rehearsal against the target disposable PostgreSQL/Timescale database.
- Duplicate-key detection currently reports grouped duplicates only; it does not mutate or repair data.
