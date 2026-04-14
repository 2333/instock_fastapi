# W0 Readiness

> Status: initial evidence captured
> Branch: `m1/data-layer-restart`
> Scope: restart readiness evidence only

## Repository State

- Current branch: `m1/data-layer-restart`.
- Worktree caveat: the branch currently contains uncommitted M1 restart work, including documentation updates, Alembic scaffold files, dependency updates, and the M1 artifact directory. Treat this artifact as part of the same restart package, not as evidence from a clean committed baseline.

## Readiness Checks

### Database Connectivity

Do not assume live database connectivity from older M1 readiness notes. Run this against the current environment before implementation waves:

```bash
.venv/bin/python -c "from app.database import SYNC_DATABASE_URL; print(SYNC_DATABASE_URL)"
```

Then validate a real connection in the target environment. For Docker-based local development, the configured TimescaleDB service is available through the compose files and should be checked after the database container is healthy.

### TimescaleDB Extension

Use the current database connection and run:

```sql
SELECT * FROM pg_extension WHERE extname = 'timescaledb';
```

Expected result: one row for the `timescaledb` extension before hypertable migrations are executed.

### Tushare Token And Point Tier

Do not trust the historical `scripts/check_m1_readiness.py` references; that script is no longer an active source of truth. Before enabling required or stretch fact tables, run a fresh token check using the current `.env` and record:

- token present / missing
- token authentication result
- point tier
- which interfaces are enabled for `daily_basic`, `stock_st`, `stk_factor_pro`, `report_rc`, `cyq_perf`, and `cyq_chips`

If token or point tier cannot be verified, required table implementation can proceed only for source-independent modeling and tests; ingestion/backfill must remain gated.

### Alembic Availability

Verified locally:

```bash
.venv/bin/python -c "import alembic; print(alembic.__version__)"
```

Observed version:

```text
1.18.4
```

Alembic is also declared in:

- `pyproject.toml`
- `requirements.txt`

## Commands Run

```bash
git status --short --branch
find alembic -maxdepth 2 -type f -print | sort
rg "alembic" -n pyproject.toml requirements.txt alembic.ini alembic
.venv/bin/python -c "import alembic; print(alembic.__version__)"
.venv/bin/alembic -c alembic.ini history
sed -n '1,220p' alembic/env.py
sed -n '1,160p' app/config.py
rg "TUSHARE|DATABASE|POSTGRES|timescale" -n app config docker-compose*.yml .env.example pyproject.toml requirements.txt
```

## Observed Live Results

Recorded on 2026-04-09:

- Disposable PostgreSQL/TimescaleDB connectivity was verified against `127.0.0.1:55432` using database `instock_m1` and user `instock_m1`.
- Live Tushare validation reached the upstream service directly but failed authentication with `您的token不对，请确认。`
- The compatibility fallback host `lianghua.nanyangqiankun.top` also failed DNS resolution in this environment.
- Because authentication failed, point tier and endpoint permissions for `daily_basic`, `stock_st`, `stk_factor_pro`, `report_rc`, `cyq_perf`, and `cyq_chips` remain unverified.

## Open Risks

- Live DB connectivity is now verified for the disposable database, but Timescale extension and hypertable checks still depend on a valid M1 starting schema.
- Tushare token presence is not sufficient; current live authentication failed, so Tushare-backed ingestion and backfill remain blocked until a valid token is provided.
- Alembic has a scaffold and revision chain, but the current head is not an empty-database baseline.
