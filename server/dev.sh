#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
mkdir -p "$WORK_ROOT"
echo "[dev.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
echo "[dev.sh] WORK_ROOT=${WORK_ROOT}" >&2
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

# Auto-migrate DB schema (parity with deploy): alembic upgrade head
# - PGDATABASE_URL set -> migrate PostgreSQL
# - not set -> migrate local SQLite. No manual DDL needed.
echo "[dev.sh] alembic upgrade head ..." >&2
python -m alembic upgrade head

exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}
