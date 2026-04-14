# W2 Core Migrations

> Agent: A
> Status: implementation draft
> Scope: `daily_bars`, `fund_flows`, `indicators`, `patterns`

## Files Changed

- `app/models/stock_model.py`
- `alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py`
- `tests/test_m1_core_migrations.py`
- `docs/milestones/m1/artifacts/W2-core-migrations.md`

## Model Decisions

- `trade_date_dt` is now the model-level unique/index date for the M1 core fact tables.
- `trade_date` remains present and indexed for API/readability compatibility while service code is migrated.
- `daily_bars` uniqueness changed to `ts_code + trade_date_dt`.
- `fund_flows` uniqueness changed to `ts_code + trade_date_dt`.
- `indicators` uniqueness changed to `ts_code + trade_date_dt + indicator_name`.
- `patterns` already used `trade_date_dt` for uniqueness; the model now also has `ix_patterns_trade_date_dt`.
- `DailyBar.trade_date_dt`, `FundFlow.trade_date_dt`, and `Indicator.trade_date_dt` remain nullable in the ORM during this transition because existing fixtures and data may still contain nulls before the migration backfill and data quality gates run.

## Migration Decisions

- Added a hand-written Alembic revision because Timescale operations are not autogenerate-safe.
- The migration:
  - creates the Timescale extension if missing
  - backfills `trade_date_dt` from valid `YYYYMMDD` `trade_date` values
  - fails fast if any target table still contains null `trade_date_dt`
  - replaces each target table's single-column `id` primary key with a Timescale-compatible `(id, trade_date_dt)` primary key before hypertable conversion
  - replaces old `trade_date` unique constraints on `daily_bars`, `fund_flows`, and `indicators`
  - creates `trade_date_dt` indexes
  - converts `daily_bars`, `fund_flows`, `indicators`, and `patterns` to hypertables with 7-day chunks
  - enables compression and a 30-day compression policy
- Downgrade removes compression policies only. It does not attempt to restore legacy primary/unique constraints because Timescale hypertables cannot accept unique constraints that omit the partition column. A full un-hypertable rollback requires backup restore or an approved copy-table rollback procedure.

## Commands Run

```bash
sed -n '1,260p' docs/milestones/m1/artifacts/W1-schema-conventions.md
sed -n '1,260p' docs/milestones/m1/artifacts/W1-timescale-policy.md
sed -n '80,230p' app/models/stock_model.py
find alembic/versions -maxdepth 1 -type f -print | sort
git status --short --branch
.venv/bin/pytest tests/test_m1_core_migrations.py -q
.venv/bin/python -m py_compile alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py
git diff --check -- app/models/stock_model.py alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py tests/test_m1_core_migrations.py docs/milestones/m1/artifacts/W2-core-migrations.md
```

## Validation

- Added `tests/test_m1_core_migrations.py` for model metadata and migration-policy SQL checks.
- `.venv/bin/pytest tests/test_m1_core_migrations.py -q` passed: 4 passed, 1 warning.
- `.venv/bin/python -m py_compile alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py` passed.
- `git diff --check` passed for the assigned write set.
- Reviewer finding resolved: the migration now drops the conventional single-column `{table}_pkey` and recreates it as `(id, trade_date_dt)` before `create_hypertable(...)`.
- Live Alembic upgrade/downgrade and Timescale health SQL still need to run against a disposable Timescale database in W5.

## Open Risks

- This revision currently has `down_revision = None` because no baseline revision existed at the start of W2. If the team introduces a separate baseline revision, this migration must be re-parented.
- `remove_compression_policy(..., if_exists => TRUE)` depends on TimescaleDB support for the `if_exists` argument; verify on the target extension version during disposable DB validation.
- Some service/repository queries still use `trade_date`; Agent C must complete W2 service compatibility before API behavior can be considered fully migrated.
