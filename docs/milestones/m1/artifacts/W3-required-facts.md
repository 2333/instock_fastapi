# W3 Required Facts Planning

> Agent: D
> Status: planning artifact; token-dependent facts narrowed to gated follow-up for current-stage acceptance
> Scope: `daily_basic`, `stock_st`, `technical_factors`

---

## Inputs Reviewed

- `docs/milestones/m1/M1_RESTART_PLAN.md`
- `docs/milestones/m1/DATA_LAYER_REPORT.md`
- `docs/milestones/m1/M1_PROGRESS_TRACKER.md`
- `core/crawling/tushare_provider.py`

Current code now defines provider methods and focused mocked provider tests for `daily_basic`, `stock_st`, and `technical_factors`. Models, migrations, jobs, and API exposure are handled by separate W3/W4 owners. `TushareProvider` centralizes these Tushare calls through `_call_pro(...)`, rate limiting through `_run_with_limits(...)`, and row conversion through explicit dict mapping helpers.

---

## Permission Assumptions

| Table | Endpoint | Required tier | M1 rule |
|-------|----------|---------------|---------|
| `daily_basic` | `daily_basic` | 2000+ points | Gated follow-up for current-stage acceptance |
| `stock_st` | `stock_st` | 3000+ points | Gated follow-up for current-stage acceptance |
| `technical_factors` | `stk_factor_pro` | 5000+ points | Current-stage acceptance uses local `daily_bars_local`; Tushare-provided variant is gated |

W0 must record current Tushare token validity and point tier before any token-dependent ingestion is accepted. While token validity is missing, `daily_basic` and `stock_st` remain gated follow-up work, and `technical_factors` proceeds only through the separately documented local `daily_bars_local` path.

---

## Endpoint Fields To Verify

Do not treat the field lists below as final DDL. Agent D should verify the current Tushare response columns during implementation, then hand the confirmed mapping to Agent A for model/migration integration.

### `daily_basic`

Purpose: daily valuation and liquidity indicators for basic screening.

Minimum fields to verify:

- identity/date: `ts_code`, `trade_date`
- turnover: `turnover_rate`, `turnover_rate_f`, `volume_ratio`
- valuation: `pe`, `pe_ttm`, `pb`, `ps`, `ps_ttm`, `dv_ratio`, `dv_ttm`
- share/cap: `total_share`, `float_share`, `free_share`, `total_mv`, `circ_mv`

Proposed unique key: `ts_code + trade_date_dt`.

Mapping decision:

- Keep raw `trade_date` for compatibility/readability during M1.
- Add canonical `trade_date_dt` in the model/migration handoff.
- Use nullable numeric columns for Tushare values because not all stocks expose every valuation metric daily.
- Provider implementation calls `daily_basic(trade_date=..., fields=...)` and maps the agreed numeric field subset to optional floats.

### `stock_st`

Purpose: ST snapshot for screening exclusion/filtering.

Minimum fields to verify:

- identity/date: `ts_code`, `trade_date`
- classification/name fields exposed by Tushare for `stock_st`
- any begin/end marker returned by the current endpoint, if present

Proposed unique key: `ts_code + trade_date_dt`.

Mapping decision:

- Store one row per stock per snapshot date.
- Preserve flexible text fields as `name`, `st_type`, `reason`, `begin_date`, and `end_date`, mapping common alternatives such as `stock_name`, `type`, `change_reason`, `entry_date`, and `remove_date`.
- Do not wire screening filtering until W4 API/repository integration confirms the final model shape.

### `technical_factors`

Purpose: Tushare-provided technical factor comparison and future screening inputs.

Minimum fields to verify:

- identity/date: `ts_code`, `trade_date`
- high-value common factors if present: moving averages, MACD/KDJ/RSI-like columns, volume/turnover-derived columns
- full response column count and maximum observed row width

Proposed unique key: `ts_code + trade_date_dt`.

Mapping decision:

- Because `stk_factor_pro` can expose 210+ fields, provider implementation stores all non-identity scalar columns in a `factors` dict rather than committing to a wide provider contract.
- Recommended DDL handoff: use `JSONB` for `technical_factors.factors` during M1, then promote selected factor columns only after W4 query/API needs are confirmed.

---

## Provider Implementation Notes For Handoff

Use existing `TushareProvider` patterns:

- add async wrapper methods that delegate to `asyncio.to_thread(...)`
- add sync implementations that call `_call_pro(endpoint, ...)`
- use `_to_ymd(...)` for date normalization
- use `_pick_str(...)` and `_pick_float(...)` for row mapping
- return `list[dict[str, Any]]` for consistency with existing task code
- log and return empty lists on provider failures, matching current style

Suggested method names:

- `fetch_daily_basic(trade_date: str) -> list[dict[str, Any]]`
- `fetch_stock_st(trade_date: str) -> list[dict[str, Any]]`
- `fetch_technical_factors(trade_date: str) -> list[dict[str, Any]]`

Provider implementation owner has now edited `core/crawling/tushare_provider.py` under the W3 provider-mapping write set. Agent A still owns model/migration files.

Implemented method names:

- `fetch_daily_basic(trade_date: str) -> list[dict[str, Any]]`
- `fetch_stock_st(trade_date: str) -> list[dict[str, Any]]`
- `fetch_technical_factors(trade_date: str) -> list[dict[str, Any]]`

Implementation rules:

- Rows without both `ts_code` and `trade_date` are skipped.
- Empty DataFrames and provider exceptions return `[]`.
- `trade_date_dt` is derived from `trade_date`.
- `technical_factors` packs non-identity scalar values into `factors`.

---

## Proposed Focused Tests

- Provider mapping tests using mocked DataFrames:
  - non-empty response maps identity/date fields and representative numeric values
  - empty DataFrame returns `[]`
  - provider exception logs and returns `[]`
  - invalid/missing `ts_code` rows are skipped
- Model/migration tests after Agent A handoff:
  - unique key conflict behavior for `ts_code + trade_date_dt`
  - nullable numeric fields accepted
  - `trade_date` and `trade_date_dt` stay consistent
- W4 API/repository tests:
  - `daily_basic` query by date/code
  - `stock_st` query supports screening exclusion decision
  - `technical_factors` exposes only the accepted M1 subset or explicitly documents deferral

---

## Handoff To Agent A

Agent A owns `app/models/stock_model.py` and `alembic/versions/`. Before Agent A writes model/migration files, this artifact should be updated with:

- verified Tushare token tier
- sample response columns for all three endpoints
- final DDL decision for `technical_factors` wide-column vs JSONB subset
- final unique/index names
- whether `technical_factors` is required, blocked, or deferred based on current points

## Commands Run

```bash
.venv/bin/pytest tests/test_tushare_required_facts.py tests/test_tushare_pro_bar.py -q
git diff --check -- core/crawling/tushare_provider.py tests/test_tushare_required_facts.py
```

## Validation

- Added `tests/test_tushare_required_facts.py`.
- Focused provider tests passed: `7 passed, 1 warning`.
- `git diff --check` passed for the W3 provider write set.

## Files Changed By Agent D

- `core/crawling/tushare_provider.py`
- `tests/test_tushare_required_facts.py`
- `docs/milestones/m1/artifacts/W3-required-facts.md`

## Residual Risks

- Live Tushare token validity and point tier are still unverified in this offline/mocked test pass.
- `technical_factors` uses JSON-style factor packing for M1; W4 must decide whether any individual factors should be promoted into first-class query columns.
- `daily_basic` and `stock_st` stay out of current-stage M1 acceptance until a valid Tushare token exists or a separate source contract is approved.
- No jobs, repositories, routers, or migrations were edited by Agent D.
