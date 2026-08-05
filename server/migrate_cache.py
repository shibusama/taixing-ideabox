"""One-off migration: import legacy cache/*.json entries into the mindmaps table.

Usage: .venv/Scripts/python.exe migrate_cache.py
Safe to re-run (skips hashes already in DB).
"""

import json
import pathlib

from db import SessionLocal
from models import Mindmap

CACHE_DIR = pathlib.Path(__file__).parent / "cache"


def main():
    imported = skipped = 0
    with SessionLocal() as db:
        existing = {m.url_hash for m in db.query(Mindmap).all()}
        for f in sorted(CACHE_DIR.glob("*.json")):
            url_hash = f.stem
            if url_hash in existing:
                skipped += 1
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as exc:
                print(f"SKIP {f.name}: {exc}")
                continue
            md = data.get("mindmap_md")
            if not md:
                print(f"SKIP {f.name}: no mindmap_md")
                skipped += 1
                continue
            db.add(
                Mindmap(
                    url_hash=url_hash,
                    url=data.get("url") or f"legacy://{url_hash}",
                    mindmap_md=md,
                )
            )
            imported += 1
        db.commit()
    print(f"imported={imported} skipped={skipped}")


if __name__ == "__main__":
    main()
