# W1 Alembic Baseline

> Status: scaffold verified; existing-schema stamp/document strategy accepted for current-stage M1
> Owner: Agent A / Agent F coordination
> Scope: Alembic baseline evidence and handoff

## Current Alembic Files

The restart branch currently contains the minimum Alembic scaffold:

```text
alembic.ini
alembic/README
alembic/env.py
alembic/script.py.mako
alembic/versions/.gitkeep
```

`alembic/env.py` wires Alembic to:

- `app.database.SYNC_DATABASE_URL`
- `app.models.stock_model.Base.metadata`

Autogenerate options currently enabled:

- `compare_type=True`
- `compare_server_default=True`

## Verified Commands

Alembic package import:

```bash
.venv/bin/python -c "import alembic; print(alembic.__version__)"
```

Observed:

```text
1.18.4
```

Alembic script directory discovery:

```bash
.venv/bin/alembic -c alembic.ini history
```

Observed result: command completed successfully with no revisions listed.

## Disposable Database Validation

Executed against a disposable TimescaleDB at `127.0.0.1:55432`:

```bash
DB_HOST=127.0.0.1 DB_PORT=55432 DB_USER=instock_m1 DB_PASSWORD=instock_m1_pass DB_NAME=instock_m1 \
  .venv/bin/alembic -c alembic.ini upgrade head
```

Observed result:

```text
INFO  [alembic.runtime.migration] Running upgrade  -> m1_core_fact_timescale, m1 core fact timescale
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "daily_bars" does not exist
```

This confirms the current M1 revision chain is an existing-schema migration path. It cannot be treated as an empty-database baseline.

## Accepted Migration Strategy

Current-stage M1 accepts the existing-schema `stamp/document` path:

- treat the pre-M1 core tables as the required starting schema
- document that starting state in M1 artifacts
- validate `alembic upgrade head` only from that accepted existing-schema start

Empty-database bootstrapping remains a later enhancement and is not part of current-stage M1 acceptance. Do not present the current revision chain as if `alembic upgrade head` were expected to succeed on an empty database.

## Empty-Database Target Plan

Run these only after a true baseline revision exists:

```bash
alembic -c alembic.ini revision --autogenerate -m "m1_baseline"
alembic -c alembic.ini upgrade head
alembic -c alembic.ini downgrade -1
alembic -c alembic.ini upgrade head
```

For Timescale-specific DDL, do not rely only on autogenerate. Add hand-written `op.execute(...)` statements for:

- `CREATE EXTENSION IF NOT EXISTS timescaledb`
- `create_hypertable(...)`
- compression settings
- compression policy

## Downgrade Policy

- Every migration must define an explicit downgrade path for ordinary schema changes.
- Timescale hypertable downgrades must be reviewed before execution. If a Timescale operation is irreversible or unsafe, the migration must document the reason and the rollback alternative in the migration body and artifact.
- No migration head should be introduced without a matching W2/W3 artifact that records upgrade/downgrade results on a disposable database.

## Handoff To Agent A

Before Agent A creates schema migrations:

- Confirm W1 schema conventions are accepted.
- Confirm W1 Timescale policy is accepted.
- Confirm the target database for autogenerate is disposable or intentionally created for migration testing.
- Confirm `app/models/stock_model.py` and `alembic/versions/` are single-writer for the wave.

## Open Risks

- There is still no empty-database baseline revision; the current W2/W3 Alembic revisions require pre-existing core tables.
- If the project later needs empty-database bootstrapping, add a true baseline revision before the M1 Timescale migration as follow-up work rather than reopening current-stage M1 acceptance.
- `app.config.get_settings()` enforces a non-default `SECRET_KEY`; Alembic commands that import application settings require a valid environment.
