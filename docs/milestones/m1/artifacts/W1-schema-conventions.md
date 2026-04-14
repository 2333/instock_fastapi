# W1 Schema Conventions

> Owner: Agent B
> Scope: date/schema convention review for `daily_bars`, `fund_flows`, `indicators`, and `patterns`
> Write set: this artifact only
> Status: review-ready

---

## Current Model Snapshot

All four core fact tables already expose both a readable string date (`trade_date`) and a canonical date column candidate (`trade_date_dt`), but their constraints and query usage are inconsistent.

| Table | Current model date columns | Current unique/index shape | M1 convention decision |
|-------|----------------------------|----------------------------|------------------------|
| `daily_bars` | `trade_date: String(10)`, `trade_date_dt: Date | None` | unique on `(ts_code, trade_date)`, index on `trade_date` | Move unique key and primary date index to `(ts_code, trade_date_dt)` / `trade_date_dt`; keep `trade_date` as compatibility output during M1. |
| `fund_flows` | `trade_date: String(10)`, `trade_date_dt: Date | None` | unique on `(ts_code, trade_date)`, indexes on `ts_code`, `trade_date` | Keep table name in M1; move unique key and date index to `(ts_code, trade_date_dt)` / `trade_date_dt`; keep `trade_date` for compatibility. |
| `indicators` | `trade_date: String(10)`, `trade_date_dt: Date | None` | unique on `(ts_code, trade_date, indicator_name)`, indexes on `ts_code`, `trade_date` | Move unique key and date index to `(ts_code, trade_date_dt, indicator_name)` / `trade_date_dt`; keep `trade_date` for compatibility. |
| `patterns` | `trade_date: String(10)`, `trade_date_dt: Date` | unique already uses `(ts_code, trade_date_dt, pattern_name)`, index still on `trade_date` | Keep unique key; add or move date index to `trade_date_dt`; keep `trade_date` for compatibility. |

M1 should standardize `trade_date_dt` as the canonical storage/query column and keep `trade_date` as an API/readability compatibility column until a later explicit removal decision.

---

## Compatibility Rules

- `trade_date_dt` is the canonical fact-table time dimension for filtering, ordering, uniqueness, and Timescale hypertables.
- `trade_date` remains available in M1 for API response compatibility and legacy query consumers that still expect `YYYYMMDD` strings.
- Migrations should backfill `trade_date_dt` from `trade_date` before constraints or hypertable conversion:

```sql
UPDATE <table>
SET trade_date_dt = TO_DATE(trade_date, 'YYYYMMDD')
WHERE trade_date_dt IS NULL
  AND trade_date IS NOT NULL
  AND trade_date <> '';
```

- New fetch/write paths should always populate both columns during the compatibility period.
- Service methods that accept `date` as a string may keep the public parameter shape, but should normalize internally before filtering on `trade_date_dt`.
- API payloads may keep returning `trade_date` strings in M1 unless an endpoint contract is explicitly changed.

---

## Service Query Migration Notes

### Already aligned or mostly aligned

- `core/providers/postgres_provider.py`
  - `get_daily_bars`, `get_technicals`, `get_fund_flow`, and `get_latest_trade_date` already filter/order with `trade_date_dt`.
  - It uses `row.trade_date_dt or row.trade_date` for output compatibility.
  - Handoff: confirm output date type expectations in provider tests because `trade_date_dt` may surface as a `date` object.

### Needs migration from `trade_date` string filtering

- `app/repositories/daily_bar_repository.py`
  - Filters, ordering, latest lookup, `get_bar_by_date`, `get_top_gainers`, and `get_top_losers` all use `DailyBarModel.trade_date`.
  - Handoff: update repository methods to normalize string inputs to `date` and query `DailyBarModel.trade_date_dt`; preserve response serialization.
- `app/services/market_data_service.py`
  - `_resolve_trade_date` and Dashboard/health joins use `trade_date`.
  - Handoff: update core fact table calls (`daily_bars`, `fund_flows`) to resolve via `trade_date_dt` while leaving non-M1 reference tables (`stock_tops`, `stock_block_trades`, `north_bound_funds`) on `trade_date`.
  - Joins such as `daily_bars.trade_date = fund_flows.trade_date` should move to `trade_date_dt` for M1 core fact tables.
- `app/services/pattern_service.py`
  - Latest date, pattern filters, ordering, and daily bar snapshot lookups use `trade_date`.
  - Handoff: migrate `patterns` filters/order to `p.trade_date_dt`; migrate `daily_bars` snapshot lookups to `trade_date_dt`, with string output preserved.
- `app/services/selection_service.py`
  - `_resolve_trade_date`, pattern lookups, indicator joins, and daily bar joins use `trade_date`.
  - Handoff: migrate the internal resolved date to a canonical `date` value while preserving returned `trade_date` string fields.
- `app/services/stock_service.py`
  - Stock list/detail, latest bar, indicator, and pattern queries use `trade_date`.
  - Handoff: migrate core fact table lookups to `trade_date_dt` and keep response fields stable.
- `app/services/strategy_service.py`
  - Backtest/strategy result joins to `daily_bars` use string `trade_date`.
  - Handoff: because `strategy_results` is not in the M1 hypertable scope, either keep the join on compatibility `trade_date` for M1 or add an explicit conversion decision before changing it.

---

## Agent A Migration Handoffs

Agent A should own the actual model and Alembic changes. Before starting W2 core migrations, resolve these implementation decisions:

- Whether `trade_date_dt` should become `nullable=False` on all four tables during M1 after backfill, or remain nullable until a separate data quality gate.
- Whether to keep legacy unique constraint names or create new names:
  - Suggested: `uq_daily_bars_ts_code_trade_date_dt`
  - Suggested: `uq_fund_flows_ts_code_trade_date_dt`
  - Suggested: `uq_indicators_ts_code_trade_date_dt_name`
  - Existing `patterns` name can remain if no rename is needed.
- Whether to preserve legacy `trade_date` indexes during the compatibility period. Recommended: keep them initially if existing raw SQL services are migrated gradually; drop only after service migration and tests pass.
- How to represent `trade_date_dt` consistently in typing: `date | None` for nullable transition; `date` after enforced backfill.
- How to update tests that construct rows with `trade_date_dt=None` in current fixtures.

---

## Acceptance Notes

- This artifact only records conventions and handoffs; it does not change schema or queries.
- The next owner for schema changes is Agent A.
- The next owner for service compatibility is Agent C after Agent A defines the final migration interface.

---

## Commands Run

```bash
rg -n "class (DailyBar|FundFlow|Indicator|Pattern)\\b|__tablename__ = \\\"(daily_bars|fund_flows|indicators|patterns)\\\"|trade_date_dt|trade_date" app/models/stock_model.py
rg -n "daily_bars|fund_flows|indicators|patterns|trade_date_dt|trade_date" app/services app/repositories core/providers tests | head -n 260
sed -n '80,230p' app/models/stock_model.py
sed -n '1,130p' app/repositories/daily_bar_repository.py
sed -n '1,280p' core/providers/postgres_provider.py
sed -n '1,190p' app/services/pattern_service.py
sed -n '1,310p' app/services/market_data_service.py
git status --short --branch
```
