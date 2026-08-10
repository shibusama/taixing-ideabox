#!/usr/bin/env python
import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request

# Ensure server/ is on path so `import llm` works when this script runs standalone
# (from app.py via importlib, or directly via `python skills/prepare_video.py`).
_SERVER_DIR = pathlib.Path(__file__).resolve().parent.parent
if str(_SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(_SERVER_DIR))

# Force UTF-8 output so emoji/Chinese in video descriptions don't crash on
# Windows (GBK console) when printing JSON.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


DOUYIN_DETAIL_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={aweme_id}"
DOUYIN_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/138.0.0.0 Safari/537.36"


def run(cmd, timeout=None):
    return subprocess.run(cmd, timeout=timeout, check=True, text=True)


def _find_ffmpeg():
    """Locate ffmpeg: prefer PATH, fall back to the binary bundled with imageio-ffmpeg.

    Coze deployment has no system ffmpeg; the imageio-ffmpeg pip package ships one,
    so adding it to requirements.txt makes video processing work there too.
    """
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _find_ffprobe():
    """Locate ffprobe on PATH (imageio-ffmpeg does not bundle ffprobe)."""
    return shutil.which("ffprobe")


def request_json(url, method="GET", payload=None, headers=None, timeout=45):
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def request_json_with_requests(url, headers=None, timeout=45):
    try:
        import requests
    except Exception as exc:
        raise RuntimeError(f"requests is required for this request: {exc}") from exc
    response = requests.get(url, headers=headers or {}, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
    if not response.text.strip():
        raise RuntimeError("empty response body")
    return response.json()


def request_text_with_requests(url, headers=None, timeout=45):
    try:
        import requests
    except Exception as exc:
        raise RuntimeError(f"requests is required for this request: {exc}") from exc
    response = requests.get(url, headers=headers or {}, timeout=timeout)
    if response.status_code != 200:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:300]}")
    return response.text


def download(url, output, user_agent=DESKTOP_UA):
    curl = shutil.which("curl.exe") or shutil.which("curl")
    if curl:
        run([
            curl,
            "-L",
            "-A",
            user_agent,
            "--fail",
            "--retry",
            "3",
            "--connect-timeout",
            "20",
            "--max-time",
            "300",
            "-o",
            str(output),
            url,
        ], timeout=360)
        return

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=300) as resp, output.open("wb") as f:
        shutil.copyfileobj(resp, f)


def detect_platform(url):
    if "weixin.qq.com/sph" in url or "channels.weixin.qq.com" in url:
        return "wechat"
    if "douyin.com" in url or "iesdouyin.com" in url:
        return "douyin"
    raise ValueError("unsupported URL platform")


def _sph_rid():
    import random

    ts = f"{int(time.time()):x}"
    rand = "".join(random.choice("0123456789abcdef") for _ in range(8))
    return f"{ts}-{rand}"


# 元宝解析（优先使用，替代不可靠的第三方 sph.litao.workers.dev）
# 逻辑与 server/app.py 的 /api/sph/resolve 一致：分享链接 → 元宝换取 exportId/token → 微信频道换取 videoUrl
_SPH_PARSE_URL = "https://yuanbao.tencent.com/api/weixin/get_parse_result"
_SPH_FEED_URL = "https://channels.weixin.qq.com/finder-preview/api/feed/get_feed_info"
_SPH_PAGE_URL = "https%3A%2F%2Fchannels.weixin.qq.com%2Ffinder-preview%2Fpages%2Ffeed"
_SPH_REFERER = "https://yuanbao.tencent.com/chat/naQivTmsDa/cf4d0079-ed1b-4c55-a3f3-2ca1379727d1"
_SPH_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
)


def _sph_parse_share_url(share_url, cookie):
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
    return request_json(_SPH_PARSE_URL, method="POST", payload=payload, headers=headers, timeout=15)


def _sph_get_feed_info(export_id, general_token):
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
    return request_json(api_url, method="POST", payload=payload, headers=headers, timeout=15)


def _parse_wechat_yuanbao(url):
    """用腾讯元宝解析视频号链接（需 HY_TOKEN cookie）。返回 video_url / feedInfo / authorInfo 或抛异常。"""
    cookie = os.environ.get("HY_TOKEN", "")
    if not cookie:
        raise RuntimeError("HY_TOKEN 未配置")
    parse = _sph_parse_share_url(url, cookie)
    data = parse.get("data") or {}
    export_id = data.get("wx_export_id", "")
    playable = data.get("playable_url") or ""
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(playable).query)
    general_token = (qs.get("token") or [""])[0]
    eid = (qs.get("eid") or [""])[0] or export_id
    feed = _sph_get_feed_info(eid, general_token)
    feed_data = feed.get("data") or {}
    feed_info = feed_data.get("feedInfo") or {}
    return {
        "video_url": feed_info.get("videoUrl") or feed_info.get("originVideoUrl") or "",
        "author": (feed_data.get("authorInfo") or {}).get("nickname") or "",
        "description": feed_info.get("description") or "",
    }


def parse_wechat(url, work_dir):
    # 优先走元宝解析（自有逻辑，可靠），失败/无 token 时回退第三方服务
    yuanbao_meta = None
    try:
        yuanbao_meta = _parse_wechat_yuanbao(url)
    except Exception as exc:
        print(f"[parse_wechat] yuanbao parse failed, fallback to third-party: {exc}", file=sys.stderr)

    if yuanbao_meta and yuanbao_meta.get("video_url"):
        video_url = yuanbao_meta["video_url"]
        # 尝试写入 profile.json 以便后续复用（元宝解析拿不到完整 feedInfo）
        (work_dir / "profile.json").write_text(
            json.dumps({"data": {"feedInfo": {"description": yuanbao_meta.get("description")},
                        "authorInfo": {"nickname": yuanbao_meta.get("author")},
                        "videoUrl": video_url}}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "platform": "wechat",
            "id": "wechat_video",
            "author": yuanbao_meta.get("author"),
            "description": yuanbao_meta.get("description"),
            "create_time": None,
            "media_type": None,
            "video_url": video_url,
            "download_user_agent": DESKTOP_UA,
        }

    # 元宝解析失败且未拿到 video_url → 直接报错（不再回退不可靠的第三方服务）
    raise RuntimeError("WeChat video parse failed: no video_url (check HY_TOKEN / yuanbao API)")


def follow_redirect(url, cookie=None):
    headers = {"User-Agent": DOUYIN_UA}
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    opener = urllib.request.build_opener(NoRedirectHandler)
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.geturl()
    except urllib.error.HTTPError as exc:
        if 300 <= exc.code < 400:
            location = exc.headers.get("Location")
            if not location:
                return url
            return urllib.parse.urljoin(url, location)
        raise


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def extract_url(text):
    match = re.search(r"https?://[^\s]+", text)
    if not match:
        raise ValueError("No URL found")
    return match.group(0).rstrip("，,。)")


def parse_douyin(url_or_text, work_dir, cookie=None):
    share_url = extract_url(url_or_text)
    real_url = follow_redirect(share_url, cookie=cookie) if "v.douyin.com" in share_url else share_url
    aweme_match = re.search(r"/video/(\d+)", real_url)
    if not aweme_match:
        parsed = urllib.parse.urlparse(real_url)
        query = urllib.parse.parse_qs(parsed.query)
        modal_id = (query.get("modal_id") or [""])[0]
        if modal_id:
            aweme_id = modal_id
        else:
            raise RuntimeError(f"Could not extract Douyin aweme_id from {real_url}")
    else:
        aweme_id = aweme_match.group(1)

    headers = {"User-Agent": DOUYIN_UA}
    if cookie:
        headers["Cookie"] = cookie
    payload = {}
    detail = {}
    try:
        payload = request_json_with_requests(DOUYIN_DETAIL_URL.format(aweme_id=aweme_id), headers=headers)
        detail = payload.get("aweme_detail") or payload
    except Exception:
        page_content = request_text_with_requests(real_url, headers=headers)
        data_match = re.search(r"window\._ROUTER_DATA\s*=\s*(.*?)</script>", page_content, re.S)
        if not data_match:
            raise RuntimeError("Douyin detail API returned no JSON and page contained no ROUTER_DATA")
        router_data = json.loads(data_match.group(1))
        loader_data = router_data.get("loaderData", router_data)
        detail = (
            ((loader_data.get("video_(id)/page") or {}).get("videoInfoRes") or {}).get("item_list", [{}])[0]
            or ((loader_data.get("note_(id)/page") or {}).get("videoInfoRes") or {}).get("item_list", [{}])[0]
        )
        payload = {"aweme_detail": detail, "source": "router_data"}

    (work_dir / "profile.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    video = detail.get("video") or {}
    play_addr = video.get("play_addr") or {}
    url_list = play_addr.get("url_list") or []
    video_url = url_list[0].replace("playwm", "play") if url_list else ""
    if not video_url:
        download_addr = video.get("download_addr") or {}
        url_list = download_addr.get("url_list") or []
        video_url = url_list[0] if url_list else ""
    if not video_url:
        raise RuntimeError("No video URL returned by Douyin detail API")
    author = detail.get("author") or {}
    return {
        "platform": "douyin",
        "id": str(detail.get("aweme_id") or aweme_id),
        "author": author.get("nickname"),
        "description": detail.get("desc"),
        "create_time": detail.get("create_time"),
        "media_type": detail.get("aweme_type"),
        "video_url": video_url,
        "real_url": real_url,
        "download_user_agent": DOUYIN_UA,
    }


def extract_media(work_dir, mp4_path, fps_interval):
    ffmpeg = _find_ffmpeg()
    ffprobe = _find_ffprobe()
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")

    audio = work_dir / "audio.wav"
    frames = work_dir / "frames"
    frames.mkdir(exist_ok=True)
    contact_sheet = work_dir / "contact_sheet.jpg"

    run([ffmpeg, "-y", "-i", str(mp4_path), "-vn", "-ac", "1", "-ar", "16000", str(audio)], timeout=180)
    # 场景检测抽帧：只在画面变化大时取一帧，避免重复/海量帧。
    # scene 阈值越高越"挑剔"（0.3 是常用起点）。配合 fps 下限防止抖动的误判。
    # -vsync vfr 表示变帧率输出，仅当 select 命中才写一帧。
    # -strict unofficial + -pix_fmt yuvj420p：兼容 non-full-range YUV 视频（否则 mjpeg 编码器拒绝，抽帧为 0）
    # 兜底：scene 检测可能 0 帧（短视频/画面静止），此时回退固定间隔抽帧，保证 ocr_frames 有输入。
    scene_threshold = "0.3"
    scene_cmd = [
        ffmpeg, "-y", "-i", str(mp4_path),
        "-strict", "unofficial",
        "-vf", f"select='gt(scene,{scene_threshold})',scale=720:-1",
        "-pix_fmt", "yuvj420p",
        "-vsync", "vfr", "-q:v", "2",
        str(frames / "frame_%03d.jpg"),
    ]
    run(scene_cmd, timeout=180)
    if not list(frames.glob("*.jpg")):
        print(f"[extract_media] scene detection produced 0 frames, falling back to fps=1/{fps_interval}", file=sys.stderr)
        frames_dir_clean = frames
        for old in frames_dir_clean.glob("*.jpg"):
            old.unlink()
        run([
            ffmpeg, "-y", "-i", str(mp4_path),
            "-strict", "unofficial",
            "-vf", f"fps=1/{fps_interval},scale=720:-1",
            "-pix_fmt", "yuvj420p",
            "-q:v", "2",
            str(frames / "frame_%03d.jpg"),
        ], timeout=180)
    run([
        ffmpeg,
        "-y",
        "-framerate",
        "1",
        "-i",
        str(frames / "frame_%03d.jpg"),
        "-vf",
        "tile=4x4:padding=8:margin=8,scale=960:-1",
        "-frames:v",
        "1",
        "-update",
        "1",
        str(contact_sheet),
    ], timeout=180)

    media_info = {}
    if ffprobe:
        p = subprocess.run([
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate",
            "-of",
            "json",
            str(mp4_path),
        ], text=True, capture_output=True)
        if p.returncode == 0 and p.stdout.strip():
            media_info = json.loads(p.stdout)
    return audio, contact_sheet, media_info


def transcribe(work_dir, audio, model_name="", skip=False):
    """Transcribe audio using Coze ASR service (cloud API, no local model needed).
    Uploads audio to object storage and calls ASR API.
    """
    if skip:
        return {"available": False, "skipped": True}

    started = time.time()
    audio_path = pathlib.Path(audio)
    if not audio_path.exists():
        return {"available": False, "error": f"Audio file not found: {audio}"}

    try:
        # Convert WAV to MP3 (ASR supports MP3 better)
        mp3_path = audio_path.with_suffix(".mp3")
        ffmpeg = _find_ffmpeg()
        if ffmpeg:
            subprocess.run(
                [ffmpeg, "-y", "-i", str(audio_path), "-acodec", "mp3", "-b:a", "64k", str(mp3_path)],
                capture_output=True, timeout=120,
            )
            audio_for_upload = mp3_path if mp3_path.exists() else audio_path
        else:
            audio_for_upload = audio_path

        # Upload to object storage
        from coze_coding_dev_sdk import S3SyncStorage, ASRClient

        s3 = S3SyncStorage()
        with open(audio_for_upload, "rb") as f:
            audio_bytes = f.read()
        object_key = s3.upload_file(audio_bytes, content_type="audio/mpeg")
        audio_url = s3.generate_presigned_url(object_key, expires=3600)

        # Call ASR
        asr = ASRClient(
            base_url=os.environ.get("COZE_ASR_BASE_URL", ""),
            api_key="",
        )
        result = asr.recognize(url=audio_url, format="mp3")

        # Parse result - ASR returns text directly
        transcript_text = result if isinstance(result, str) else (result.get("text", "") if isinstance(result, dict) else str(result))
        rows = [{"start": 0, "end": 0, "text": transcript_text.strip()}]

        transcript_json = {
            "language": "zh",
            "duration": round(time.time() - started, 1),
            "segments": rows,
            "elapsed_seconds": round(time.time() - started, 1),
            "model": "coze-asr",
        }
        (work_dir / "transcript.json").write_text(
            json.dumps(transcript_json, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (work_dir / "transcript.txt").write_text(
            transcript_text.strip(), encoding="utf-8"
        )
        return {
            "available": True,
            "segments": len(rows),
            "elapsed_seconds": transcript_json["elapsed_seconds"],
            "model": "coze-asr",
        }
    except Exception as exc:
        print(f"[asr] ASR transcription failed: {exc}", file=sys.stderr)
        return {"available": False, "error": str(exc)}


def ocr_frames_tesseract(work_dir):
    """Fallback: extract text from keyframes via pytesseract (Tesseract OCR).

    Gracefully degrades: if tesseract is unavailable, returns empty.
    """
    frames_dir = work_dir / "frames"
    if not frames_dir.is_dir():
        return {"available": False, "error": "no frames directory"}
    try:
        import pytesseract
        from PIL import Image
    except Exception as exc:
        return {"available": False, "error": f"pytesseract/PIL not available: {exc}"}

    tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        for candidate in (
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract",
        ):
            p = pathlib.Path(candidate)
            if p.exists():
                tesseract_cmd = candidate
                break
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    lines = []
    for img in sorted(frames_dir.glob("*.jpg")):
        try:
            text = pytesseract.image_to_string(Image.open(str(img)), lang="chi_sim+eng")
        except Exception as exc:
            print(f"[ocr] {img.name} failed: {exc}", file=sys.stderr)
            continue
        for ln in text.splitlines():
            ln = ln.strip()
            if ln:
                lines.append(ln)
    # dedupe, keep order
    seen, uniq = set(), []
    for ln in lines:
        if ln not in seen:
            seen.add(ln)
            uniq.append(ln)
    ocr_text = "\n".join(uniq)
    (work_dir / "ocr_result.txt").write_text(ocr_text, encoding="utf-8")
    return {"available": bool(uniq), "text": ocr_text, "frames_read": len(uniq)}


def ocr_frames(work_dir):
    """Extract image content from keyframes, VLM first (Coze/SiliconFlow), tesseract fallback.

    VLM understands image semantics (charts, products, scenes) beyond raw text, which
    matters for image/music videos. Falls back to tesseract OCR when LLM_PROVIDER=none.
    """
    frames_dir = work_dir / "frames"
    if not frames_dir.is_dir():
        return {"available": False, "error": "no frames directory"}

    # Cap how many frames we feed the VLM (scene detection can still yield many).
    frame_paths = sorted(frames_dir.glob("*.jpg"))
    if not frame_paths:
        return {"available": False, "error": "no frames extracted"}
    max_frames = int(os.environ.get("VLM_MAX_FRAMES", "8"))
    total = len(frame_paths)
    if total <= max_frames:
        selected = frame_paths
    elif max_frames <= 1:
        selected = frame_paths[:1]
    else:
        # 均匀选帧（含首尾）：避免只取开头 N 帧而漏掉视频中后段的关键画面
        idxs = sorted({round(i * (total - 1) / (max_frames - 1)) for i in range(max_frames)})
        selected = [frame_paths[i] for i in idxs]

    import llm as llm_mod

    provider = os.environ.get("LLM_PROVIDER", "coze")
    if provider == "none":
        return ocr_frames_tesseract(work_dir)

    single_prompt = (
        "这是一段视频的关键帧。请用中文描述图片内容："
        "1) 图片上所有可见的文字（原样提取，包括标题、标语、字幕、数字）；"
        "2) 图片展示的主体内容（产品/图表/场景/人物动作等）。"
        "简洁分点输出。"
    )

    # 优先一次请求带全部帧（省往返/成本），失败则逐帧兜底
    try:
        if len(selected) == 1:
            desc = llm_mod.describe_image(str(selected[0]), prompt=single_prompt)
            ocr_text = f"[{selected[0].name}] {desc}"
            frames_read = 1
        else:
            batch_prompt = (
                f"这是一段视频按时间顺序抽出的 {len(selected)} 张关键帧。"
                "请逐张用中文描述，每张单独一段、以'图N:'开头："
                "1) 该帧所有可见的文字（原样提取，包括标题、标语、字幕、数字）；"
                "2) 该帧展示的主体内容（产品/图表/场景/人物动作等）。"
                "简洁分点输出。"
            )
            ocr_text = llm_mod.describe_images([str(p) for p in selected], prompt=batch_prompt)
            frames_read = len(selected)
    except Exception as exc:
        print(f"[vlm] batch describe failed ({exc}), fallback to per-frame", file=sys.stderr)
        ocr_text = None

    if ocr_text is None:
        # 逐帧兜底（兼容单图/旧端点）
        descriptions = []
        for img in selected:
            try:
                desc = llm_mod.describe_image(str(img), prompt=single_prompt)
                descriptions.append(f"[{img.name}] {desc}")
            except Exception as exc:
                print(f"[vlm] {img.name} failed: {exc}", file=sys.stderr)
                continue
        if not descriptions:
            return ocr_frames_tesseract(work_dir)
        ocr_text = "\n\n".join(descriptions)
        frames_read = len(descriptions)

    (work_dir / "ocr_result.txt").write_text(ocr_text, encoding="utf-8")
    return {"available": True, "text": ocr_text, "frames_read": frames_read, "engine": "vlm"}


def build_low_cost_material(work_dir, material, max_chars):
    transcript_json_path = work_dir / "transcript.json"
    selected_segments = []
    transcript_stats = {"available": False}

    if transcript_json_path.exists():
        transcript_json = json.loads(transcript_json_path.read_text(encoding="utf-8"))
        segments = transcript_json.get("segments") or []
        transcript_stats = {
            "available": True,
            "language": transcript_json.get("language"),
            "duration": transcript_json.get("duration"),
            "segments": len(segments),
            "model": transcript_json.get("model"),
        }
        if segments:
            candidate_indexes = set()
            for idx in range(min(3, len(segments))):
                candidate_indexes.add(idx)
            for idx in range(max(0, len(segments) - 3), len(segments)):
                candidate_indexes.add(idx)
            slots = min(10, len(segments))
            if slots > 1:
                for slot in range(slots):
                    candidate_indexes.add(round(slot * (len(segments) - 1) / (slots - 1)))

            used_chars = 0
            for idx in sorted(candidate_indexes):
                row = segments[idx]
                text = (row.get("text") or "").strip()
                if not text:
                    continue
                if used_chars + len(text) > max_chars and selected_segments:
                    break
                selected_segments.append({
                    "start": row.get("start"),
                    "end": row.get("end"),
                    "text": text[: max(0, max_chars - used_chars)],
                })
                used_chars += len(text)
                if used_chars >= max_chars:
                    break

    preview_lines = [
        f"platform: {material.get('platform')}",
        f"id: {material.get('id')}",
        f"author: {material.get('author')}",
        f"description: {material.get('description')}",
        "",
        "selected transcript segments:",
    ]
    for row in selected_segments:
        preview_lines.append(f"[{row.get('start')}-{row.get('end')}] {row.get('text')}")
    if not selected_segments:
        preview_lines.append("(no transcript preview available)")
    ocr_result_path = work_dir / "ocr_result.txt"
    if ocr_result_path.exists():
        ocr_lines = [ln.strip() for ln in ocr_result_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        if ocr_lines:
            preview_lines.append("")
            preview_lines.append("ocr text from keyframes (image-only video):")
            preview_lines.extend(ocr_lines[:50])

    transcript_preview = work_dir / "transcript_preview.txt"
    transcript_preview.write_text("\n".join(preview_lines), encoding="utf-8")

    # OCR text from keyframes (image/music videos without speech)
    ocr_result = work_dir / "ocr_result.txt"
    ocr_text = ocr_result.read_text(encoding="utf-8").strip() if ocr_result.exists() else ""

    low_cost = {
        "mode": "low_cost_first",
        "instruction": (
            "Use this file before reading the full transcript or opening image artifacts. "
            "Escalate only when the user asks for exact wording, detailed timeline, visual UI steps, "
            "or when this preview is insufficient."
        ),
        "metadata": {
            "platform": material.get("platform"),
            "id": material.get("id"),
            "author": material.get("author"),
            "description": material.get("description"),
            "create_time": material.get("create_time"),
            "media_type": material.get("media_type"),
            "share_url": material.get("share_url"),
        },
        "media_info": material.get("media_info"),
        "transcript": transcript_stats,
        "selected_segments": selected_segments,
        "ocr_text": ocr_text or None,
        "omitted": {
            "full_transcript_path": material.get("paths", {}).get("transcript_txt"),
            "contact_sheet_path": material.get("paths", {}).get("contact_sheet"),
            "reason": "Omitted from default reading path to reduce model tokens.",
        },
        "recommended_read_order": [
            "low_cost_material.json",
            "transcript_preview.txt",
            "analysis_material.json",
            "ocr_text field (image text, when transcript is empty)",
            "transcript.txt only if exact coverage is required",
            "contact_sheet.jpg only if visual verification is required",
        ],
    }
    low_cost_path = work_dir / "low_cost_material.json"
    low_cost_path.write_text(json.dumps(low_cost, ensure_ascii=False, indent=2), encoding="utf-8")
    return low_cost_path, transcript_preview


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="WeChat Channels or Douyin share URL/text")
    parser.add_argument("--work-dir", required=True, help="Directory for intermediate files")
    parser.add_argument("--model", default="", help="(unused, kept for compatibility)")
    parser.add_argument("--frame-interval", type=int, default=5, help="Seconds between sampled frames")
    parser.add_argument("--douyin-cookie", default="", help="Optional user-provided Douyin Cookie header")
    parser.add_argument("--no-transcript", action="store_true", help="Skip ASR transcription")
    parser.add_argument("--low-cost-chars", type=int, default=2400, help="Max transcript preview characters for low-cost material")
    args = parser.parse_args()

    work_dir = pathlib.Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    platform = detect_platform(args.url)
    cookie = args.douyin_cookie or ""
    if platform == "wechat":
        metadata = parse_wechat(args.url, work_dir)
    else:
        metadata = parse_douyin(args.url, work_dir, cookie=cookie)

    (work_dir / "video_url.txt").write_text(metadata["video_url"], encoding="utf-8")
    mp4_path = work_dir / "input.mp4"
    download(metadata["video_url"], mp4_path, user_agent=metadata.get("download_user_agent") or DESKTOP_UA)
    audio, contact_sheet, media_info = extract_media(work_dir, mp4_path, args.frame_interval)
    transcript_status = transcribe(work_dir, audio, args.model, skip=args.no_transcript)

    # Image/music videos often have no speech -> transcription empty, info lives in frames.
    ocr_status = None
    if not transcript_status.get("available"):
        ocr_status = ocr_frames(work_dir)
        if ocr_status.get("available"):
            print(f"[ocr] extracted text from frames", file=sys.stderr)

    material = {
        **{k: v for k, v in metadata.items() if k not in {"video_url", "download_user_agent"}},
        "share_url": args.url,
        "paths": {
            "mp4": str(mp4_path),
            "audio": str(audio),
            "contact_sheet": str(contact_sheet),
            "profile": str(work_dir / "profile.json"),
            "transcript_txt": str(work_dir / "transcript.txt"),
            "transcript_json": str(work_dir / "transcript.json"),
            "low_cost_material": str(work_dir / "low_cost_material.json"),
            "transcript_preview": str(work_dir / "transcript_preview.txt"),
        },
        "media_info": media_info,
        "transcript": transcript_status,
        "ocr": ocr_status,
    }
    build_low_cost_material(work_dir, material, args.low_cost_chars)
    (work_dir / "analysis_material.json").write_text(json.dumps(material, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(material, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}", file=sys.stderr)
        raise
