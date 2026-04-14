#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
PROD_COMPOSE_FILE="${PROD_COMPOSE_FILE:-docker-compose.yml}"
PROD_PROJECT="${PROD_PROJECT:-}"
PROD_DB_SERVICE="${PROD_DB_SERVICE:-postgres}"
POSTGRES_DB_NAME="${POSTGRES_DB:-instock}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="${BACKUP_DIR}/${POSTGRES_DB_NAME}_${timestamp}.dump"

mkdir -p "$BACKUP_DIR"

if [ -n "$PROD_PROJECT" ]; then
  compose_cmd="docker compose -p $PROD_PROJECT -f $PROD_COMPOSE_FILE"
else
  compose_cmd="docker compose -f $PROD_COMPOSE_FILE"
fi

echo "Creating PostgreSQL backup: $backup_file"
# Custom format keeps restore flexible and works well with pg_restore.
$compose_cmd exec -T "$PROD_DB_SERVICE" sh -lc \
  'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$backup_file"

if [ "${RETENTION_DAYS}" -gt 0 ] 2>/dev/null; then
  find "$BACKUP_DIR" -name "${POSTGRES_DB_NAME}_*.dump" -type f -mtime +"$RETENTION_DAYS" -delete
fi

echo "Backup complete: $backup_file"
