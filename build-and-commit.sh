#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Building frontend ==="
pnpm run build

echo "=== Staging dist/ ==="
git add dist/

echo "=== Committing ==="
git commit -m "update frontend dist build"

echo "=== Done! Run 'git push' to deploy ==="