#!/bin/sh
set -eu

VERSION="${1:-${VERSION:-${APP_VERSION:-}}}"
if [ -z "$VERSION" ]; then
  echo "Usage: VERSION=0.2.0 sh scripts/deploy_release.sh" >&2
  exit 1
fi

CURRENT_VERSION="$(python3 scripts/release_version.py check)"
if [ "$VERSION" != "$CURRENT_VERSION" ]; then
  echo "VERSION=$VERSION does not match repository version $CURRENT_VERSION. Run scripts/release_version.py set $VERSION first." >&2
  exit 1
fi

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-instock}"
APP_GIT_SHA="${APP_GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
ENV_FILE="${ENV_FILE:-.env}"
DEPLOY_COMPOSE_FILE="${DEPLOY_COMPOSE_FILE:-docker-compose.deploy.yml}"
export APP_VERSION="$VERSION"
export IMAGE_NAMESPACE
export APP_GIT_SHA
export ENV_FILE

echo "Deploying ${IMAGE_NAMESPACE} release ${APP_VERSION} with ${DEPLOY_COMPOSE_FILE}"

if ! docker network inspect instock_network >/dev/null 2>&1; then
  echo "Required external network instock_network was not found." >&2
  echo "Start or restore the production database container before deploying the app stack." >&2
  exit 1
fi

for container in instock_app instock_frontend; do
  if docker inspect "$container" >/dev/null 2>&1; then
    echo "Removing existing container: $container"
    docker rm -f "$container" >/dev/null
  fi
done

docker compose -f "$DEPLOY_COMPOSE_FILE" up -d --force-recreate --remove-orphans
docker compose -f "$DEPLOY_COMPOSE_FILE" ps
