#!/bin/sh
set -eu

cat <<'EOF'
scripts/start.sh has been retired.

This project now uses an explicit environment model:
  - make dev-up        for the long-lived development stack
  - make prod-deploy-version VERSION=x.y.z
                       for production app/frontend deployment
  - make staging-up    for temporary staging verification only

The old default docker-compose.yml main-stack workflow was removed to avoid
accidental production-like startups from ambiguous commands.
EOF

exit 1
