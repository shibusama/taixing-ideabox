#!/bin/bash
set -e
cd "$(dirname "$0")"

PORT="${DEPLOY_RUN_PORT:-5000}"
echo "=== Starting IdeaBox server on port ${PORT} ==="

exec node server.cjs