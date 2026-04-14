# W2 Service Compatibility

> Status: partial implementation completed after interrupted Agent C run
> Scope: existing read-path compatibility for M1 core fact tables
> Owner: Agent C handoff completed locally

## Files Changed

- `app/repositories/daily_bar_repository.py`
- `app/services/backtest_service.py`
- `app/services/date_utils.py`
- `app/services/market_data_service.py`
- `app/services/pattern_service.py`
- `app/services/selection_service.py`
- `app/services/stock_service.py`

## Compatibility Decisions

- Runtime service queries now prefer canonical `trade_date_dt` for M1 core fact tables where practical.
- Existing `trade_date` response fields remain unchanged for public API compatibility.
- Because current tests and some pre-migration data still contain `trade_date_dt = NULL`, service reads use a transition fallback:
  - date equality: `trade_date_dt = :date_dt OR (trade_date_dt IS NULL AND trade_date = :date)`
  - date ranges: `trade_date_dt BETWEEN :start_dt AND :end_dt OR (trade_date_dt IS NULL AND trade_date BETWEEN :start_date AND :end_date)`
  - latest/range ordering: prefer non-null `trade_date_dt`, then fall back to `trade_date`
  - nullable core-table joins: match on `trade_date_dt`, or fall back to `trade_date` when both sides are pre-migration null
- Runtime raw SQL no longer uses PostgreSQL-only `TO_DATE(...)`; date values are normalized in application code via `app.services.date_utils.trade_date_dt_param(...)` so SQLite tests and PostgreSQL runtime can share the same query shape.

## Query Paths Updated

- `DailyBarRepository` range, latest, exact-date, top gainers, and top losers queries now use `DailyBar.trade_date_dt`.
- `SelectionService` SQL screening, pattern hit lookup, latest date resolution, and indicator joins now use `trade_date_dt` with compatibility fallback.
- `StockService` stock list/detail, latest bar, indicator snapshot, recent patterns, DB bar range, and ETF list reads now use `trade_date_dt` with compatibility fallback.
- `MarketDataService` daily bars and fund flows now use `trade_date_dt` where both sides are core fact tables; non-core reference tables remain on `trade_date`.
- `PatternService` pattern date filters and supporting daily-bar lookups now use `trade_date_dt` with compatibility fallback.
- `BacktestService` daily-bar range reads now use `trade_date_dt` with compatibility fallback.
- Reviewer follow-up resolved deterministic fallback ordering in range queries and nullable joins in `MarketDataService` and `SelectionService`.

## Explicit Deferrals

- Joins involving non-M1 reference tables such as `stock_tops`, `stock_block_trades`, and `north_bound_funds` keep their reference table filters on `trade_date`.
- `strategy_results` remains outside the M1 hypertable scope, so strategy-history reads are not migrated in this wave.
- This artifact does not validate live PostgreSQL query plans; W5 must still record Timescale health checks and representative `EXPLAIN` output.

## Validation

```bash
.venv/bin/pytest tests/test_service_queries.py tests/test_stock_service.py tests/test_selection_market_services.py tests/test_selection_today_summary.py tests/test_backtest_service.py -q
.venv/bin/pytest tests/test_m1_core_migrations.py tests/test_service_queries.py tests/test_stock_service.py tests/test_selection_market_services.py tests/test_selection_today_summary.py tests/test_backtest_service.py tests/test_pattern_service.py -q
```

Result:

```text
40 passed, 1 warning
48 passed, 1 warning
```

```bash
rg "TO_DATE|strftime" -n app/services app/repositories
git diff --check
```

Result:

```text
No runtime service/repository TO_DATE or strftime usage remains.
git diff --check passed.
```

## Open Risks

- Some compatibility fallbacks should be removed after the M1 migration/backfill and data quality gates prove `trade_date_dt` is populated.
- The service layer still needs full-suite regression after this artifact and the W2 provider/migration changes are combined.
- Live PostgreSQL/Timescale validation is still required in W5.
