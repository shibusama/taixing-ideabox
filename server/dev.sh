#!/bin/bash
set -e
cd "$(dirname "$0")"
export WORK_ROOT="${WORK_ROOT:-/tmp/ideabox/work}"
mkdir -p "$WORK_ROOT"

echo "[dev.sh] starting backend on :8000" >&2
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
echo "[dev.sh] backend pid=$BACKEND_PID" >&2

# 给后端一点启动时间，避免前端首屏请求落空
sleep 2

echo "[dev.sh] starting vite (frontend)" >&2
cd ..
exec pnpm run dev
