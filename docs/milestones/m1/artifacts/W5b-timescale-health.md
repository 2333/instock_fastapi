# W5b Timescale Health Checks

> Owner: Worker F-W5b
> Status: implementation complete, live Timescale validation still required
> Scope: lightweight Timescale health runner and testable result shaping

## Files Changed

- `scripts/timescale_health_check.py`
- `tests/test_timescale_health_check.py`
- `docs/milestones/m1/artifacts/W5b-timescale-health.md`

## Checks Implemented

- Timescale extension availability via `pg_extension`
- Hypertable registration for:
  - `daily_bars`
  - `fund_flows`
  - `indicators`
  - `patterns`
- Chunk existence for each core hypertable
- Compression enabled for each core hypertable
- Compression policy presence for each core hypertable
- Representative `EXPLAIN` checks for:
  - a `daily_bars` window query
  - a `fund_flows` rank query

## Runner Behavior

- The runner returns structured dictionaries with:
  - `check`
  - `status`
  - `table`
  - `value`
  - `details`
- Non-PostgreSQL connections return the full check set with `status = "skipped"`.
- The CLI is intentionally lightweight and supports a JSON output mode.
- W3/W4 fact tables are not part of the hypertable scope in this runner; they remain regular PostgreSQL tables unless a later explicit promotion is approved.

## Validation

```bash
.venv/bin/pytest tests/test_timescale_health_check.py -q
git diff --check -- scripts/timescale_health_check.py tests/test_timescale_health_check.py docs/milestones/m1/artifacts/W5b-timescale-health.md
```

Expected result:

- unit tests pass without a live Timescale database
- diff check passes for the W5b write set

## Live Gate

Required before W5 acceptance:

```bash
.venv/bin/python scripts/timescale_health_check.py --json
```

Run this against a disposable PostgreSQL/Timescale database after W2/W3/W4 are deployed, and record:

- extension availability
- hypertable registration
- chunk counts
- compression state
- compression policies
- representative `EXPLAIN` output

## Residual Risks

- This artifact does not yet include live SQL output from a Timescale database.
- The representative `EXPLAIN` checks are shape checks, not plan-content assertions; W5 should record the live output in the aggregate health artifact.
