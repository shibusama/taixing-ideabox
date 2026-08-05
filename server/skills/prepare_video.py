#!/usr/bin/env python
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request


WECHAT_PARSER_URL = "https://sph.litao.workers.dev/api/fetch_video_profile"
DOUYIN_DETAIL_URL = "https://www.douyin.com/aweme/v1/web/aweme/detail/?aweme_id={aweme_id}"
DOUYIN_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)
DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/138.0.0.0 Safari/537.36"


def run(cmd, timeout=None):
    return subprocess.run(cmd, timeout=timeout, check=True, text=True)


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


def parse_wechat(url, work_dir):
    payload = request_json(
        WECHAT_PARSER_URL,
        method="POST",
        payload={"url": url},
        headers={"Content-Type": "application/json; charset=utf-8", "User-Agent": DESKTOP_UA},
    )
    (work_dir / "profile.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    data = payload.get("data") or {}
    feed = data.get("feedInfo") or payload.get("feedInfo") or {}
    author = data.get("authorInfo") or payload.get("authorInfo") or {}
    video_url = (
        feed.get("videoUrl")
        or (feed.get("h264VideoInfo") or {}).get("videoUrl")
        or (feed.get("h265VideoInfo") or {}).get("videoUrl")
        or feed.get("originVideoUrl")
    )
    if not video_url:
        raise RuntimeError("No video URL returned by WeChat parser")
    return {
        "platform": "wechat",
        "id": str((data.get("sceneInfo") or {}).get("dynamicExportId") or "wechat_video"),
        "author": author.get("nickname"),
        "description": feed.get("description"),
        "create_time": feed.get("createtime"),
        "media_type": feed.get("mediaType"),
        "video_url": video_url,
        "download_user_agent": DESKTOP_UA,
    }


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
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required but was not found on PATH")

    audio = work_dir / "audio.wav"
    frames = work_dir / "frames"
    frames.mkdir(exist_ok=True)
    contact_sheet = work_dir / "contact_sheet.jpg"

    run([ffmpeg, "-y", "-i", str(mp4_path), "-vn", "-ac", "1", "-ar", "16000", str(audio)], timeout=180)
    run([
        ffmpeg,
        "-y",
        "-i",
        str(mp4_path),
        "-vf",
        f"fps=1/{fps_interval},scale=360:-1",
        "-q:v",
        "2",
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
        ffmpeg = shutil.which("ffmpeg")
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

    transcript_preview = work_dir / "transcript_preview.txt"
    transcript_preview.write_text("\n".join(preview_lines), encoding="utf-8")

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
        "omitted": {
            "full_transcript_path": material.get("paths", {}).get("transcript_txt"),
            "contact_sheet_path": material.get("paths", {}).get("contact_sheet"),
            "reason": "Omitted from default reading path to reduce model tokens.",
        },
        "recommended_read_order": [
            "low_cost_material.json",
            "transcript_preview.txt",
            "analysis_material.json",
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
    parser.add_argument("--frame-interval", type=int, default=10, help="Seconds between sampled frames")
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
