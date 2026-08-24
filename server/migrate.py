#!/usr/bin/env python3
"""智能数据库迁移入口（Coze 部署 / 本地通用）。

在跑 alembic 前根据数据库现状自动决定策略，避免两类坑：
  A. 库已有表但无 alembic_version（旧库/手动建过的库）
     -> 重复 upgrade 会报 DuplicateTable（如 relation "covers" already exists）
  B. 旧库缺新增的表（如计划模块 plans/plan_nodes/plan_logs）
     -> 只 stamp 会丢这些表

策略：
  - 全新空库（无任何业务表）          -> alembic upgrade head（自动建全部表）
  - 旧库（有业务表但无 alembic_version）
      -> 1) Base.metadata.create_all(checkfirst=True) 只补齐缺失的表（如 plans 三表）
      -> 2) alembic stamp head  标记已最新（跳过对已存在表的重复 DDL）
  - 已有 alembic_version            -> alembic upgrade head（幂等演进）

连接串与 server/db.py 完全一致（自动降级）：
  PGDATABASE_URL 设了 -> PostgreSQL；否则 -> 本地 SQLite。
"""

import os
import subprocess
import sys
from pathlib import Path

# 确保 server/ 可被 import（复用 db.py 的连接逻辑）
SERVER_DIR = Path(__file__).resolve().parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from db import DATABASE_URL, Base  # noqa: E402
import models  # noqa: E402,F401   # 必须 import，让 Base.metadata 含全部表（含 plans 三表）
from sqlalchemy import create_engine, inspect  # noqa: E402

# 业务表集合（用于判断"是否已有数据")
BIZ_TABLES = {"ideas", "tags", "mindmaps", "covers", "tasks",
              "plans", "plan_nodes", "plan_logs"}


def _get_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL
    return f"sqlite:///{SERVER_DIR / 'ideabox.db'}"


def _alembic(*args):
    """调用 alembic 模块（不带 shell）。"""
    cmd = [sys.executable, "-m", "alembic"] + list(args)
    print("[migrate] run:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> int:
    url = _get_url()
    engine = create_engine(url)
    insp = inspect(engine)
    try:
        tables = set(insp.get_table_names())
    except Exception as exc:
        print(f"[migrate] 无法连接数据库: {exc}", file=sys.stderr)
        # 连不上时把真实连接错误暴露出来
        _alembic("upgrade", "head")
        return 0

    has_business = bool(tables & BIZ_TABLES)
    has_version = "alembic_version" in tables

    if not has_business:
        # 全新空库 -> 建全部表
        print("[migrate] 空库 -> upgrade head（自动建全部表）")
        _alembic("upgrade", "head")
    elif not has_version:
        # 旧库：有表但无 alembic_version
        print("[migrate] 旧库（有表但无 alembic_version）")
        missing = sorted(
            name for name in Base.metadata.tables if name not in tables
        )
        if missing:
            print(f"[migrate] 补齐缺失表: {missing}（create_all checkfirst）")
            Base.metadata.create_all(bind=engine, checkfirst=True)
            # 补完后重新读取表集合并确认
            tables = set(insp.get_table_names())
            still_missing = [n for n in missing if n not in tables]
            if still_missing:
                print(f"[migrate] 仍有表未建成: {still_missing}")
        print("[migrate] stamp head（标记版本，跳过对已存在表的重复 DDL）")
        _alembic("stamp", "head")
    else:
        # 正常版本化库 -> 幂等演进（含新迁移）
        print("[migrate] upgrade head（幂等演进）")
        _alembic("upgrade", "head")
    return 0


if __name__ == "__main__":
    sys.exit(main())
