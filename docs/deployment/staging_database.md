# Staging Database Workflow

Staging uses an isolated PostgreSQL/TimescaleDB container. It must not connect
directly to the production write database.

## Environment Layout

| Environment | PostgreSQL port | App port | Frontend port | Volume |
| --- | --- | --- | --- | --- |
| default/prod-like | 5432 | 8000 | 3001 | postgres_data |
| dev | 5433 | 8001 | 3002 | postgres_dev_data |
| staging | 5434 | 8002 | 3003 | postgres_staging_data |

Staging defaults to `DEBUG=false`, `LOG_LEVEL=INFO`, and
`SCHEDULER_ENABLED=false` to avoid running market fetch/backfill jobs against
snapshot data unless explicitly enabled.

## Refresh Staging From A Production Snapshot

Create a production backup from the main compose stack:

```bash
make backup-prod-db
```

Restore a selected backup into the isolated staging database:

```bash
make restore-staging-db BACKUP=backups/postgres/instock_YYYYmmdd_HHMMSS.dump
make staging-up
```

The restore command stops staging `app` and `frontend`, drops and recreates only
the staging database, then restores the dump into staging PostgreSQL.

## Backup Policy

For this project stage, keep a simple scheduled custom-format dump:

```cron
15 2 * * * cd /path/to/instock_fastapi && make backup-prod-db >> logs/backup_prod_db.log 2>&1
```

Use `RETENTION_DAYS=14` by default for local/server snapshots. For a real
production deployment, prefer managed database backups with point-in-time
recovery in addition to these logical dumps.

Do not restore raw production data into shared staging environments if the data
contains user-sensitive fields. Add a sanitization step before wider team use.
