"""Create tables in PostgreSQL/Supabase from the SQLAlchemy models.

Usage:
    cd server
    PGDATABASE_URL="postgresql://user:pass@host:5432/dbname" python create_tables.py

Note:
    - This project does NOT auto-create tables on PostgreSQL (init_db() only
      runs create_all for SQLite). Run this once against a new PG database.
    - Table columns follow the ORM models: timestamps are DOUBLE PRECISION
      (epoch ms, matching the frontend), tags is JSONB.
"""

import os

# Import models FIRST so their tables are registered on Base.metadata.
import db
from models import Idea, Mindmap, Tag, Task  # noqa: F401

if not os.environ.get("PGDATABASE_URL"):
    raise SystemExit(
        "PGDATABASE_URL is not set. This script is only for PostgreSQL/Supabase; "
        "local SQLite auto-creates its own tables."
    )

print("Creating tables on:", db.DATABASE_URL.split("@")[-1].split("/")[-1])
db.Base.metadata.create_all(bind=db.engine)
print("Done. Tables:", sorted(db.Base.metadata.tables))
