"""Copy all data from the old (locked/readonly) ideabox.db into the new ideabox_v2.db.

Reads from old file with raw sqlite3 (read-only access always works),
writes into the new file via the app's SQLAlchemy session (new file = writable).

Usage: .venv/Scripts/python.exe migrate_db.py
"""

import json
import sqlite3
import pathlib
from datetime import datetime

from db import SessionLocal, init_db
from models import Idea, Mindmap, Tag, Task

BASE_DIR = pathlib.Path(__file__).parent
OLD_DB = BASE_DIR / "ideabox.db"
NEW_DB = BASE_DIR / "ideabox_v2.db"


def _as_dt(value):
    """Convert sqlite string/float to datetime; None passes through."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value)
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.now()


def main():
    if not OLD_DB.exists():
        print(f"no old db at {OLD_DB}")
        return
    src = sqlite3.connect(str(OLD_DB))
    src.row_factory = sqlite3.Row

    init_db()  # create tables in the new db file

    with SessionLocal() as db:
        # ideas
        for row in src.execute("SELECT * FROM ideas"):
            db.add(
                Idea(
                    id=row["id"],
                    content=row["content"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    pinned=row["pinned"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    deleted_at=row["deleted_at"],
                )
            )
        print(f"ideas: {db.query(Idea).count()}")

        # tags
        for row in src.execute("SELECT * FROM tags"):
            db.add(Tag(id=row["id"], name=row["name"], count=row["count"]))
        print(f"tags: {db.query(Tag).count()}")

        # mindmaps
        for row in src.execute("SELECT * FROM mindmaps"):
            db.add(
                Mindmap(
                    id=row["id"],
                    url_hash=row["url_hash"],
                    url=row["url"],
                    mindmap_md=row["mindmap_md"],
                    created_at=_as_dt(row["created_at"]),
                )
            )
        print(f"mindmaps: {db.query(Mindmap).count()}")

        # tasks
        for row in src.execute("SELECT * FROM tasks"):
            db.add(
                Task(
                    task_id=row["task_id"],
                    url=row["url"],
                    status=row["status"],
                    result=json.loads(row["result"]) if row["result"] else None,
                    error=row["error"],
                    created_at=_as_dt(row["created_at"]),
                )
            )
        print(f"tasks: {db.query(Task).count()}")

        db.commit()

    src.close()
    print("\nmigration complete ->", NEW_DB.name)


if __name__ == "__main__":
    main()
