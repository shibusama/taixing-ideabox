"""SQLite data layer via SQLAlchemy (sync engine).

DB file: ideabox.db (fixed name). The backend process owns it; because this
environment's safe-delete wrapper can block *file deletion* (not writes),
we never delete/replace the db file — we only write rows inside it.
"""

import pathlib

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

BASE_DIR = pathlib.Path(__file__).parent
DB_PATH = BASE_DIR / "ideabox.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)


def _on_connect(dbapi_conn, _record):
    """WAL mode + busy timeout: allow concurrent readers/writers."""
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA busy_timeout=5000")
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


from sqlalchemy import event  # noqa: E402

event.listen(engine, "connect", _on_connect)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def init_db():
    """Create all tables (idempotent)."""
    import models  # noqa: F401 - register models on Base.metadata

    Base.metadata.create_all(bind=engine)
