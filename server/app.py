"""IdeaBox API.

Storage:
  - Ideas / archived / tags  -> SQLite (ideas, tags tables)
  - Mindmap cache            -> SQLite (mindmaps table, replaces cache/*.json)
  - Mindmap task states      -> SQLite (tasks table, survives restarts)

Pipeline (unchanged):
  1. POST /api/mindmap {url}          -> {task_id}  (runs in background)
  2. GET  /api/mindmap/{task_id}      -> {status, result?, error?}
"""

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db as dbmod
import llm
from db import SessionLocal, init_db
from models import Cover, Idea, Mindmap, Note, Tag, Task

BASE_DIR = pathlib.Path(__file__).parent

# prepare_video.py 位置：优先用环境变量 SKILL_SCRIPT_PATH（Linux 部署用），
# 否则回退到 server/skills/prepare_video.py（随仓库部署的副本）。
_default_skill_script = BASE_DIR / "skills" / "prepare_video.py"
SKILL_SCRIPT = pathlib.Path(
    os.environ.get("SKILL_SCRIPT_PATH", str(_default_skill_script))
)
WORK_ROOT = pathlib.Path(os.environ.get("WORK_ROOT", str(BASE_DIR / "work")))
LEGACY_CACHE_DIR = BASE_DIR / "cache"
WORK_ROOT.mkdir(parents=True, exist_ok=True)

init_db()

app = FastAPI(title="IdeaBox API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mindmap")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_ms() -> float:
    return time.time() * 1000


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def cache_key(url: str) -> str:
    return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:16]


def _read_optional(path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


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
    from datetime import datetime

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


# ---------------------------------------------------------------------------
# Ideas CRUD (soft delete / archive)
# ---------------------------------------------------------------------------

class IdeaPayload(BaseModel):
    content: str
    tags: list[str] = []
    pinned: bool = False
    id: str | None = None
    createdAt: float | None = None
    updatedAt: float | None = None


@app.get("/api/ideas")
def list_ideas():
    with SessionLocal() as db:
        rows = (
            db.query(Idea)
            .filter(Idea.deleted_at.is_(None))
            .order_by(Idea.pinned.desc(), Idea.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]


@app.get("/api/ideas/archived")
def list_archived():
    with SessionLocal() as db:
        rows = (
            db.query(Idea)
            .filter(Idea.deleted_at.is_not(None))
            .order_by(Idea.deleted_at.desc())
            .all()
        )
        return [r.to_dict(include_deleted=True) for r in rows]


@app.post("/api/ideas")
def create_idea(payload: IdeaPayload):
    now = _now_ms()
    idea = Idea(
        id=payload.id or _new_id(),
        content=payload.content.strip(),
        tags=list(dict.fromkeys(payload.tags)),
        pinned=1 if payload.pinned else 0,
        created_at=payload.createdAt or now,
        updated_at=payload.updatedAt or now,
        deleted_at=None,
    )
    with SessionLocal() as db:
        db.add(idea)
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@app.put("/api/ideas/{idea_id}")
def update_idea(idea_id: str, payload: IdeaPayload):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None or idea.deleted_at is not None:
            raise HTTPException(404, "idea not found")
        if payload.content is not None:
            idea.content = payload.content.strip()
        if payload.tags is not None:
            idea.tags = list(dict.fromkeys(payload.tags))
        if payload.pinned is not None:
            idea.pinned = 1 if payload.pinned else 0
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@app.delete("/api/ideas/{idea_id}")
def delete_idea(idea_id: str):
    """Soft delete -> move to archive."""
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "idea not found")
        idea.deleted_at = _now_ms()
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return {"ok": True}


@app.post("/api/ideas/{idea_id}/restore")
def restore_idea(idea_id: str):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None:
            raise HTTPException(404, "idea not found")
        idea.deleted_at = None
        idea.updated_at = _now_ms()
        _rebuild_tags(db)
        db.commit()
        return idea.to_dict()


@app.post("/api/ideas/{idea_id}/pin")
def toggle_pin(idea_id: str):
    with SessionLocal() as db:
        idea = db.get(Idea, idea_id)
        if idea is None or idea.deleted_at is not None:
            raise HTTPException(404, "idea not found")
        idea.pinned = 0 if idea.pinned else 1
        idea.updated_at = _now_ms()
        db.commit()
        return idea.to_dict()


@app.delete("/api/archived")
def purge_archived():
    """Permanently delete archived ideas."""
    with SessionLocal() as db:
        db.query(Idea).filter(Idea.deleted_at.is_not(None)).delete()
        db.commit()
        return {"ok": True}


@app.get("/api/tags")
def list_tags():
    with SessionLocal() as db:
        return [
            {"name": t.name, "count": t.count}
            for t in db.query(Tag).order_by(Tag.count.desc(), Tag.name).all()
        ]


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

@app.get("/api/export")
def export_data():
    with SessionLocal() as db:
        ideas = db.query(Idea).all()
        return {
            "ideas": [i.to_dict() for i in ideas if i.deleted_at is None],
            "archived": [i.to_dict(include_deleted=True) for i in ideas if i.deleted_at is not None],
            "exportedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }


@app.post("/api/import")
def import_data(payload: dict):
    """Replace all ideas+archived with the given dataset."""
    ideas_in = payload.get("ideas", []) or []
    archived_in = payload.get("archived", []) or []
    now = _now_ms()
    with SessionLocal() as db:
        db.query(Idea).delete()
        for item in ideas_in + archived_in:
            deleted = item.get("deletedAt")
            db.add(
                Idea(
                    id=item.get("id") or _new_id(),
                    content=str(item.get("content", "")).strip(),
                    tags=list(dict.fromkeys(item.get("tags", []) or [])),
                    pinned=1 if item.get("pinned") else 0,
                    created_at=float(item.get("createdAt") or now),
                    updated_at=float(item.get("updatedAt") or now),
                    deleted_at=float(deleted) if deleted is not None else None,
                )
            )
        _rebuild_tags(db)
        db.commit()
        return {"ok": True, "imported": len(ideas_in) + len(archived_in)}


# ---------------------------------------------------------------------------
# Mindmap pipeline (persistent cache + persistent tasks)
# ---------------------------------------------------------------------------

class MindmapRequest(BaseModel):
    url: str


def _load_legacy_cache(url_hash: str) -> dict | None:
    """Migrate a cache/*.json entry into the mindmaps table if present."""
    legacy = LEGACY_CACHE_DIR / f"{url_hash}.json"
    if not legacy.exists():
        return None
    try:
        data = json.loads(legacy.read_text(encoding="utf-8"))
    except Exception:
        return None
    md = data.get("mindmap_md")
    url = data.get("url") or ""
    if md:
        with SessionLocal() as db:
            db.add(Mindmap(url_hash=url_hash, url=url, mindmap_md=md, created_at=_now_ms()))
            db.commit()
    return {"id": url_hash, "cached": True, "mindmap_md": md} if md else None


def _get_cached_mindmap(url_hash: str) -> dict | None:
    with SessionLocal() as db:
        row = db.query(Mindmap).filter(Mindmap.url_hash == url_hash).first()
        if row:
            return {"id": url_hash, "cached": True, "mindmap_md": row.mindmap_md}
    return _load_legacy_cache(url_hash)


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


def _run_task(task_id: str, url: str):
    """Background job: download/transcribe -> LLM -> persist result."""
    key = cache_key(url)
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "running"
                db.commit()

        cached = _get_cached_mindmap(key)
        if cached:
            result = cached
        else:
            low_cost, preview = _prepare_material(key, url)
            mindmap_md = llm.generate_mindmap(low_cost, preview)

            result = {"id": key, "cached": False, "mindmap_md": mindmap_md}
            with SessionLocal() as db:
                db.add(Mindmap(url_hash=key, url=url, mindmap_md=mindmap_md, created_at=_now_ms()))
                db.commit()

        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()


def _get_cached_note(url_hash: str) -> dict | None:
    with SessionLocal() as db:
        row = db.query(Note).filter(Note.url_hash == url_hash).first()
        if row:
            return {
                "id": url_hash,
                "cached": True,
                "note_md": row.note_md,
                "detail": bool(row.detail),
            }
    return None


def _run_note_task(task_id: str, url: str, detail: bool = False):
    """Background job: download/transcribe -> LLM note -> persist result."""
    key = cache_key(url)
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "running"
                db.commit()

        cached = _get_cached_note(key)
        if cached and cached.get("detail") == detail:
            result = cached
        else:
            low_cost, preview = _prepare_material(key, url)
            note_md = llm.generate_note(low_cost, url, preview, detail=detail)

            result = {"id": key, "cached": False, "note_md": note_md, "detail": detail}
            with SessionLocal() as db:
                db.add(Note(url_hash=key, url=url, note_md=note_md, detail=detail, created_at=_now_ms()))
                db.commit()

        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()


@app.on_event("startup")
def _startup():
    """Mark interrupted tasks as error; auto-migrate legacy DB if current one is empty."""
    _migrate_legacy_data()
    with SessionLocal() as db:
        db.query(Task).filter(Task.status.in_(["pending", "running"])).update(
            {"status": "error", "error": "服务重启，任务已中断，请重新提交"}
        )
        db.commit()


@app.post("/api/mindmap")
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
        db.add(Task(task_id=task_id, url=url, status="pending", created_at=now, updated_at=now))
        db.commit()
    _executor.submit(_run_task, task_id, url)
    return {"task_id": task_id}


# ---------------------------------------------------------------------------
# Note pipeline (link -> Markdown note, reuses the same video material)
# ---------------------------------------------------------------------------

class NoteRequest(BaseModel):
    url: str
    detail: bool = False


@app.post("/api/note")
def create_note(req: NoteRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        return {"task_id": None, "error": "请提供有效的链接"}
    key = cache_key(url)
    cached = _get_cached_note(key)
    if cached and cached.get("detail") == req.detail:
        return {"task_id": None, "result": cached}
    now = _now_ms()
    task_id = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        db.add(Task(task_id=task_id, url=url, status="pending", created_at=now, updated_at=now))
        db.commit()
    _executor.submit(_run_note_task, task_id, url, req.detail)
    return {"task_id": task_id}


@app.get("/api/note/{task_id}")
def get_note(task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
    if task is None:
        return {"status": "error", "error": "task not found"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
    }


# ---------------------------------------------------------------------------
# Cover pipeline (link -> AI image via text-to-image API)
# ---------------------------------------------------------------------------

class CoverRequest(BaseModel):
    url: str


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


def _text_to_image(prompt: str) -> str:
    """Call SiliconFlow /images/generations, return the image URL."""
    import urllib.request

    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    if not base_url:
        base_url = "https://api.siliconflow.cn/v1"
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("IMAGE_MODEL", "Qwen/Qwen-Image")
    image_size = os.environ.get("IMAGE_SIZE", "1024x1024")

    payload = {"model": model, "prompt": prompt, "image_size": image_size}
    req = urllib.request.Request(
        f"{base_url}/images/generations",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    images = data.get("images") or []
    url = images[0].get("url") if images else ""
    if not url:
        raise RuntimeError("text-to-image API returned no image url")
    return url


def _run_cover_task(task_id: str, url: str):
    """Background job: analyze content -> generate prompt -> text-to-image -> persist."""
    key = cache_key(url)
    try:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "running"
                db.commit()

        cached = _get_cached_cover(key)
        if cached:
            result = cached
        else:
            low_cost, preview = _prepare_material(key, url)
            prompt = llm.generate_image_prompt(low_cost, preview)
            image_url = _text_to_image(prompt)

            result = {"id": key, "cached": False, "image_url": image_url, "prompt": prompt}
            with SessionLocal() as db:
                existing = db.get(Cover, key)
                if existing:
                    existing.image_url = image_url
                    existing.prompt = prompt
                else:
                    db.add(Cover(url_hash=key, url=url, image_url=image_url, prompt=prompt, created_at=_now_ms()))
                db.commit()

        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "done"
                task.result = result
                db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            task = db.get(Task, task_id)
            if task:
                task.status = "error"
                task.error = str(exc)
                db.commit()


@app.post("/api/cover")
def create_cover(req: CoverRequest):
    url = req.url.strip()
    if not url.startswith(("http://", "https://")):
        return {"task_id": None, "error": "请提供有效的链接"}
    key = cache_key(url)
    cached = _get_cached_cover(key)
    if cached:
        return {"task_id": None, "result": cached}
    now = _now_ms()
    task_id = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        db.add(Task(task_id=task_id, url=url, status="pending", created_at=now, updated_at=now))
        db.commit()
    _executor.submit(_run_cover_task, task_id, url)
    return {"task_id": task_id}


@app.get("/api/cover/{task_id}")
def get_cover(task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
    if task is None:
        return {"status": "error", "error": "task not found"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
    }


# ---------------------------------------------------------------------------
# Admin: regenerate cached mindmaps with real transcription (in-process)
# ---------------------------------------------------------------------------

def _transcribe_work_dir(work_dir):
    """Transcribe audio.wav into transcript.json if missing (in-process)."""
    import importlib.util

    transcript_json = work_dir / "transcript.json"
    if transcript_json.exists():
        return True
    audio = work_dir / "audio.wav"
    if not audio.exists():
        return False
    spec = importlib.util.spec_from_file_location("prepare_video", SKILL_SCRIPT)
    pv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pv)
    try:
        pv.transcribe(work_dir, audio, "small", skip=False)
        return transcript_json.exists()
    except Exception:
        return False


def _regenerate_one(row):
    """Regenerate a single cached mindmap using real transcription."""
    import json as _json

    work_dir = WORK_ROOT / row.url_hash
    low_cost_path = work_dir / "low_cost_material.json"
    if not work_dir.exists() or not low_cost_path.exists():
        return {"url_hash": row.url_hash, "ok": False, "error": "no work dir / low_cost_material.json"}

    # 1. transcribe (if possible) -> rebuild preview from transcript.json
    transcribed = _transcribe_work_dir(work_dir)
    preview_lines = []
    transcript_json = work_dir / "transcript.json"
    segments = []
    if transcript_json.exists():
        try:
            data = _json.loads(transcript_json.read_text(encoding="utf-8"))
            segments = data.get("segments") or []
        except Exception:
            segments = []
    if segments:
        for seg in segments[:10]:
            text = (seg.get("text") or "").strip()
            if text:
                preview_lines.append(f"[{seg.get('start', 0)}-{seg.get('end', 0)}] {text}")
    preview = "\n".join(preview_lines) if preview_lines else "(no transcript available)"

    # 2. LLM regenerate
    low_cost = _json.loads(low_cost_path.read_text(encoding="utf-8"))
    low_cost["transcript"] = {"available": bool(segments), "segments": len(segments)}
    mindmap_md = llm.generate_mindmap(low_cost, preview)

    # 3. persist (in-process writer)
    with SessionLocal() as db:
        m = db.get(Mindmap, row.id)
        if m:
            m.mindmap_md = mindmap_md
            db.commit()
    return {"url_hash": row.url_hash, "ok": True, "chars": len(mindmap_md), "transcribed": transcribed}


@app.post("/api/admin/regenerate-mindmaps")
def admin_regenerate():
    """Regenerate all cached mindmaps with real transcription (background)."""
    with SessionLocal() as db:
        rows = list(db.query(Mindmap).all())
    _executor.submit(_admin_regenerate_worker, [r.id for r in rows])
    return {"ok": True, "queued": len(rows)}


def _admin_regenerate_worker(mindmap_ids):
    for mid in mindmap_ids:
        with SessionLocal() as db:
            row = db.get(Mindmap, mid)
        if row is None:
            continue
        try:
            _regenerate_one(row)
        except Exception as exc:
            print(f"[admin] regenerate {row.url_hash} failed: {exc}", file=sys.stderr)


@app.get("/api/mindmap/{task_id}")
def get_mindmap(task_id: str):
    with SessionLocal() as db:
        task = db.get(Task, task_id)
    if task is None:
        return {"status": "error", "error": "task not found"}
    return {
        "status": task.status,
        "result": task.result,
        "error": task.error,
    }


@app.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# 视频号链接解析（移植自 wx_channels_download/internal/api/sph/worker.js）
# 两步纯 HTTP：分享链接 → 元宝换取 exportId/token → 微信频道换取 videoUrl
# 依赖环境变量 HY_TOKEN（腾讯元宝 cookie，可在浏览器登录元宝后 F12 获取）
# ---------------------------------------------------------------------------
import httpx

_SPH_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
_SPH_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
_SPH_PAGE_URL = "https%3A%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed"
_SPH_REFERER = "https://yuanbao.tencent.com/chat/naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1"
_SPH_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def _sph_rid() -> str:
    import random

    ts = f"{int(time.time()):x}"
    rand = "".join(random.choice("0123456789abcdef") for _ in range(8))
    return f"{ts}-{rand}"


def _sph_parse_share_url(share_url: str, cookie: str) -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://yuanbao.tencent.com",
        "referer": _SPH_REFERER,
        "user-agent": _SPH_UA,
        "t-userid": "b9575f6b0a8c4a55a08096904a5ef20a",
        "x-agentid": "naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1",
        "x-device-id": "1921b001708100d7fa31002b9646bd0cc15a3e2e1f",
        "x-hy92": "e963067ffa31002b9646bd0c03000008b1951a",
        "x-hy93": "1921b001708100d7fa31002b9646bd0cc15a3e2e1f",
        "x-id": "b9575f6b0a8c4a55a08096904a5ef20a",
        "x-platform": "mac",
        "x-source": "web",
        "x-webversion": "2.69.0",
        "cookie": cookie,
    }
    payload = {"type": "video_channel_url", "url": share_url, "scene": 1}
    resp = httpx.post(_SPH_PARSE_URL, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _sph_get_feed_info(export_id: str, general_token: str) -> dict:
    rid = _sph_rid()
    referer = (
        "https://channels.weixin.qq.com/finder-preview/pages/feed"
        f"?entry_card_type=48&comment_scene=39&appid=0&token={general_token}"
        f"&entry_scene=0&eid={export_id}"
    )
    headers = {
        "accept": "application/json, text/plain, */*",
        "content-type": "application/json",
        "origin": "https://channels.weixin.qq.com",
        "referer": referer,
        "user-agent": _SPH_UA,
    }
    api_url = f"{_SPH_FEED_URL}?_rid={rid}&_pageUrl={_SPH_PAGE_URL}"
    payload = {"baseReq": {"generalToken": general_token}, "exportId": export_id}
    resp = httpx.post(api_url, json=payload, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.json()


class SphResolveRequest(BaseModel):
    url: str


@app.post("/api/sph/resolve")
def sph_resolve(req: SphResolveRequest):
    """解析视频号分享链接，返回可播放/下载的视频直链。"""
    cookie = os.environ.get("HY_TOKEN", "")
    if not cookie:
        raise HTTPException(status_code=400, detail="HY_TOKEN 未配置")

    try:
        parse = _sph_parse_share_url(req.url.strip(), cookie)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"parse share url failed: {exc}") from exc

    data = parse.get("data") or {}
    export_id = data.get("wx_export_id", "")
    playable = data.get("playable_url") or ""
    from urllib.parse import parse_qs, urlparse

    qs = parse_qs(urlparse(playable).query)
    general_token = (qs.get("token") or [""])[0]
    eid = (qs.get("eid") or [""])[0] or export_id

    try:
        feed = _sph_get_feed_info(eid, general_token)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"get feed info failed: {exc}") from exc

    feed_data = feed.get("data") or {}
    feed_info = feed_data.get("feedInfo") or {}
    return {
        "code": 0,
        "data": {
            "videoUrl": feed_info.get("videoUrl") or "",
            "originVideoUrl": feed_info.get("originVideoUrl") or "",
            "description": feed_info.get("description") or "",
            "author": (feed_data.get("authorInfo") or {}).get("nickname") or "",
            "coverUrl": feed_info.get("coverUrl") or "",
        },
    }


# ---------------------------------------------------------------------------
# Serve built frontend (production) — mount AFTER all API routes
# ---------------------------------------------------------------------------
try:
    from fastapi.staticfiles import StaticFiles

    dist_dir = BASE_DIR.parent / "dist"
    if dist_dir.exists():
        app.mount("/", StaticFiles(directory=str(dist_dir), html=True), name="frontend")
        print(f"[deploy] frontend mounted from {dist_dir}", file=sys.stderr)
except Exception as exc:
    print(f"[deploy] frontend mount skipped: {exc}", file=sys.stderr)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
