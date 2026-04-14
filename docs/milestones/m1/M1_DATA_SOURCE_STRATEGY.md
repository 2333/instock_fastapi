# M1 Data Source Strategy

> Status: active M1 source policy
> Scope: token-independent data acquisition choices after live Tushare auth failure

## Principle

M1 does not use silent fallback for new data-layer acceptance. Every fetch or backfill path must declare the source policy it is using, record the actual source used in audit output, and document any semantic differences from the original Tushare interface.

Source substitution is allowed only when the target table's field semantics remain clear. Partial or snapshot-only data must not be presented as a complete historical Tushare equivalent.

## Current Stage Acceptance Boundary

While Tushare access remains unavailable, current-stage M1 acceptance is limited to:

- Alembic validation on the accepted existing-schema start
- `daily_bars` bounded rehearsal with an explicit source policy
- `technical_factors` local computation from `daily_bars`, recorded as `daily_bars_local`
- quality checks
- Timescale health checks

`daily_basic` and `stock_st` are not part of current-stage acceptance. They move only when one of these conditions is true:

- a valid Tushare token is available again, or
- a separate source contract is reviewed and approved for their reduced semantics

## Table Policy

| Table | M1 Source Policy | Status |
|-------|------------------|--------|
| `daily_bars` | Explicit source policy. Default bounded strategy is `prefer_tushare`, which tries `tushare -> baostock -> eastmoney` and records the actual source used. Single-source modes `tushare`, `baostock`, and `eastmoney` remain available. | Implemented for bounded backfill |
| `technical_factors` | Compute locally from `daily_bars` and mark source as `daily_bars_local`. Do not depend on Tushare `stk_factor_pro` while token access is unstable. | Implemented for local bounded backfill |
| `stock_st` | EastMoney/stock-name snapshot can be considered later as `eastmoney_name_snapshot`, but it is not a historical `stock_st` equivalent. | Gated follow-up |
| `daily_basic` | EastMoney snapshot can be considered later for partial valuation/liquidity fields, but it is not a complete historical `daily_basic` equivalent. | Gated follow-up |
| `broker_forecast`, `chip_performance`, `chip_distribution` | Keep gated behind confirmed Tushare permissions or a separately approved source contract. | Deferred |

## Acceptance Rules

- `daily_bars` bounded rehearsal must pass an explicit source policy before execution.
- `prefer_tushare` is acceptable because the policy itself is explicit and the final source used is recorded per item and in audit output.
- `technical_factors` can be accepted with local computation if the job reads only `daily_bars`, writes `technical_factors`, and records `source=daily_bars_local`.
- `stock_st` and `daily_basic` non-Tushare alternatives require a new mapping artifact before implementation and do not block current-stage M1 acceptance.
- Any source-specific field loss must be visible in the task artifact and API documentation before production use.

## Current Commands

```bash
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source baostock --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source eastmoney --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_daily_bars_rehearsal.py --source prefer_tushare --start-date 20240102 --end-date 20240105 --code-limit 5
.venv/bin/python scripts/run_m1_technical_factors_backfill.py --start-date 20240102 --end-date 20240105 --code-limit 5
```

All commands default to dry-run. Add `--execute` only after the environment points to a disposable database or an approved target database.
