"""Video pipeline routes: mindmap / cover."""

import json
import os
import pathlib
import subprocess
import sys
import threading
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

import llm
from config import (
    _executor,
    SKILL_SCRIPT,
    WORK_ROOT,
    LEGACY_CACHE_DIR,
    cover_progress,
    mindmap_progress,
    material_locks,
)
from cover import _get_cached_cover, run_cover_task, submit_cover_task
from db import SessionLocal
from helpers import _now_ms, _new_id, cache_key, _read_optional, _load_legacy_cache
from models import Cover, Mindmap, Task

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class MindmapRequest(BaseModel):
    url: str


class CoverRequest(BaseModel):
    url: str


# ---------------------------------------------------------------------------
# Mindmap cache helpers
# ---------------------------------------------------------------------------

def _get_cached_mindmap(url_hash: str) -> dict | None:
    with SessionLocal() as db:
        row = db.query(Mindmap).filter(Mindmap.url_hash == url_hash).first()
        if row:
            return {"id": url_hash, "cached": True, "mindmap_md": row.mindmap_md}
    return _load_legacy_cache(url_hash)


# ---------------------------------------------------------------------------
# Video material preparation
# ---------------------------------------------------------------------------

def _prepare_material(key: str, url: str):
    """Run prepare_video.py once -> (low_cost, transcript_preview). Reuses existing work dir."""
    work_dir = WORK_ROOT / key
    low_cost_path = work_dir / "low_cost_material.json"
    if low_cost_path.exists():
        low_cost = json.loads(low_cost_path.read_text(encoding="utf-8"))
        preview = _read_optional(work_dir / "transcript_preview.txt")
        return low_cost, preview

    work_dir.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            sys.executable,
            str(SKILL_SCRIPT),
            "--url",
            url,
            "--work-dir",
            str(work_dir),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=1200,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        tail_lines = [ln for ln in stderr.splitlines() if ln.strip()][-4:]
        raise RuntimeError("prepare_video.py failed: " + " | ".join(tail_lines[-2:]))

    if not low_cost_path.exists():
        raise RuntimeError("low_cost_material.json was not produced")
    low_cost = json.loads(low_cost_path.read_text(encoding="utf-8"))
    preview = _read_optional(work_dir / "transcript_preview.txt")
    return low_cost, preview


def _material(key: str, url: str):
    """Run _prepare_material once per url_hash, guarded by a per-key lock."""
    lock = material_locks.setdefault(key, threading.Lock())
    with lock:
        return _prepare_material(key, url)


# ---------------------------------------------------------------------------
# Mindmap background task
# ---------------------------------------------------------------------------

def _run_task(task_id: str, url: str):
    """Background job: download/transcribe -> LLM -> persist result."""
    key = cache_key(url)
    mindmap_progress[task_id] = "解析视频链接…"
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "running"
                db.commit()

        cached = _get_cached_mindmap(key)
        if cached:
            result = cached
            mindmap_progress[task_id] = "已命中缓存，直接使用"
        else:
            mindmap_progress[task_id] = "下载并分析视频内容…"
            low_cost, preview = _material(key, url)

            mindmap_progress[task_id] = "生成思维导图中…"
            mindmap_md = llm.generate_mindmap(low_cost, preview)

            result = {"id": key, "cached": False, "mindmap_md": mindmap_md}
            with SessionLocal() as db:
                db.add(Mindmap(url_hash=key, url=url, mindmap_md=mindmap_md, created_at=_now_ms()))
                db.commit()

        mindmap_progress[task_id] = "完成！"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()
    except Exception as exc:
        mindmap_progress[task_id] = f"失败: {exc}"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()


# ---------------------------------------------------------------------------
# Mindmap routes
# ---------------------------------------------------------------------------

@router.post("/api/mindmap")
def create_mindmap(req: MindmapRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        return {"task_id": None, "error": "请提供有效的视频链接"}
    key = cache_key(url)
    cached = _get_cached_mindmap(key)
    if cached:
        return {"task_id": None, "result": cached}
    now = _now_ms()
    task_id = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        db.add(Task(task_id=task_id, url=url, status="pending", kind="mindmap", key=key, created_at=now, updated_at=now))
        db.commit()
    _executor.submit(_run_task, task_id, url)
    return {"task_id": task_id}


@router.get("/api/mindmap/{task_id}")
def get_mindmap(task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
    if task is None:
        return {"status": "error", "error": "task not found"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "progress": mindmap_progress.get(task_id, ""),
    }


# ---------------------------------------------------------------------------
# Cover routes
# ---------------------------------------------------------------------------

@router.post("/api/cover")
def create_cover(req: CoverRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        return {"task_id": None, "error": "请提供有效的链接"}
    task_id = submit_cover_task(url)
    if task_id is None:
        return {"task_id": None, "result": _get_cached_cover(cache_key(url))}
    return {"task_id": task_id}


@router.get("/api/cover/{task_id}")
def get_cover(task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
    if task is None:
        return {"status": "error", "error": "task not found"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
        "progress": cover_progress.get(task_id, ""),
    }
