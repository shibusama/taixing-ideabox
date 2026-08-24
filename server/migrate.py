#!/usr/bin/env python3
"""智能数据库迁移入口（Coze 部署 / 本地通用）—— 全自动建表。

设计目标：开发者改完 models.py 新增表后，只需 commit + push，
部署/预览启动时自动把缺失的表建出来，无需手动生成迁移或建表 SQL。

每次启动统一执行：
  1) Base.metadata.create_all(checkfirst=True)
     —— 自动建"models 里有、数据库里没有"的所有表（幂等，不动已有表/数据）。
        新表（如新功能模块的表）部署即自动生效。
  2) Alembic 版本处理（处理历史迁移链，避免与旧库冲突）：
     - 全新空库            -> alembic upgrade head（建全部表 + 版本链）
     - 旧库(有表无版本标记)  -> alembic stamp head（打版本标记，不重复 DDL）
     - 已有版本标记         -> alembic upgrade head（幂等演进，执行新迁移）

说明：
  - "新增整张新表" 100% 自动，无需手动步骤。
  - "修改已有表结构（加列/改字段）" 仍需 alembic 迁移文件（业界标准安全设计）。

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
import models  # noqa: E402,F401   # 必须 import，让 Base.metadata 含全部表
from sqlalchemy import create_engine, inspect  # noqa: E402

# 业务表集合（用于识别"非空库"）
BIZ_TABLES = {"ideas", "tags", "mindmaps", "covers", "tasks",
              "plans", "plan_nodes", "plan_logs"}


def _get_url() -> str:
    # 可选显式覆盖（测试/特殊场景），默认复用 db.py 的自动降级逻辑
    override = os.environ.get("IDEA_MIGRATE_URL")
    if override:
        return override
    if DATABASE_URL:
        return DATABASE_URL
    return f"sqlite:///{SERVER_DIR / 'ideabox.db'}"


def _alembic(*args, url=None):
    """调用 alembic 模块（不带 shell）。url 非空时同步给 ALEMBIC_URL，
    保证 alembic 与 create_all 连到同一个库（env.py 优先读 ALEMBIC_URL）。"""
    cmd = [sys.executable, "-m", "alembic"] + list(args)
    print("[migrate] run:", " ".join(cmd))
    env = dict(os.environ)
    if url:
        env["ALEMBIC_URL"] = url
    subprocess.run(cmd, env=env, check=True)


def main() -> int:
    url = _get_url()
    engine = create_engine(url)

    # 1) 自动补齐缺失表（新表部署即自动建；幂等，不影响已有表/数据）
    try:
        missing = sorted(
            name for name in Base.metadata.tables
        )
        existing = set(inspect(engine).get_table_names())
        to_create = [n for n in missing if n not in existing]
        if to_create:
            print(f"[migrate] 自动创建缺失表: {to_create}")
            Base.metadata.create_all(bind=engine, checkfirst=True)
        else:
            print("[migrate] 表结构已是最新，无需新建表")
    except Exception as exc:
        # 建表失败不掩盖真实错误：打印后交给 alembic 尝试（它会给出更明确信息）
        print(f"[migrate] create_all 异常: {exc}", file=sys.stderr)

    # 2) Alembic 版本处理（历史迁移链 / 旧库兼容）
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    has_business = bool(tables & BIZ_TABLES)
    has_version = "alembic_version" in tables

    if not has_business:
        print("[migrate] 空库 -> alembic upgrade head（建全部表 + 版本链）")
        _alembic("upgrade", "head", url=url)
    elif not has_version:
        print("[migrate] 旧库（有表但无 alembic_version）-> stamp head")
        _alembic("stamp", "head", url=url)
    else:
        print("[migrate] 已有版本标记 -> alembic upgrade head（幂等演进）")
        _alembic("upgrade", "head", url=url)
    return 0


if __name__ == "__main__":
    sys.exit(main())