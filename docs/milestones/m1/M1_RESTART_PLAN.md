# M1 Data Layer Restart Plan

> Version: 2026-04-07
> Branch: `m1/data-layer-restart`
> Status: restart source of truth; current-stage acceptance complete, token-dependent follow-up remains open
> Supersedes: older kickoff/readiness notes that referenced deleted M1 readiness or Timescale transition scripts

---

## Summary

`M1` restarts from the cleaned `M0` baseline as the data-layer / Timescale milestone. The goal is not to write a migration in isolation; the current stage is complete only when schema, token-independent ingestion, backfill, data quality, and Timescale health checks are all verified together.

This file is the authoritative M1 restart plan. Older files in this directory remain useful as historical analysis, but any conflict should be resolved in favor of this restart plan.

Current source policy after live Tushare authentication failure is tracked in `docs/milestones/m1/M1_DATA_SOURCE_STRATEGY.md`.

The active source-selection companion plan is `docs/milestones/m1/M1_DATA_SOURCE_STRATEGY.md`. It is required while Tushare access is unstable and forbids silent fallback behavior in new M1 rehearsal paths.

Current stage acceptance is intentionally narrowed so progress is not blocked by a missing Tushare token. The accepted token-independent boundary is:

- Alembic existing-schema migration path and documented starting schema
- `daily_bars` ingestion and bounded rehearsal
- local `technical_factors` backfill from `daily_bars`
- quality checks
- Timescale health checks

`daily_basic` and `stock_st` remain explicit gated follow-up work until a valid Tushare token exists or a separately approved non-Tushare source contract is added.

---

## Branch And Start Rules

- Work from `main` after `M0 rebaseline` has been merged or explicitly accepted as the new baseline.
- Use branch `m1/data-layer-restart`.
- Start commands:

```bash
git switch main
git pull --ff-only origin main
git switch -c m1/data-layer-restart
```

If the branch already exists locally, use:

```bash
git switch m1/data-layer-restart
```

Before starting implementation, run a fresh readiness check instead of relying on old references to deleted scripts:

- Confirm database connectivity using the current project settings.
- Confirm Timescale extension availability with `SELECT * FROM pg_extension WHERE extname = 'timescaledb';`.
- Confirm the current Tushare token works and record the point tier.
- Confirm Alembic availability after dependency installation.

---

## WS-0 Foundation

### Alembic Baseline

- Add Alembic to project dependencies.
- Initialize `alembic/` and wire `alembic/env.py` to `app.models.stock_model.Base`.
- Establish Alembic as the schema-change mechanism for M1 and future schema changes.
- Treat the current M1 revisions as an existing-schema migration path until a true baseline or stamp strategy is added and validated.
- Keep the existing `init_db()` helper as test/dev support unless tests are explicitly migrated away from it.
- Add migration conventions for revision naming, downgrade expectations, hand-written Timescale SQL, and disposable-database validation.

### Schema Conventions

- Use `trade_date_dt` as the canonical fact-table date for M1 query and hypertable policy.
- Keep existing `trade_date` as a compatibility/readable source during the M1 transition unless a table-specific migration removes it.
- Use stable unique constraints and indexes for fact tables:
  - `daily_bars`: `ts_code + trade_date_dt`
  - `fund_flows`: `ts_code + trade_date_dt`
  - `indicators`: `ts_code + trade_date_dt + indicator_name`
  - `patterns`: `ts_code + trade_date_dt + pattern_name`
- Review and update services so canonical date filtering uses `trade_date_dt`, while preserving API response compatibility where needed.

### Timescale Policy

- Convert core fact tables to Timescale hypertables on `trade_date_dt`.
- M1 hypertable scope:
  - `daily_bars`
  - `fund_flows`
  - `indicators`
  - `patterns`
- Keep `fund_flows` as the compatibility table name in M1 unless a dedicated migration explicitly replaces it with `moneyflow`.
- Set compression policy after 30 days.
- Do not drop historical data via retention in M1.
- Validate extension availability, hypertable registration, chunk creation, compression policy, and representative query plans.

---

## WS-1 Core Tables And Ingestion

- Standardize `daily_bars`, `fund_flows`, `indicators`, and `patterns` time columns and service queries.
- Extend `TushareProvider` with a canonical `fetch_pro_bar(...)` method rather than creating a separate service, because current Tushare access already lives in `core/crawling/tushare_provider.py`.
- Switch `fetch_daily_task` to use `fetch_pro_bar(asset="E")`.
- Defer index/fund/futures ingestion unless a later M1 task explicitly includes it.
- Preserve existing stock, selection, and backtest API behavior while the storage layer changes underneath.

---

## WS-2 New Fact Tables

Implement new M1 tables in this priority order:

| Priority | Table | Tushare Interface | M1 Rule |
|----------|-------|-------------------|---------|
| 1 | `daily_basic` | `daily_basic` | Gated follow-up until a valid Tushare token exists or a separately approved source contract is added |
| 2 | `stock_st` | `stock_st` | Gated follow-up until a valid Tushare token exists or a separately approved source contract is added |
| 3 | `technical_factors` | `stk_factor_pro` | Current stage accepts local computation from `daily_bars`; Tushare-provided variant is deferred |
| 4 | `broker_forecast` | `report_rc` | Optional stretch; gated by confirmed permissions |
| 5 | `chip_performance` | `cyq_perf` | Optional stretch; gated by confirmed permissions |
| 6 | `chip_distribution` | `cyq_chips` | Optional stretch; gated by confirmed permissions |

Each implemented table needs:

- SQLAlchemy model.
- Alembic migration.
- Provider fetch method.
- Fetch task or explicit backfill entry.
- Unit tests for mapping and conflict handling.
- Data quality checks for duplicates, null rate, and date coverage.

After live Tushare authentication failed, M1 uses explicit source contracts instead of silent fallback:

- `daily_bars` bounded rehearsal uses an explicit source policy. Default policy is `prefer_tushare`, which keeps Tushare first without making it mandatory and records the actual source used.
- `technical_factors` may be computed locally from `daily_bars` and recorded as `daily_bars_local`.
- `daily_basic` and `stock_st` remain outside current stage acceptance until Tushare auth is restored or a separate source contract is approved.

---

## WS-3 Quality, Backfill, And Health

- Add a lightweight data quality runner for completeness, date range, duplicate keys, null rates, and cross-source sanity where EastMoney fallback exists.
- Add Timescale health checks for:
  - extension availability
  - hypertable registration
  - chunk creation
  - compression policy
  - representative query plans
- Require one controlled backfill rehearsal for `daily_bars`.
- Require one controlled backfill rehearsal for at least one newly added table in the accepted current-stage scope.
- Record backfill and health-check results in an M1 artifact before marking the milestone complete.

---

## Multi-Agent Execution Matrix

Use this matrix to split M1 work across agents without overlapping write sets. If a task needs to touch a file outside its write set, stop and record the required handoff in the task artifact before editing.

All task artifacts should be written under `docs/milestones/m1/artifacts/`.

| Wave | Agent | Owned scope | Write set | Depends on | Acceptance artifact |
|------|-------|-------------|-----------|------------|---------------------|
| W0 | Agent F | Restart coordination and readiness evidence | `docs/milestones/m1/M1_RESTART_PLAN.md`, `docs/milestones/m1/artifacts/`, M1 tracker if introduced | Current branch `m1/data-layer-restart` | `docs/milestones/m1/artifacts/W0-readiness.md` records branch, DB connectivity, Timescale extension check, Tushare token/point tier, and Alembic availability |
| W1 | Agent A | Alembic baseline and migration conventions | `alembic/`, `alembic.ini`, migration convention docs, dependency files | W0 readiness | `docs/milestones/m1/artifacts/W1-alembic-baseline.md` records `alembic history`, disposable DB migration command plan, and downgrade policy |
| W1 | Agent B | Date/schema convention review for core fact tables | Schema convention docs, analysis artifact only unless Agent A hands off a migration | W0 readiness | `docs/milestones/m1/artifacts/W1-schema-conventions.md` records canonical `trade_date_dt` policy, compatibility use of `trade_date`, and unique/index decisions |
| W1 | Agent F | Timescale policy and health-check design | Timescale policy docs, health-check script/spec files only | W0 readiness, Agent B schema convention draft | `docs/milestones/m1/artifacts/W1-timescale-policy.md` records hypertable scope, chunk policy, compression policy, no-retention decision, and SQL validation queries |
| W2 | Agent A | Core fact table migrations | `app/models/stock_model.py`, `alembic/versions/`, migration tests | W1 Alembic baseline, W1 schema conventions, W1 Timescale policy | `docs/milestones/m1/artifacts/W2-core-migrations.md` records migration files, affected tables, upgrade/downgrade results, and Timescale validation |
| W2 | Agent B | `pro_bar` provider and daily fetch switch | `core/crawling/tushare_provider.py`, `app/jobs/tasks/fetch_daily_task.py`, focused provider/fetch tests | W1 schema conventions; can run in parallel with Agent A until final integration | `docs/milestones/m1/artifacts/W2-pro-bar.md` records supported parameters, `asset="E"` behavior, fallback behavior, and focused test output |
| W2 | Agent C | Service/query compatibility for existing reads | Repositories/services using `daily_bars`, `fund_flows`, `indicators`, `patterns`; focused service tests | W2 core migration interface settled by Agent A | `docs/milestones/m1/artifacts/W2-service-compat.md` records changed query paths and stock/selection/backtest regression results |
| W3 | Agent D | New fact table ingestion design and gating decisions | Mapping artifacts and tests for `daily_basic`, `stock_st`, `technical_factors`; no shared model/migration edits without Agent A handoff | W1 Alembic baseline, current Tushare permission tier | `docs/milestones/m1/artifacts/W3-required-facts.md` records endpoint fields, permission status, mapping decisions, and focused tests |
| W3 | Agent A | Required new fact table model and migration integration | `app/models/stock_model.py`, `alembic/versions/`, model tests | Agent D mapping artifact | `docs/milestones/m1/artifacts/W3-required-fact-migrations.md` records model/migration files and upgrade/downgrade validation |
| W3 | Agent E | Optional/stretch fact table feasibility | Artifact only for `broker_forecast`, `chip_performance`, `chip_distribution` unless permissions are confirmed | W0 Tushare token/point check | `docs/milestones/m1/artifacts/W3-stretch-facts.md` records go/no-go per optional table and required permissions |
| W4 | Agent C | Current-stage fact table repository/API integration | Repositories, services, routers, schemas, and focused API tests for M1 fact tables | W3 required fact migrations; at least one required table has quality-check coverage planned | `docs/milestones/m1/artifacts/W4-api-repository.md` records exposed endpoints or explicit deferrals, service query paths, API test output, and screening integration status |
| W5 | Agent F | Data quality runner, backfill rehearsal, Timescale health checks | Quality/check scripts, backfill scripts, health-check artifacts | W2 core migrations, at least one W3 required fact table, W4 API/repository decisions | `docs/milestones/m1/artifacts/W5-quality-backfill-health.md` records quality output, `daily_bars` backfill rehearsal, one new-table backfill rehearsal, and Timescale health SQL results |
| W6 | Reviewer | Integration review and merge readiness | Review artifact only unless fixes are handed back to owners | W2, W3, W4, and W5 artifacts complete | `docs/milestones/m1/artifacts/W6-review.md` records open risks, required fixes, final test commands, rollback boundary, and go/no-go |

### Parallelism Rules

- W0 must complete before all implementation waves.
- W1 tasks can run in parallel, but Agent A owns Alembic files and Agent F owns Timescale health policy.
- W2 Agent A and Agent B can work in parallel until integration; Agent C starts after Agent A defines the migration interface.
- W3 mapping work can run in parallel, but `app/models/stock_model.py` and `alembic/versions/` remain owned by Agent A to avoid migration conflicts.
- W4 starts after required fact table migrations are available and records whether each new table has API exposure or an explicit M1 deferral.
- W5 starts only after core migrations, at least one required new fact table, and W4 API/repository decisions are available.
- W6 reviewer starts only after all acceptance artifacts for W2-W5 exist.

### Shared File Rules

- `app/models/stock_model.py`: single-writer, Agent A during migration waves.
- `alembic/versions/`: single-writer, Agent A; no parallel migration head creation without explicit coordination.
- `core/crawling/tushare_provider.py`: Agent B owns provider changes; other agents submit mapping notes through artifacts.
- Scheduler/task registration files: single-writer per wave; owner must be declared in the artifact before editing.
- Shared test fixtures such as `tests/conftest.py`: single-writer per wave; table-specific tests should prefer dedicated test files unless a fixture handoff is recorded.
- `docs/milestones/m1/M1_RESTART_PLAN.md`: Agent F owns coordination edits after this matrix is accepted.

### Wave-Level Exit Criteria

- Every wave must leave an artifact with changed files, commands run, results, and unresolved risks.
- No wave may be marked complete if it introduces a new unreviewed migration head.
- Current-stage M1 is not complete until backend regression, Alembic validation on the accepted existing-schema start, Timescale health checks, and the two required backfill rehearsals are recorded.

---

## Test Plan

- Run backend regression:

```bash
.venv/bin/pytest -q
```

- Run focused ingestion tests for:
  - `fetch_daily_task`
  - `TushareProvider.fetch_pro_bar`
  - Alembic migrations
  - data quality checks
- Run Alembic checks on a disposable database:

```bash
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

- Run SQL health checks against Timescale:
  - extension exists
  - hypertables are registered
  - compression policy is present
- Run one manual smoke path:
  - fetch or backfill a small date range
  - confirm rows exist
  - verify existing stock, selection, and backtest reads still work

---

## Completion Definition

Current-stage `M1` is complete when:

- Alembic has an accepted baseline/stamp strategy and the required starting database state is documented.
- M1 Alembic revisions are validated on the accepted starting database state.
- Core fact tables use the agreed canonical date policy.
- Required core hypertables are created and validated.
- `fetch_daily_task` uses the canonical `fetch_pro_bar(asset="E")` path.
- `daily_bars` and local `technical_factors` are implemented and validated.
- `daily_basic` and `stock_st` are explicitly marked as gated follow-up until a valid Tushare token exists or a separately approved source contract is added.
- Data quality and Timescale health checks run successfully.
- At least two backfill rehearsals are recorded: one for `daily_bars`, one for a new fact table.
- Existing stock, selection, and backtest reads still pass regression tests.

## Follow-Up Boundary

After current-stage acceptance, the remaining work stays attached to `M1` as follow-up backlog rather than reopening the completed current-stage scope:

- `daily_basic` live gate, bounded backfill rehearsal, and quality evidence
- `stock_st` live gate, bounded backfill rehearsal, and quality evidence
- any `daily_basic` / `stock_st` screening integration that depends on those live gates
- any separately approved source contract for reduced-semantics replacements

These follow-up items do not block `M2` by default. If a later milestone directly depends on one of them, that dependency should be declared in that milestone's task definition instead of rolling back the current-stage `M1` acceptance result.

---

## Historical Documents

The following files remain useful as context but are no longer authoritative:

- `DATA_LAYER_REPORT.md`
- `M1_TASK_BREAKDOWN.md`
- `M1_KICKOFF_CHECKLIST.md`
- `M1_READINESS_SUMMARY.md`
- `M1_TUSHARE_TOKEN_BLOCK.md`

Do not run commands from older docs if they reference deleted scripts such as `scripts/check_m1_readiness.py`; replace them with a fresh readiness check that matches the current repository.
