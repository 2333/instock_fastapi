#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-backups/postgres}"
PROD_COMPOSE_FILE="${PROD_COMPOSE_FILE:-}"
PROD_PROJECT="${PROD_PROJECT:-}"
PROD_DB_SERVICE="${PROD_DB_SERVICE:-postgres}"
PROD_DB_CONTAINER="${PROD_DB_CONTAINER:-instock_postgres}"
POSTGRES_DB_NAME="${POSTGRES_DB_NAME:-${POSTGRES_DB:-instock}}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

timestamp="$(date +%Y%m%d_%H%M%S)"
backup_file="${BACKUP_DIR}/${POSTGRES_DB_NAME}_${timestamp}.dump"

mkdir -p "$BACKUP_DIR"

echo "Creating PostgreSQL backup: $backup_file"

if docker inspect "$PROD_DB_CONTAINER" >/dev/null 2>&1; then
  echo "Using running container: $PROD_DB_CONTAINER"
  docker exec "$PROD_DB_CONTAINER" sh -lc \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$backup_file"
else
  if [ -z "$PROD_COMPOSE_FILE" ]; then
    echo "Container $PROD_DB_CONTAINER not found and no fallback compose file was provided." >&2
    echo "Set PROD_DB_CONTAINER to the running production database container, or provide PROD_COMPOSE_FILE and PROD_DB_SERVICE." >&2
    exit 1
  fi

  if [ -n "$PROD_PROJECT" ]; then
    compose_cmd="docker compose -p $PROD_PROJECT -f $PROD_COMPOSE_FILE"
  else
    compose_cmd="docker compose -f $PROD_COMPOSE_FILE"
  fi

  echo "Container $PROD_DB_CONTAINER not found, falling back to compose service $PROD_DB_SERVICE"
  # Custom format keeps restore flexible and works well with pg_restore.
  $compose_cmd exec -T "$PROD_DB_SERVICE" sh -lc \
    'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-acl' > "$backup_file"
fi

if [ "${RETENTION_DAYS}" -gt 0 ] 2>/dev/null; then
  find "$BACKUP_DIR" -name "${POSTGRES_DB_NAME}_*.dump" -type f -mtime +"$RETENTION_DAYS" -delete
fi

echo "Backup complete: $backup_file"
