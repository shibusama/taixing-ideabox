#!/bin/bash
set -e
cd "$(dirname "$0")"
echo "[start.sh] PWD=$(pwd)" >&2
echo "[start.sh] Python=$(python3 --version 2>&1)" >&2
echo "[start.sh] PGDATABASE_URL=${PGDATABASE_URL:+SET}" >&2
# Test import before running uvicorn
python3 -c "
import sys
print('[start.sh] sys.path:', sys.path, file=sys.stderr)
try:
    import app
    print('[start.sh] app imported OK', file=sys.stderr)
except Exception as e:
    import traceback
    print('[start.sh] IMPORT ERROR:', file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
" 2>&1
exec python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}