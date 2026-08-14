"""Cover image generation — delegates to url2image.coze.site workflow."""

import os
import uuid

import httpx

from config import _executor, cover_progress
from db import SessionLocal
from helpers import _now_ms, cache_key
from models import Cover, Task


def _get_cached_cover(url_hash: str) -> dict | None:
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


def _call_workflow(url: str, output_type: str = "cover") -> dict:
    """调用 url2image.coze.site 工作流。

    Args:
        url: 视频链接
        output_type: 输出类型，"cover"（信息海报封面）或 "mindmap"（思维导图）

    Returns:
        工作流返回的完整 JSON dict
    """
    base_url = os.environ.get("VIDEO2IMAGE_BASE_URL", "https://url2image.coze.site")
    token = os.environ.get("VIDEO2IMAGE_TOKEN", "")
    if not token:
        raise RuntimeError("VIDEO2IMAGE_TOKEN 未配置")
    with httpx.Client(timeout=180.0) as client:
        resp = client.post(
            f"{base_url}/run",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "video_url": {"url": url, "file_type": "video"},
                "style": "pop",
                "type": output_type,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("error"):
            raise RuntimeError(f"工作流解析失败: {data['error']}")
        return data


def _call_video2image_workflow(url: str) -> str:
    """调用工作流生成知识卡片封面图，返回 card_image_url。"""
    data = _call_workflow(url, "cover")
    card_url = data.get("card_image_url")
    if not card_url:
        raise RuntimeError("工作流未返回 card_image_url")
    return card_url


def run_cover_task(task_id: str, url: str):
    """Background job: call video2image workflow -> persist result."""
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
            cover_progress[task_id] = "正在通过工作流解析视频并生成封面…"
            image_url = _call_video2image_workflow(url)
            prompt = ""

            result = {"id": key, "cached": False, "image_url": image_url, "prompt": prompt}
            with SessionLocal() as db:
                existing = db.get(Cover, key)
                if existing:
                    existing.image_url = image_url
                    existing.prompt = prompt
                else:
                    db.add(Cover(url_hash=key, url=url, image_url=image_url, prompt=prompt, created_at=_now_ms()))
                db.commit()

        cover_progress[task_id] = "完成！"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()
    except Exception as exc:
        cover_progress[task_id] = f"失败: {exc}"
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()


def submit_cover_task(url: str) -> str | None:
    """Submit a cover generation task, returning task_id or None if cached."""
    key = cache_key(url)
    cached = _get_cached_cover(key)
    if cached:
        return None
    task_id = uuid.uuid4().hex[:12]
    now = _now_ms()
    with SessionLocal() as db:
        db.add(Task(task_id=task_id, url=url, status="pending", kind="cover", key=key, created_at=now, updated_at=now))
        db.commit()
    _executor.submit(run_cover_task, task_id, url)
    return task_id