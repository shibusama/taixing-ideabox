"""Admin routes: health check, regenerate mindmaps, sph/resolve."""

import importlib.util
import json
import os
import random
import time

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import llm
from config import _executor, SKILL_SCRIPT, WORK_ROOT
from db import SessionLocal
from models import Mindmap, Task

router = APIRouter()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/api/health")
def health():
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin: regenerate cached mindmaps
# ---------------------------------------------------------------------------

def _transcribe_work_dir(work_dir):
    """Transcribe audio.wav into transcript.json if missing (in-process)."""
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
    work_dir = WORK_ROOT / row.url_hash
    low_cost_path = work_dir / "low_cost_material.json"
    if not work_dir.exists() or not low_cost_path.exists():
        return {"url_hash": row.url_hash, "ok": False, "error": "no work dir / low_cost_material.json"}

    transcribed = _transcribe_work_dir(work_dir)
    preview_lines = []
    transcript_json = work_dir / "transcript.json"
    segments = []
    if transcript_json.exists():
        try:
            data = json.loads(transcript_json.read_text(encoding="utf-8"))
            segments = data.get("segments") or []
        except Exception:
            segments = []
    if segments:
        for seg in segments[:10]:
            text = (seg.get("text") or "").strip()
            if text:
                preview_lines.append(f"[{seg.get('start', 0)}-{seg.get('end', 0)}] {text}")
    preview = "\n".join(preview_lines) if preview_lines else "(no transcript available)"

    low_cost = json.loads(low_cost_path.read_text(encoding="utf-8"))
    low_cost["transcript"] = {"available": bool(segments), "segments": len(segments)}
    mindmap_md = llm.generate_mindmap(low_cost, preview)

    with SessionLocal() as db:
        m = db.get(Mindmap, row.id)
        if m:
            m.mindmap_md = mindmap_md
            db.commit()
    return {"url_hash": row.url_hash, "ok": True, "chars": len(mindmap_md), "transcribed": transcribed}


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


@router.post("/api/admin/regenerate-mindmaps")
def admin_regenerate():
    """Regenerate all cached mindmaps with real transcription (background)."""
    with SessionLocal() as db:
        rows = list(db.query(Mindmap).all())
    _executor.submit(_admin_regenerate_worker, [r.id for r in rows])
    return {"ok": True, "queued": len(rows)}


# ---------------------------------------------------------------------------
# 视频号链接解析（移植自 wx_channels_download/internal/api/sph/worker.js）
# 两步纯 HTTP：分享链接 → 元宝换取 exportId/token → 微信频道换取 videoUrl
# 依赖环境变量 HY_TOKEN（腾讯元宝 cookie，可在浏览器登录元宝后 F12 获取）
# ---------------------------------------------------------------------------

_SPH_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
_SPH_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
_SPH_PAGE_URL = "https%3A%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed"
_SPH_REFERER = "https://yuanbao.tencent.com/chat/naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1"
_SPH_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def _sph_rid() -> str:
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


@router.post("/api/sph/resolve")
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