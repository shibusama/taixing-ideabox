#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
echo "[start.sh] PWD=$(pwd)" >&2
echo "[start.sh] Python=$(python3 --version 2>&1)" >&2
echo "[start.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
echo "[start.sh] WORK_ROOT=${WORK_ROOT}" >&2

# Auto-migrate DB schema: alembic upgrade head (idempotent)
# - PGDATABASE_URL set -> migrate PostgreSQL
# - not set -> migrate local SQLite. No manual DDL needed.
echo "[start.sh] alembic upgrade head ..." >&2
python -m alembic upgrade head

exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}