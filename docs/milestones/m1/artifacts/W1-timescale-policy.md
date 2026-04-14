# W1 Timescale Policy

> Date: 2026-04-08
> Agent: Agent F
> Scope: Timescale policy and health-check design
> Write set: `docs/milestones/m1/artifacts/W1-timescale-policy.md`

## Inputs Reviewed

- `docs/milestones/m1/M1_RESTART_PLAN.md`
- `app/models/stock_model.py`
- Current M1 rule: keep `fund_flows` as the compatibility table name unless a dedicated migration explicitly replaces it with `moneyflow`.

## Hypertable Scope

M1 should convert these existing core fact tables to Timescale hypertables:

| Table | Time column | Current notes |
|-------|-------------|---------------|
| `daily_bars` | `trade_date_dt` | Has nullable `trade_date_dt`; current uniqueness still uses `ts_code + trade_date`. |
| `fund_flows` | `trade_date_dt` | Has nullable `trade_date_dt`; current uniqueness still uses `ts_code + trade_date`. |
| `indicators` | `trade_date_dt` | Has nullable `trade_date_dt`; current uniqueness still uses `ts_code + trade_date + indicator_name`. |
| `patterns` | `trade_date_dt` | Already has non-null `trade_date_dt` and uniqueness on `ts_code + trade_date_dt + pattern_name`; still indexes `trade_date`. |

Do not include `stock_tops`, `stock_block_trades`, `stock_bonus`, `stock_limitup_reasons`, `stock_chip_races`, `sector_fund_flows`, or `north_bound_funds` in the first M1 hypertable wave unless a later task explicitly promotes them.

## Chunk, Compression, And Retention Policy

- Chunk interval: start with `7 days` for all four core fact tables.
- Compression: enable after `30 days`.
- Suggested segment-by:
  - `daily_bars`: `ts_code`
  - `fund_flows`: `ts_code`
  - `indicators`: `ts_code, indicator_name`
  - `patterns`: `ts_code, pattern_name`
- Suggested order-by: `trade_date_dt DESC`.
- Retention: do not configure data-drop retention in M1. Historical data must remain available until a separate retention decision is made.

## Migration Cautions

- Backfill `trade_date_dt` from `trade_date` before creating hypertables or changing uniqueness. Rows with null `trade_date_dt` must be fixed or excluded before hypertable conversion.
- Existing unique constraints that still use `trade_date` need explicit migration decisions:
  - Either add new unique indexes on the canonical `trade_date_dt` keys and keep old constraints temporarily, or replace old constraints after data parity is proven.
  - Avoid dropping old constraints before services are updated to use `trade_date_dt`.
- Timescale unique indexes on hypertables must include the time partition column. The target uniqueness keys in the restart plan satisfy that rule if they use `trade_date_dt`.
- `patterns` is closest to target uniqueness, but its `trade_date` index should be reviewed after query migration.
- Existing services still query `trade_date` in several places; do not force `trade_date` removal in the Timescale migration. Keep API compatibility while service/query work catches up.
- Use hand-written Alembic SQL for Timescale operations; autogenerate will not understand `create_hypertable` or compression policies.

## Migration SQL Sketch

Use this as a policy sketch, not as copy-paste final migration SQL:

```sql
CREATE EXTENSION IF NOT EXISTS timescaledb;

UPDATE daily_bars
SET trade_date_dt = to_date(trade_date, 'YYYYMMDD')
WHERE trade_date_dt IS NULL AND trade_date ~ '^[0-9]{8}$';

SELECT create_hypertable(
    'daily_bars',
    by_range('trade_date_dt', INTERVAL '7 days'),
    if_not_exists => TRUE,
    migrate_data => TRUE
);

ALTER TABLE daily_bars SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'ts_code',
    timescaledb.compress_orderby = 'trade_date_dt DESC'
);

SELECT add_compression_policy('daily_bars', INTERVAL '30 days', if_not_exists => TRUE);
```

Repeat the same structure for `fund_flows`, `indicators`, and `patterns`, adapting segment-by columns and canonical uniqueness checks.

## Validation SQL

```sql
SELECT extname, extversion
FROM pg_extension
WHERE extname = 'timescaledb';

SELECT hypertable_schema, hypertable_name, num_dimensions
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('daily_bars', 'fund_flows', 'indicators', 'patterns')
ORDER BY hypertable_name;

SELECT hypertable_name, chunk_name, range_start, range_end
FROM timescaledb_information.chunks
WHERE hypertable_name IN ('daily_bars', 'fund_flows', 'indicators', 'patterns')
ORDER BY hypertable_name, range_start DESC
LIMIT 20;

SELECT hypertable_name, compression_enabled
FROM timescaledb_information.hypertables
WHERE hypertable_name IN ('daily_bars', 'fund_flows', 'indicators', 'patterns')
ORDER BY hypertable_name;

SELECT hypertable_name, policy_name, config
FROM timescaledb_information.jobs
WHERE hypertable_name IN ('daily_bars', 'fund_flows', 'indicators', 'patterns')
ORDER BY hypertable_name, policy_name;

EXPLAIN
SELECT ts_code, trade_date_dt, close
FROM daily_bars
WHERE ts_code = '000001.SZ'
  AND trade_date_dt >= CURRENT_DATE - INTERVAL '90 days'
ORDER BY trade_date_dt DESC
LIMIT 120;
```

## Acceptance Criteria

- `CREATE EXTENSION IF NOT EXISTS timescaledb` is present in the migration path.
- All four target tables appear in `timescaledb_information.hypertables`.
- Compression is enabled for all four tables with a 30-day policy.
- No retention-drop policy is configured in M1.
- Validation output is recorded in the later `W5-quality-backfill-health.md` artifact.
- Migration artifacts clearly state how old `trade_date` constraints and indexes are preserved, replaced, or phased out.
