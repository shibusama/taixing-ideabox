#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
echo "[start.sh] PWD=$(pwd)" >&2
echo "[start.sh] Python=$(python3 --version 2>&1)" >&2
echo "[start.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
echo "[start.sh] WORK_ROOT=${WORK_ROOT}" >&2

# Auto-migrate DB schema (idempotent, smart): server/migrate.py
# - new/empty db       -> alembic upgrade head (create all tables)
# - existing tables but no alembic_version -> alembic stamp head (no duplicate DDL)
# - PGDATABASE_URL set -> PostgreSQL; else -> local SQLite.
echo "[start.sh] migrate ..." >&2
python -m migrate

exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}