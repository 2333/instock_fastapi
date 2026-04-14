# W3 Required Fact Migrations

> Agent: A
> Status: implementation draft
> Scope: `daily_basic`, `stock_st`, `technical_factors`

## Files Changed

- `app/models/stock_model.py`
- `alembic/versions/2026_04_08_0002-m1_required_fact_tables.py`
- `tests/test_m1_required_fact_models.py`
- `docs/milestones/m1/artifacts/W3-required-fact-migrations.md`

## Model Decisions

- Added `DailyBasic`, `StockST`, and `TechnicalFactor` models as regular fact tables.
- Each table uses canonical `trade_date_dt` for uniqueness and keeps string `trade_date` indexed for compatibility and readability.
- `daily_basic` stores the M1 valuation/liquidity subset directly as nullable numeric columns.
- `stock_st` stores flexible text fields for name/type/reason and begin/end markers until the live Tushare response is verified.
- `technical_factors` stores a JSONB `factors` bag rather than creating 210+ columns before the response shape and query requirements are confirmed.

## Migration Decisions

- Added revision `m1_required_fact_tables` with `down_revision = "m1_core_fact_timescale"`.
- The revision creates:
  - `daily_basic`
  - `stock_st`
  - `technical_factors`
- The new tables are not converted to Timescale hypertables in W3. W5 remains responsible for live Timescale health checks and any post-design hypertable policy for new facts.
- Downgrade drops the three new tables and their explicit indexes in reverse dependency order.

## Commands Run

```bash
sed -n '80,260p' app/models/stock_model.py
find alembic/versions -maxdepth 1 -type f -print | sort
sed -n '1,260p' alembic/versions/2026_04_08_0001-m1_core_fact_timescale.py
sed -n '1,160p' tests/test_m1_core_migrations.py
```

## Validation

- Focused validation run:

```bash
.venv/bin/pytest tests/test_m1_required_fact_models.py -q
.venv/bin/alembic -c alembic.ini history
git diff --check -- app/models/stock_model.py alembic/versions/2026_04_08_0002-m1_required_fact_tables.py tests/test_m1_required_fact_models.py docs/milestones/m1/artifacts/W3-required-fact-migrations.md
.venv/bin/python -m py_compile alembic/versions/2026_04_08_0002-m1_required_fact_tables.py
```

Result:

```text
tests/test_m1_required_fact_models.py: 4 passed, 1 warning
alembic history: m1_core_fact_timescale -> m1_required_fact_tables (head)
git diff --check: passed
py_compile: passed
```

## Open Risks

- Live Tushare token/point tier is not verified in this artifact.
- Live response columns for `stock_st` and `stk_factor_pro` still need Worker D provider mapping confirmation.
- Disposable PostgreSQL/Timescale `alembic upgrade head` and downgrade checks remain W5 acceptance gates.
