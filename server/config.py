"""IdeaBox global configuration — env vars, paths, shared objects."""

import os
import pathlib
from concurrent.futures import ThreadPoolExecutor

from db import init_db

BASE_DIR = pathlib.Path(__file__).parent


def _load_dotenv():
    """加载 server/.env 文件"""
    import pathlib
    env_path = pathlib.Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


_load_dotenv()
init_db()

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="task")

# In-memory task progress (survives task lifetime, not persisted)
cover_progress: dict[str, str] = {}
mindmap_progress: dict[str, str] = {}
