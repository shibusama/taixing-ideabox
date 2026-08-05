"""Smoke test: transcribe an existing audio.wav with faster-whisper.

Usage: .venv/Scripts/python.exe test_transcribe.py <work-dir-with-audio.wav>
"""

import json
import pathlib
import sys
import time

from faster_whisper import WhisperModel


def main():
    work_dir = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "work/0905ae1fcf595afd")
    audio = work_dir / "audio.wav"
    if not audio.exists():
        print(f"no audio at {audio}")
        sys.exit(1)

    started = time.time()
    print(f"loading model (small, int8, cpu)...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    print(f"model loaded in {time.time() - started:.1f}s")

    started = time.time()
    segments, info = model.transcribe(
        str(audio), language="zh", vad_filter=True, beam_size=5
    )
    rows = [
        {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text.strip()}
        for seg in segments
    ]
    print(f"transcribed in {time.time() - started:.1f}s | language={info.language} duration={info.duration:.1f}s segments={len(rows)}")

    out = work_dir / "transcript.json"
    out.write_text(
        json.dumps(
            {"language": info.language, "duration": info.duration, "segments": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (work_dir / "transcript.txt").write_text(
        "\n".join(f"[{r['start']:06.2f}-{r['end']:06.2f}] {r['text']}" for r in rows),
        encoding="utf-8",
    )
    print(f"\n--- first 5 segments ---")
    for r in rows[:5]:
        print(f"[{r['start']:06.2f}-{r['end']:06.2f}] {r['text']}")


if __name__ == "__main__":
    main()
