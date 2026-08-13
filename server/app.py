"""IdeaBox FastAPI entry point."""

import os
import pathlib
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import llm
from config import _executor, _KINDS, _CACHE_GETTERS, _CACHE_TABLES
from cover import run_cover_task
from db import init_db, SessionLocal
from helpers import _migrate_legacy_data, _now_ms
from models import Task
from routers import admin, ideas, video

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI()

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # 1. Ensure DB tables exist
    init_db()

    # 2. Legacy data migration (one-shot)
    _migrate_legacy_data()

    # 3. Mark interrupted tasks as error
    with SessionLocal() as db:
        interrupted = db.query(Task).filter(Task.status == "running").all()
        for task in interrupted:
            task.status = "error"
            task.error = "Server restarted while task was running"
            task.updated_at = _now_ms()
        db.commit()

    # 4. Start background cleanup thread (delete tasks older than 7 days)
    def _cleanup_loop():
        while True:
            try:
                cutoff = _now_ms() - 7 * 24 * 60 * 60 * 1000
                with SessionLocal() as db:
                    deleted = db.query(Task).filter(Task.created_at < cutoff).delete()
                    db.commit()
            except Exception:
                pass
            threading.Event().wait(3600)

    threading.Thread(target=_cleanup_loop, daemon=True, start=True)

    yield


app = FastAPI(lifespan=lifespan)

# ---------------------------------------------------------------------------
# Include routers
# ---------------------------------------------------------------------------

app.include_router(ideas.router)
app.include_router(video.router)
app.include_router(admin.router)

# ---------------------------------------------------------------------------
# Static files (production)
# ---------------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).resolve().parent
dist_path = BASE_DIR / "dist"
if dist_path.exists():
    app.mount("/", StaticFiles(directory=str(dist_path), html=True), name="dist")
