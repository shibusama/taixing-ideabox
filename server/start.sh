#!/bin/bash
set -e
cd "$(dirname "$0")"
python -m uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT:-5000}