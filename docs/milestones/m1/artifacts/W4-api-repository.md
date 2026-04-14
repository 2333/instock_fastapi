# W4 API / Repository Integration

> Status: completed
> Scope: repository/service/router exposure for required M1 fact tables
> Owner: Agent C

## Files Changed

- `app/repositories/fact_repository.py`
- `app/services/fact_service.py`
- `app/api/routers/fact_router.py`
- `app/schemas/fact_schema.py`
- `app/api/routers/__init__.py`
- `app/main.py`
- `tests/conftest.py`
- `tests/test_fact_queries.py`
- `docs/milestones/m1/artifacts/W4-api-repository.md`

## Exposed Endpoints

- `GET /api/v1/facts/daily-basic`
- `GET /api/v1/facts/stock-st`
- `GET /api/v1/facts/technical-factors`

Each endpoint supports:

- `code` for `ts_code`-style or symbol-style lookup
- `date` for exact-day lookup
- `start_date` / `end_date` for range reads
- `limit` for bounded result sets

## Repository / Service Paths

- `FactRepository.get_daily_basic(...)`
- `FactRepository.get_stock_st(...)`
- `FactRepository.get_technical_factors(...)`
- `FactService.get_daily_basic(...)`
- `FactService.get_stock_st(...)`
- `FactService.get_technical_factors(...)`

The repository layer:

- normalizes `code` using existing stock-code variants
- normalizes `date` / `start_date` / `end_date` via the existing date helper pattern
- falls back from `trade_date_dt` to `trade_date` when needed
- orders rows by latest trade date with deterministic null handling
- serializes the ORM rows directly for API consumption

## Mapping Decisions

- `daily_basic` is exposed as a direct read model with valuation and liquidity fields.
- `stock_st` is exposed as a direct read model with optional text markers for `st_type`, `reason`, `begin_date`, and `end_date`.
- `technical_factors` exposes the JSONB `factors` payload as stored, rather than flattening the wide upstream factor set.
- No screening filter wiring was added in this wave.

## Screening Integration Status

- Deferred.
- W4 only exposes read access for the new fact tables.
- Selection/screening logic remains on the existing `daily_bars`, `indicators`, and `patterns` stack until W5 verifies quality and backfill coverage.

## Validation

```bash
.venv/bin/pytest tests/test_fact_queries.py tests/test_api.py tests/test_router_endpoints.py -q
```

Result:

```text
21 passed, 1 warning
```

```bash
.venv/bin/pytest -q
.venv/bin/alembic -c alembic.ini history
git diff --check
```

Result:

```text
148 passed, 1 warning
m1_core_fact_timescale -> m1_required_fact_tables (head), m1 required fact tables
<base> -> m1_core_fact_timescale, m1 core fact timescale
```

## Open Risks

- Live PostgreSQL/Timescale smoke testing is still deferred to W5.
- Live Tushare permission and endpoint schema drift are still mocked in tests.
- If any of the new fact tables are later converted to hypertables, the same unique-key/time-column constraint used in W2 must be preserved.
