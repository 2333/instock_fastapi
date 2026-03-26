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
export APP_VERSION="$VERSION"
export IMAGE_NAMESPACE
export APP_GIT_SHA
export ENV_FILE

echo "Deploying ${IMAGE_NAMESPACE} release ${APP_VERSION} with docker-compose.deploy.yml"
docker compose -f docker-compose.deploy.yml up -d
docker compose -f docker-compose.deploy.yml ps
