"""Regenerate all cached mindmaps with real transcription (in-memory, no file writes).

For each cached URL:
  1. transcribe work/{hash}/audio.wav if transcript.json is missing
  2. build low_cost dict + transcript preview IN MEMORY (no file overwrites)
  3. call LLM to regenerate the mindmap
  4. update the mindmaps table

Usage: .venv/Scripts/python.exe regenerate_mindmaps.py [url_hash ...]
"""

import importlib.util
import json
import pathlib
import sys
import time

import llm
from db import SessionLocal
from models import Mindmap

BASE_DIR = pathlib.Path(__file__).parent
WORK_ROOT = BASE_DIR / "work"
SKILL_SCRIPT = pathlib.Path(
    r"C:\Users\13191\.codex\skills\video-link-summarizer\scripts\prepare_video.py"
)

spec = importlib.util.spec_from_file_location("prepare_video", SKILL_SCRIPT)
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)

MAX_CHARS = 2400


def get_transcript(work_dir):
    """Return segments list, using cached transcript.json if present."""
    transcript_json = work_dir / "transcript.json"
    if transcript_json.exists():
        data = json.loads(transcript_json.read_text(encoding="utf-8"))
        return data.get("segments") or []
    audio = work_dir / "audio.wav"
    if not audio.exists():
        return []
    started = time.time()
    print(f"  transcribing {audio.name} ...")
    pv.transcribe(work_dir, audio, "small", skip=False)
    print(f"  transcription took {time.time() - started:.1f}s")
    data = json.loads(transcript_json.read_text(encoding="utf-8"))
    return data.get("segments") or []


def build_preview(segments):
    """Select a representative sample (head/tail/evenly spaced) as before."""
    if not segments:
        return "(no transcript available)"
    candidate_indexes = set()
    for idx in range(min(3, len(segments))):
        candidate_indexes.add(idx)
    for idx in range(max(0, len(segments) - 3), len(segments)):
        candidate_indexes.add(idx)
    slots = min(10, len(segments))
    if slots > 1:
        for slot in range(slots):
            candidate_indexes.add(round(slot * (len(segments) - 1) / (slots - 1)))

    used = 0
    rows = []
    for idx in sorted(candidate_indexes):
        text = (segments[idx].get("text") or "").strip()
        if not text:
            continue
        if used + len(text) > MAX_CHARS and rows:
            break
        rows.append(f"[{segments[idx].get('start', 0)}-{segments[idx].get('end', 0)}] {text[:max(0, MAX_CHARS - used)]}")
        used += len(text)
        if used >= MAX_CHARS:
            break
    return "\n".join(rows) if rows else "(no transcript available)"


def main():
    targets = sys.argv[1:] or None

    with SessionLocal() as db:
        rows = db.query(Mindmap).all()

    for row in rows:
        if targets and row.url_hash not in targets:
            continue
        work_dir = WORK_ROOT / row.url_hash
        print(f"\n=== {row.url_hash} ({row.url[:60]}) ===")
        if not work_dir.exists():
            print("  no work dir, skipping")
            continue

        segments = get_transcript(work_dir)
        preview = build_preview(segments)

        # Reuse the stored low_cost_material.json for metadata (read-only)
        low_cost_path = work_dir / "low_cost_material.json"
        if not low_cost_path.exists():
            print("  no low_cost_material.json, skipping")
            continue
        low_cost = json.loads(low_cost_path.read_text(encoding="utf-8"))
        low_cost["transcript"] = {
            "available": bool(segments),
            "segments": len(segments),
        }

        md = llm.generate_mindmap(low_cost, preview)
        with SessionLocal() as db:
            m = db.get(Mindmap, row.id)
            if m:
                m.mindmap_md = md
                db.commit()
        print(f"  mindmap regenerated: {len(md)} chars")


if __name__ == "__main__":
    main()
