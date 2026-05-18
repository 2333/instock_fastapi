#!/bin/sh
set -eu

VERSION="${1:-${VERSION:-${APP_VERSION:-}}}"
if [ -z "$VERSION" ]; then
  echo "Usage: VERSION=0.2.0 sh scripts/deploy_release.sh" >&2
  exit 1
fi

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Python runtime for release tooling was not found: $PYTHON_BIN" >&2
  exit 1
fi

CURRENT_VERSION="$("$PYTHON_BIN" scripts/release_version.py check)"
if [ "$VERSION" != "$CURRENT_VERSION" ]; then
  echo "VERSION=$VERSION does not match repository version $CURRENT_VERSION. Run scripts/release_version.py set $VERSION first." >&2
  exit 1
fi

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-instock}"
APP_GIT_SHA="${APP_GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
ENV_FILE="${ENV_FILE:-.env}"
DEPLOY_COMPOSE_FILE="${DEPLOY_COMPOSE_FILE:-docker-compose.deploy.yml}"
PRE_M3_RELEASE_CLASS="${PRE_M3_RELEASE_CLASS:-}"
PRE_M3_APPLY_DB_UPGRADE="${PRE_M3_APPLY_DB_UPGRADE:-0}"
POSTDEPLOY_SMOKE="${POSTDEPLOY_SMOKE:-1}"
export APP_VERSION="$VERSION"
export IMAGE_NAMESPACE
export APP_GIT_SHA
export ENV_FILE

echo "Deploying ${IMAGE_NAMESPACE} release ${APP_VERSION} with ${DEPLOY_COMPOSE_FILE}"

if [ -z "$PRE_M3_RELEASE_CLASS" ]; then
  echo "Set PRE_M3_RELEASE_CLASS=non_schema or PRE_M3_RELEASE_CLASS=schema_contract before deploy." >&2
  exit 1
fi

PRECHECK_ARGS="--release-class ${PRE_M3_RELEASE_CLASS}"
if [ "$PRE_M3_APPLY_DB_UPGRADE" = "1" ]; then
  PRECHECK_ARGS="${PRECHECK_ARGS} --apply-db-upgrade"
fi

"$PYTHON_BIN" scripts/release_precheck.py ${PRECHECK_ARGS} --env-file "${ENV_FILE}"

if ! docker network inspect instock_network >/dev/null 2>&1; then
  echo "Required external network instock_network was not found." >&2
  echo "Start or restore the production database container before deploying the app stack." >&2
  exit 1
fi

docker compose -f "$DEPLOY_COMPOSE_FILE" up -d --force-recreate --remove-orphans
docker compose -f "$DEPLOY_COMPOSE_FILE" ps

if [ "$POSTDEPLOY_SMOKE" = "1" ]; then
  BACKEND_URL="${BACKEND_URL:-http://localhost:8000}" \
  FRONTEND_URL="${FRONTEND_URL:-http://localhost:3001}" \
  ./scripts/docker_smoke.sh
fi

if [ "$PRE_M3_RELEASE_CLASS" = "schema_contract" ]; then
  "$PYTHON_BIN" scripts/release_precheck.py --release-class schema_contract --env-file "${ENV_FILE}"
fi
