"""Alembic 迁移环境。

复用服务端 db.py 的数据库连接逻辑：
- 设了 PGDATABASE_URL → 连 PostgreSQL
- 没有 → 连本地 SQLite（server/ideabox.db）
这正是"本地 SQLite / 云端 Postgres / 自动降级"的统一机制。
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# 让本文件所在目录（server/）可被 import，以便 `import db / import models`
SERVER_DIR = Path(__file__).resolve().parent.parent
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

# 必须 import 模型，让 Base.metadata 包含全部表（含 plans 三表）
from db import Base  # noqa: E402
import models  # noqa: E402,F401  (确保模型注册到 metadata)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 关键：把连接串交给 Alembic。优先级：显式 ALEMBIC_URL 环境变量 > db 模块逻辑。
import os as _os
from db import DATABASE_URL  # noqa: E402

_override = _os.environ.get("ALEMBIC_URL")
if _override:
    config.set_main_option("sqlalchemy.url", _override)
elif DATABASE_URL:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)
else:
    # SQLite 默认路径（与 server/db.py 保持一致）
    sqlite_path = str(SERVER_DIR / "ideabox.db")
    config.set_main_option(
        "sqlalchemy.url", f"sqlite:///{sqlite_path}"
    )

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 但不连接数据库。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：直接对数据库执行迁移。"""
    configuration = config.get_section(config.config_ini_section, {})
    if DATABASE_URL is None:
        # SQLite：支持 batch 模式以处理 ALTER 的兼容
        configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
