#!/bin/sh
set -eu

VERSION="${1:-${VERSION:-${APP_VERSION:-}}}"
if [ -z "$VERSION" ]; then
  echo "Usage: VERSION=0.2.0 sh scripts/build_release_images.sh" >&2
  exit 1
fi

CURRENT_VERSION="$(python3 scripts/release_version.py check)"
if [ "$VERSION" != "$CURRENT_VERSION" ]; then
  echo "VERSION=$VERSION does not match repository version $CURRENT_VERSION. Run scripts/release_version.py set $VERSION first." >&2
  exit 1
fi

IMAGE_NAMESPACE="${IMAGE_NAMESPACE:-instock}"
APP_GIT_SHA="${APP_GIT_SHA:-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
export APP_VERSION="$VERSION"
export IMAGE_NAMESPACE
export APP_GIT_SHA

echo "Building versioned images..."
echo "  ${IMAGE_NAMESPACE}/instock-app:${APP_VERSION}"
echo "  ${IMAGE_NAMESPACE}/instock-frontend:${APP_VERSION}"

docker build \
  --build-arg APP_VERSION="$APP_VERSION" \
  --build-arg APP_GIT_SHA="$APP_GIT_SHA" \
  -t "${IMAGE_NAMESPACE}/instock-app:${APP_VERSION}" \
  .

docker build \
  -f web/Dockerfile \
  --build-arg APP_VERSION="$APP_VERSION" \
  --build-arg APP_GIT_SHA="$APP_GIT_SHA" \
  -t "${IMAGE_NAMESPACE}/instock-frontend:${APP_VERSION}" \
  ./web
