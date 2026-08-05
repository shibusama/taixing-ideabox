#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Installing frontend dependencies ==="
pnpm install 2>&1

echo "=== Building frontend ==="
pnpm run build 2>&1

echo "=== Build complete ==="