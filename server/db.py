"""
Database connection and session management.

Uses PostgreSQL (Supabase) in production, SQLite in local development.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Load server/.env if present (never overrides real env vars).
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))

# Database URL from environment (PostgreSQL) or fallback to SQLite for local dev
DATABASE_URL = os.environ.get("PGDATABASE_URL")

if DATABASE_URL:
    # Production: PostgreSQL (Supabase)
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
    )
else:
    # Local development: SQLite
    DB_PATH = Path(__file__).parent / "ideabox.db"
    engine = create_engine(
        f"sqlite:///{DB_PATH}",
        connect_args={"check_same_thread": False},
    )
    # SQLite WAL mode for better concurrent read performance
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def init_db():
    """Create tables if they don't exist (SQLite only; Supabase tables are created manually)."""
    if not DATABASE_URL:
        Base.metadata.create_all(bind=engine)
