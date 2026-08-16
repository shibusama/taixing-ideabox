"""Utility functions for IdeaBox."""

import hashlib
import json
import sys
import time
import uuid
from datetime import datetime

from db import SessionLocal
from models import Idea, Mindmap, Tag, Task

from config import BASE_DIR


def _now_ms() -> float:
    return time.time() * 1000


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def cache_key(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


def _rebuild_tags(db):
    """Recompute tag counts from all non-deleted ideas."""
    counts = {}
    for idea in db.query(Idea).filter(Idea.deleted_at.is_(None)).all():
        for tag in (idea.tags or []):
            counts[tag] = counts.get(tag, 0) + 1
    db.query(Tag).delete()
    db.add_all([Tag(name=n, count=c) for n, c in counts.items()])


def _migrate_legacy_data():
    """One-time rescue: if the current DB is empty, import from a legacy backup.

    Kept for safety only — normal operation uses the fixed ideabox.db.
    Candidates are the historical DB files (v3/v2/backup) in order of recency.
    """
    # Only migrate when the current DB has no data yet.
    with SessionLocal() as db:
        has_data = db.query(Idea).count() > 0 or db.query(Mindmap).count() > 0
    if has_data:
        return

    legacy_names = ["ideabox_v3.db", "ideabox_v2.db", "ideabox_backup.db"]
    for name in legacy_names:
        legacy = BASE_DIR / name
        if not legacy.exists():
            continue
        try:
            src = __import__("sqlite3").connect(str(legacy))
            src.row_factory = __import__("sqlite3").Row
        except Exception:
            continue

        def as_dt(value):
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

        with SessionLocal() as db:
            try:
                for row in src.execute("SELECT * FROM ideas"):
                    db.add(Idea(
                        id=row["id"],
                        content=row["content"],
                        tags=json.loads(row["tags"]) if row["tags"] else [],
                        pinned=row["pinned"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                        deleted_at=row["deleted_at"],
                    ))
                for row in src.execute("SELECT * FROM tags"):
                    db.add(Tag(id=row["id"], name=row["name"], count=row["count"]))
                for row in src.execute("SELECT * FROM mindmaps"):
                    db.add(Mindmap(
                        id=row["id"],
                        url_hash=row["url_hash"],
                        url=row["url"],
                        mindmap_md=row["mindmap_md"],
                        created_at=as_dt(row["created_at"]),
                    ))
                for row in src.execute("SELECT * FROM tasks"):
                    db.add(Task(
                        task_id=row["task_id"],
                        url=row["url"],
                        status=row["status"],
                        result=json.loads(row["result"]) if row["result"] else None,
                        error=row["error"],
                        created_at=as_dt(row["created_at"]),
                    ))
                db.commit()
            except Exception as exc:
                print(f"[migrate] failed from {name}: {exc}", file=sys.stderr)
                db.rollback()
            finally:
                src.close()
        print(f"[migrate] copied data from {name}", file=sys.stderr)
        return

def _read_optional(path) -> str:
    """Read file content if exists, else empty string."""
    import pathlib
    p = pathlib.Path(path)
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _load_legacy_cache(url_hash: str) -> dict | None:
    """Check legacy JSON cache files for a cached result."""
    import json
    from config import LEGACY_CACHE_DIR
    legacy = LEGACY_CACHE_DIR / f"{url_hash}.json"
    if legacy.exists():
        try:
            data = json.loads(legacy.read_text(encoding="utf-8"))
            return {"id": url_hash, "cached": True, "mindmap_md": data.get("mindmap_md", "")}
        except Exception:
            pass
    return None
