#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 path/to/backup.dump" >&2
  exit 2
fi

BACKUP_FILE="$1"
STAGING_COMPOSE_FILE="${STAGING_COMPOSE_FILE:-docker-compose.staging.yml}"
STAGING_PROJECT="${STAGING_PROJECT:-instock_staging}"
STAGING_DB_SERVICE="${STAGING_DB_SERVICE:-postgres}"
STAGING_POSTGRES_DB="${STAGING_POSTGRES_DB:-instock}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 2
fi

compose_cmd="docker compose -p $STAGING_PROJECT -f $STAGING_COMPOSE_FILE"

echo "Starting staging PostgreSQL..."
$compose_cmd up -d "$STAGING_DB_SERVICE"

echo "Stopping staging app/frontend before restore..."
$compose_cmd stop app frontend >/dev/null 2>&1 || true

echo "Dropping and recreating staging database: $STAGING_POSTGRES_DB"
$compose_cmd exec -T "$STAGING_DB_SERVICE" sh -lc \
  'dropdb -U "$POSTGRES_USER" --if-exists --force "$POSTGRES_DB"'
$compose_cmd exec -T "$STAGING_DB_SERVICE" sh -lc \
  'createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'

echo "Restoring backup into staging database..."
$compose_cmd exec -T "$STAGING_DB_SERVICE" sh -lc \
  'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner --no-acl' < "$BACKUP_FILE"

echo "Restore complete. Start staging with: make staging-up"
