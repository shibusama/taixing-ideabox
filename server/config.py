"""IdeaBox global configuration — env vars, paths, shared objects."""

import os
import pathlib
import threading
from concurrent.futures import ThreadPoolExecutor

from db import init_db

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

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="mindmap")

# In-memory task progress (survives task lifetime, not persisted)
cover_progress: dict[str, str] = {}
mindmap_progress: dict[str, str] = {}

# Per-key lock to prevent concurrent video processing for the same URL
material_locks: dict[str, threading.Lock] = {}