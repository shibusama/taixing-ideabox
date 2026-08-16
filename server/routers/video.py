"""Video pipeline routes: mindmap / poster."""

import json
import os
import uuid

from fastapi import APIRouter
from pydantic import BaseModel

from config import _executor, mindmap_progress
from cover import _get_cached_cover, submit_cover_task
from db import SessionLocal
from helpers import _now_ms, cache_key
from models import Mindmap, Task

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
    return None


# ---------------------------------------------------------------------------
# Mindmap background task
# ---------------------------------------------------------------------------

def _run_mindmap_task(task_id: str, url: str):
    """Background job: call qwen2image workflow -> persist result."""
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
            mindmap_progress[task_id] = "正在通过工作流生成思维导图…"

            # Call qwen2image workflow for mindmap
            import httpx
            base_url = os.environ.get("QWEN2IMAGE_BASE_URL", "https://qwen2image.coze.site")

            with httpx.Client(timeout=300.0) as client:
                files = {
                    "mode": (None, "url"),
                    "size": (None, "1024x1024"),
                    "style": (None, "pop"),
                    "type": (None, "mindmap"),
                    "url": (None, url),
                }
                resp = client.post(f"{base_url}/api/generate", files=files)
                resp.raise_for_status()
                data = resp.json()

                if not data.get("ok"):
                    raise RuntimeError(data.get("detail", "工作流生成失败"))

                image_base64 = data.get("image_base64")
                if not image_base64:
                    raise RuntimeError("工作流未返回图片数据")

            result = {
                "id": key,
                "cached": False,
                "mindmap_md": image_base64,
            }
            with SessionLocal() as db:
                db.add(Mindmap(
                    url_hash=key,
                    url=url,
                    mindmap_md=image_base64,
                    created_at=_now_ms(),
                ))
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
    _executor.submit(_run_mindmap_task, task_id, url)
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
# Poster routes
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