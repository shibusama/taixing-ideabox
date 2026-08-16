"""Cover / information poster generation via qwen2image.coze.site."""

import os
import threading
import uuid
from datetime import datetime, timedelta, timezone

import httpx

from config import _executor, cover_progress
from db import SessionLocal
from helpers import cache_key
from models import Cover, Task

# Task expiry (30 minutes)
_TASK_TTL = timedelta(minutes=30)

# Cache for in-flight tasks (url_hash -> task_id)
_pending_tasks: dict[str, str] = {}
_lock = threading.Lock()


def _now_dt() -> datetime:
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def _cleanup_expired_tasks():
    """Remove tasks older than TTL from database and cache."""
    cutoff = _now_dt() - _TASK_TTL
    with SessionLocal() as db:
        expired = db.query(Task).filter(
            Task.kind == "cover",
            Task.updated_at < cutoff,
        ).all()
        for task in expired:
            db.delete(task)
        db.commit()


def _get_cached_cover(url_hash: str) -> dict | None:
    """Get cached cover result by URL hash."""
    with SessionLocal() as db:
        row = db.query(Cover).filter(Cover.url_hash == url_hash).first()
        if row:
            return {
                "id": url_hash,
                "cached": True,
                "image_url": row.image_url,
                "prompt": row.prompt,
            }
    return None


def _call_qwen2image_workflow(url: str, output_type: str = "poster") -> str:
    """
    Call qwen2image.coze.site API to generate cover/mindmap.

    Args:
        url: Video URL
        output_type: "poster" or "mindmap"

    Returns:
        Base64 data URL of generated image
    """
    base_url = os.environ.get("QWEN2IMAGE_BASE_URL", "https://qwen2image.coze.site")

    with httpx.Client(timeout=300.0) as client:
        # Build multipart form data
        files = {
            "mode": (None, "url"),
            "size": (None, "1024x1024"),
            "style": (None, "pop"),
            "type": (None, output_type),
            "url": (None, url),
        }

        resp = client.post(
            f"{base_url}/api/generate",
            files=files,
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("ok"):
            raise RuntimeError(data.get("detail", "工作流生成失败"))

        image_base64 = data.get("image_base64")
        if not image_base64:
            raise RuntimeError("工作流未返回图片数据")

        return image_base64


def run_cover_task(task_id: str, url: str):
    """Background job: call qwen2image workflow -> persist result."""
    key = cache_key(url)
    cover_progress[task_id] = "解析视频链接…"
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "running"
                db.commit()

        cached = _get_cached_cover(key)
        if cached:
            result = cached
            cover_progress[task_id] = "已命中缓存，直接使用"
        else:
            cover_progress[task_id] = "正在通过工作流解析视频并生成海报…"
            image_data = _call_qwen2image_workflow(url, output_type="poster")
            prompt = ""

            result = {
                "id": key,
                "cached": False,
                "image_url": image_data,
                "prompt": prompt,
            }
            with SessionLocal() as db:
                existing = db.get(Cover, key)
                if existing:
                    existing.image_url = image_data
                    existing.prompt = prompt
                else:
                    db.add(Cover(
                        url_hash=key,
                        url=url,
                        image_url=image_data,
                        prompt=prompt,
                        created_at=_now_ms(),
                    ))
                db.commit()

        cover_progress[task_id] = "完成！"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()

        # Remove from pending cache
        with _lock:
            _pending_tasks.pop(key, None)

    except Exception as exc:
        cover_progress[task_id] = f"失败: {exc}"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()
        with _lock:
            _pending_tasks.pop(key, None)


def _now_ms():
    """Return current timestamp in milliseconds."""
    return int(_now_dt().timestamp() * 1000)


def submit_cover_task(url: str) -> str | None:
    """Submit a cover generation task. Returns task_id or None if cached."""
    # Clean up expired tasks periodically
    _cleanup_expired_tasks()

    key = cache_key(url)

    # Check cache first
    if _get_cached_cover(key):
        return None

    # Check if task already pending
    with _lock:
        if key in _pending_tasks:
            return _pending_tasks[key]

    # Create new task
    task_id = uuid.uuid4().hex[:12]
    now = _now_ms()
    with SessionLocal() as db:
        db.add(Task(
            task_id=task_id,
            url=url,
            status="pending",
            kind="cover",
            key=key,
            created_at=now,
            updated_at=now,
        ))
        db.commit()

    with _lock:
        _pending_tasks[key] = task_id

    _executor.submit(run_cover_task, task_id, url)
    return task_id
