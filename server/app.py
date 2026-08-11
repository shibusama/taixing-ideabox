"""IdeaBox API — minimal entry point."""

import pathlib
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config  # noqa: F401 — triggers init_db() and env setup
from db import SessionLocal
from helpers import _migrate_legacy_data
from models import Task
from routers import admin, ideas, video

app = FastAPI(title="IdeaBox API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ideas.router)
app.include_router(video.router)
app.include_router(admin.router)


@app.on_event("startup")
def _startup():
    """Mark interrupted tasks as error; auto-migrate legacy DB if current one is empty."""
    _migrate_legacy_data()
    with SessionLocal() as db:
        db.query(Task).filter(Task.status.in_(["pending", "running"])).update(
            {"status": "error", "error": "服务重启，任务已中断，请重新提交"}
        )
        db.commit()


# ---------------------------------------------------------------------------
# Serve built frontend (production) — mount AFTER all API routes
# ---------------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).parent
try:
    dist_dir = BASE_DIR.parent / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
        print(f"[deploy] frontend mounted from {dist_dir}", file=sys.stderr)
except Exception as exc:
    print(f"[deploy] frontend mount skipped: {exc}", file=sys.stderr)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)