# W3 Stretch Facts Feasibility

> Agent: E
> Status: planning artifact
> Scope: `broker_forecast`, `chip_performance`, `chip_distribution`

---

## Inputs Reviewed

- `docs/milestones/m1/M1_RESTART_PLAN.md`
- `docs/milestones/m1/DATA_LAYER_REPORT.md`
- `docs/milestones/m1/M1_PROGRESS_TRACKER.md`
- `core/crawling/tushare_provider.py`

Current restart policy gates these tables behind confirmed Tushare permissions. They should not block M1 if the current token/point tier cannot support them.

---

## Go / No-Go Gates

| Table | Endpoint | Required tier | M1 decision rule |
|-------|----------|---------------|------------------|
| `broker_forecast` | `report_rc` | 8000+ points for full use | Implement only if W0 confirms full tier; otherwise record explicit deferral |
| `chip_performance` | `cyq_perf` | 5000+ points | Implement only if W0 confirms access and W3 required facts are not blocked |
| `chip_distribution` | `cyq_chips` | 5000+ points | Implement only if W0 confirms access and W3 required facts are not blocked |

If W0 cannot verify token validity, mark all three as `blocked_by_readiness` and do not create models or migrations yet.

---

## Minimal Scope If Allowed

### `broker_forecast`

Purpose: analyst forecast reference data.

Minimum identity/key fields to verify:

- `ts_code`
- `report_date`
- `org_name`
- `quarter`

Proposed unique key: `ts_code + report_date + org_name + quarter`.

Minimum payload fields to verify:

- stock/name metadata if returned
- forecast EPS/profit/revenue fields exposed by current Tushare response
- report title/type/author fields if returned

Implementation rule:

- This is optional stretch work. If included, keep the first M1 API surface narrow and read-only.

### `chip_performance`

Purpose: daily chip cost/winner-rate reference.

Minimum identity/key fields to verify:

- `ts_code`
- `trade_date`

Proposed unique key: `ts_code + trade_date_dt`.

Minimum payload fields to verify:

- cost distribution summary fields
- winner rate / profit ratio fields
- average cost or concentration fields if returned

Implementation rule:

- Store only verified numeric columns and keep nullable columns permissive.
- Do not wire screening conditions until W4 explicitly accepts the service/API scope.

### `chip_distribution`

Purpose: price-level chip distribution reference.

Minimum identity/key fields to verify:

- `ts_code`
- `trade_date`
- `price` or equivalent price bucket field

Proposed unique key: `ts_code + trade_date_dt + price`.

Minimum payload fields to verify:

- price bucket
- proportion/volume/cost fields returned by `cyq_chips`

Implementation rule:

- Expect more rows per stock/date than other daily fact tables.
- Agent A should review storage/index impact before adding this table to mandatory M1 scope.

---

## Deferral Rule

If the token tier is insufficient or endpoint access is unverified:

- do not add SQLAlchemy models
- do not add Alembic migrations
- do not add scheduler tasks
- record the endpoint as deferred in this artifact with the exact readiness blocker
- keep M1 completion focused on `daily_basic`, `stock_st`, and any required facts allowed by points

---

## Proposed Focused Tests If Allowed

- mocked provider mapping test for each endpoint
- empty response returns `[]`
- exception path returns `[]` and logs a warning
- unique-key conflict behavior after Agent A model/migration handoff
- read-only service/API tests only if W4 accepts endpoint exposure in M1

---

## Handoff To Agent A / Agent C

Agent A owns final model/migration integration. Agent C owns W4 repository/API exposure. Before either owner edits shared files, update this artifact with:

- verified point tier and endpoint access result
- representative response columns
- final go/no-go per table
- storage/index risk for `chip_distribution`
- API exposure decision or explicit M1 deferral

No shared code was edited in this planning artifact.
