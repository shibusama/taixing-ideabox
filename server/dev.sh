#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
mkdir -p "$WORK_ROOT"
echo "[dev.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
echo "[dev.sh] WORK_ROOT=${WORK_ROOT}" >&2
exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}
