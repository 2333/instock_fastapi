# W2 pro_bar Provider And Daily Fetch Switch

> Agent: B
> Status: implemented, focused tests passing
> Scope: `TushareProvider.fetch_pro_bar(...)` and `fetch_daily_task` Tushare primary path

## Files Changed

- `core/crawling/tushare_provider.py`
- `app/jobs/tasks/fetch_daily_task.py`
- `tests/test_tushare_pro_bar.py`
- `tests/test_fetch_tasks.py`

## Behavior Implemented

- Added canonical async `TushareProvider.fetch_pro_bar(...)`.
- Added sync helper `_fetch_pro_bar_sync(...)` with current M1 support for:
  - `asset="E"`
  - `freq="D"`
  - optional `adj`
  - single-stock `ts_code`
  - whole-market `trade_date` compatibility path
- `fetch_kline(...)` now delegates to `fetch_pro_bar(asset="E", freq="D")`.
- `fetch_daily_by_date(...)` now routes through `_fetch_pro_bar_sync(...)` while preserving the existing whole-market Tushare `daily(trade_date=...)` behavior internally.
- `_fetch_bars_with_fallback(...)` now calls `fetch_pro_bar(...)` for the primary Tushare stock path before falling back to BaoStock and EastMoney.
- `fetch_daily_task` now targets `uq_daily_bars_ts_code_trade_date_dt` for M1 upsert compatibility.
- Normalized Tushare bar rows now include:
  - `ts_code`
  - `trade_date`
  - `trade_date_dt`
  - legacy-compatible `date`, OHLCV, amount, and change fields

## Fallback Behavior

- ETF and BJ routing still bypasses Tushare and goes directly to EastMoney.
- If `fetch_pro_bar(...)` returns no bars or raises, `_fetch_bars_with_fallback(...)` preserves the existing primary-only and fallback-chain behavior.
- Unsupported `asset` or `freq` values return an empty result with a warning rather than attempting an unverified endpoint.

## Commands Run

```bash
.venv/bin/pytest tests/test_tushare_pro_bar.py tests/test_fetch_tasks.py::test_fetch_daily_bars_uses_tushare_pro_bar_before_fallback tests/test_fetch_tasks.py::test_fetch_daily_bars_routes_etf_directly_to_eastmoney tests/test_fetch_tasks.py::test_fetch_daily_bars_routes_bj_directly_to_eastmoney -q
.venv/bin/pytest tests/test_m1_core_migrations.py tests/test_tushare_pro_bar.py tests/test_fetch_tasks.py -q
```

Result:

```text
6 passed, 1 warning
18 passed, 1 warning
```

## Open Risks

- The single-stock path uses the Tushare SDK `ts.pro_bar(...)`; live token and point-tier behavior still needs W0 environment verification.
- Whole-market `trade_date` bulk mode remains backed by Tushare `daily(trade_date=...)` because `ts.pro_bar(...)` is not a safe drop-in replacement for that existing batch behavior.
- Only `asset="E"` / daily stock bars are implemented in M1 W2. Index/fund/futures support remains deferred unless a later M1 task explicitly adds it.
