#!/bin/bash
# 本地统一开发启动脚本：单进程同源托管前后端（与生产部署一致）
# 用法：sh start-dev.sh [port]   默认端口 8000
set -e
cd "$(dirname "$0")"

PORT="${1:-8000}"

# 前端依赖（仓库统一用 pnpm，缺失则提示，不静默回退 npm 以免破坏 lock 文件）
if ! command -v pnpm >/dev/null 2>&1; then
  echo "[start-dev] 未找到 pnpm。请先安装：npm install -g pnpm"
  exit 1
fi
if [ ! -d node_modules ]; then
  echo "[start-dev] 安装前端依赖 (pnpm install)..."
  pnpm install
fi

# 后端依赖
python - <<'EOF'
import importlib.util
missing = [m for m in ("fastapi", "uvicorn", "sqlalchemy") if importlib.util.find_spec(m) is None]
if missing:
    raise SystemExit(f"missing: {missing}")
EOF
if [ $? -ne 0 ]; then
  echo "[start-dev] 安装后端依赖 (pip install -r server/requirements.txt)..."
  python -m pip install -r server/requirements.txt
fi

# 前端构建产物（后端托管静态文件必需）
if [ ! -d dist ]; then
  echo "[start-dev] 构建前端 (pnpm run build)..."
  pnpm run build
fi

echo "[start-dev] 单进程启动：http://localhost:${PORT}  (前端 + /api 同源)"
cd server
exec python -m uvicorn app:app --host 127.0.0.1 --port "${PORT}" --reload
