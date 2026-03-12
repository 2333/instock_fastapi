#!/bin/bash

set -euo pipefail

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:3001}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-120}"
SLEEP_SECONDS="${SLEEP_SECONDS:-3}"

wait_for_json_field() {
    local name="$1"
    local url="$2"
    local expected="$3"
    local waited=0

    while [ "$waited" -lt "$TIMEOUT_SECONDS" ]; do
        local body
        if body="$(curl -fsS "$url" 2>/dev/null)"; then
            if printf '%s' "$body" | grep -q "$expected"; then
                echo "[ok] $name: $url"
                return 0
            fi
        fi

        sleep "$SLEEP_SECONDS"
        waited=$((waited + SLEEP_SECONDS))
    done

    echo "[error] $name did not become ready: $url"
    return 1
}

wait_for_http_200() {
    local name="$1"
    local url="$2"
    local waited=0

    while [ "$waited" -lt "$TIMEOUT_SECONDS" ]; do
        if curl -fsS "$url" >/dev/null 2>&1; then
            echo "[ok] $name: $url"
            return 0
        fi

        sleep "$SLEEP_SECONDS"
        waited=$((waited + SLEEP_SECONDS))
    done

    echo "[error] $name did not become ready: $url"
    return 1
}

wait_for_json_field "backend health" "$BACKEND_URL/health" '"status":"healthy"'
wait_for_json_field "backend info" "$BACKEND_URL/api/v1/info" '"name":"InStock API"'
wait_for_http_200 "frontend home" "$FRONTEND_URL/"

echo "[ok] docker smoke test passed"
