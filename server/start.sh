#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
echo "[start.sh] PWD=$(pwd)" >&2
echo "[start.sh] Python=$(python3 --version 2>&1)" >&2
echo "[start.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
echo "[start.sh] WORK_ROOT=${WORK_ROOT}" >&2

# 数据库自动迁移：把数据库升到最新表结构（自动建表/改表，幂等）
# - 设了 PGDATABASE_URL -> 迁移 PostgreSQL
# - 没设 -> 迁移本地 SQLite。无需手动执行建表 SQL。
echo "[start.sh] alembic upgrade head ..." >&2
python -m alembic upgrade head

exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}