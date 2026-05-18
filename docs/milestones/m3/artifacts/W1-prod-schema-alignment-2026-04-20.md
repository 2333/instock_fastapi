# W1 Production Schema Alignment 2026-04-20

> Status: completed
> Owner: controller
> Scope: production-only minimal schema alignment required before rebuilding and redeploying `0.3.0`

## Goal

Bring the live production PostgreSQL schema back to the minimum contract required by the current runtime without introducing fallback code or falsely stamping Alembic history.

## Controlled boundary

- Take a restorable production backup before any DDL.
- Apply only the missing runtime-blocking columns and index:
  - `stocks.industry_label`
  - `stocks.industry_taxonomy`
  - `stocks.industry_source`
  - `stocks.industry_updated_at`
  - `daily_bars.source`
  - `attention.group`
  - `attention.notes`
  - `attention.alert_conditions`
  - `user_events.event_version`
  - `ix_user_events_event_type_created`
- Do not stamp `alembic_version`.
- Do not attempt Timescale / PK / historical uniqueness rewrites in this operation.
- Note: this boundary was truthful for the `2026-04-20` minimal unblock only. It did not resolve later-audited `daily_bars` uniqueness drift.

## Backup

- full backup: `backups/postgres/instock_20260420_172221.dump`
- schema snapshot: `backups/postgres/instock_schema_pre_align_20260420.sql`

## DDL source

- [scripts/pre_m3_prod_schema_align_20260420.sql](/Users/zhangkai/projects/instock_fastapi/scripts/pre_m3_prod_schema_align_20260420.sql:1)

## Verification

- applied with:
  - `docker exec -i instock_postgres psql -U instock -d instock -v ON_ERROR_STOP=1 -f - < scripts/pre_m3_prod_schema_align_20260420.sql`
- post-DDL contract checks:
  - model-vs-db diff now only reports `user_events.ip_hash` / `user_events.user_agent` as harmless extra legacy columns
  - ORM materialization succeeds for `Stock`, `Attention`, `UserEvent`, and `DailyBar`
- release + deploy:
  - rebuilt `instock/instock-app:0.3.0`
  - rebuilt `instock/instock-frontend:0.3.0`
  - deployed with `PRE_M3_RELEASE_CLASS=non_schema`
  - postdeploy smoke passed for backend health, backend info, and frontend home

## Observed runtime state

- `instock_app`: `healthy`
- `instock_frontend`: `healthy`
- `/health` returns version `0.3.0`
- `/api/v1/info` returns version `0.3.0`

## Release follow-up

- Production is now running the rebuilt `0.3.0` images on the aligned schema.
- The live production database is still not under Alembic control; future `schema_contract` releases remain blocked until a truthful Alembic onboarding/baseline is completed.

## 2026-04-21 follow-up finding

- The April completeness audit and repair run on `2026-04-21` proved that live `daily_bars` still lacked the runtime-assumed uniqueness contract `uq_daily_bars_ts_code_trade_date_dt`.
- During the BaoStock-based repair, `save_daily_bars(...)` first attempted `ON CONFLICT ON CONSTRAINT uq_daily_bars_ts_code_trade_date_dt`, then truthfully downgraded to row-by-row compatibility writes because the live production database did not have that constraint.
- This drift was outside the `2026-04-20` minimal unblock boundary above; it must now be tracked as a post-alignment schema fact rather than silently treated as “already aligned”.
- Before future truthful `schema_contract` onboarding, production must either:
  - add the `daily_bars` uniqueness contract after duplicate-data verification, or
  - explicitly record why that contract cannot be established and what compensating boundary is being enforced instead.
