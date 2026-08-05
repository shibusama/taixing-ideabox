#!/bin/bash
set -e
cd "$(dirname "$0")"

# Python 后端依赖
echo "=== Installing Python dependencies ==="
cd server
pip install -r requirements.txt -q 2>&1
cd ..

# 前端依赖 + 构建
echo "=== Installing frontend dependencies ==="
pnpm install 2>&1

echo "=== Building frontend ==="
pnpm run build 2>&1

echo "=== Build complete ==="