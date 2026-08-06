"""LLM integration point for mindmap generation.

Provider is selected via env vars:
  LLM_PROVIDER = none | openai-compatible | siliconflow   (default: none -> template fallback)
  LLM_API_KEY  = your api key
  LLM_BASE_URL = e.g. https://api.siliconflow.cn/v1 (OpenAI-compatible chat completions)
  LLM_MODEL    = e.g. Qwen/Qwen2.5-7B-Instruct

Until an API key is configured the server returns a template mindmap built from
video metadata + sampled transcript, so the whole pipeline stays testable.
"""

import json
import os
import pathlib
import urllib.request


def _load_dotenv():
    """Minimal .env loader (server/.env), never overrides real env vars."""
    env_path = pathlib.Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv()

SYSTEM_PROMPT = (
    "你是视频内容分析师。根据提供的视频元信息与转录文本，生成一份 Markdown 思维导图（markmap 格式）。\n"
    "要求：\n"
    "- 根节点用 `# 标题`（概括视频主题）\n"
    "- 用 `##` / `###` 层级组织分支\n"
    "- 分支覆盖：一句话总结、核心观点、时间线（如有）、行动建议（如有）\n"
    "- 只输出 markdown 思维导图本身，不要任何多余解释或代码块包裹\n"
)


def _template_mindmap(low_cost):
    """Fallback: build a useful mindmap from metadata + sampled transcript only."""
    meta = low_cost.get("metadata", {})
    segments = low_cost.get("selected_segments", [])
    media = low_cost.get("media_info") or {}
    fmt = media.get("format") or {}

    lines = []
    title = (meta.get("description") or "视频摘要").strip() or "视频摘要"
    lines.append(f"# {title[:80]}")

    lines.append("## 视频信息")
    if meta.get("platform"):
        lines.append(f"- 平台: {meta['platform']}")
    if meta.get("author"):
        lines.append(f"- 作者: {meta['author']}")
    if fmt.get("duration"):
        lines.append(f"- 时长: {round(float(fmt['duration']))} 秒")
    lines.append("- 状态: 模板导图（LLM 未配置）")

    if segments:
        lines.append("## 转录采样")
        for row in segments:
            stamp = f"{row.get('start', 0):.0f}s"
            text = (row.get("text") or "").strip()
            if text:
                lines.append(f"- [{stamp}] {text[:80]}")
    else:
        lines.append("## 转录")
        lines.append("- 暂无转写文本（未安装 faster-whisper 或转写失败）")

    lines.append("## 说明")
    lines.append("- 配置 LLM_API_KEY 后可生成更详细的思维导图")
    lines.append("- 设置环境变量 LLM_PROVIDER + LLM_BASE_URL + LLM_MODEL 即可启用")
    return "\n".join(lines)


def _chat_completion(provider, messages):
    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    if provider == "siliconflow" and not base_url:
        base_url = "https://api.siliconflow.cn/v1"
    model = os.environ.get("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    api_key = os.environ.get("LLM_API_KEY", "")

    payload = {"model": model, "messages": messages, "temperature": 0.4}
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


def generate_mindmap(low_cost, transcript_preview="", analysis=None):
    """Return markmap-format markdown for the given video material."""
    provider = os.environ.get("LLM_PROVIDER", "none").lower()
    api_key = os.environ.get("LLM_API_KEY", "")

    if provider == "none" or not api_key:
        return _template_mindmap(low_cost)

    meta = low_cost.get("metadata", {})
    segments = low_cost.get("selected_segments", [])
    user_prompt = (
        f"视频信息:\n"
        f"- 平台: {meta.get('platform')}\n"
        f"- 作者: {meta.get('author')}\n"
        f"- 描述: {meta.get('description')}\n\n"
        f"转录采样文本:\n{transcript_preview or '(无)'}\n\n"
        f"请生成 markmap 思维导图 markdown。"
    )
    try:
        return _chat_completion(
            provider,
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        # Fall back to template so the pipeline never hard-fails on LLM issues.
        return _template_mindmap(low_cost) + f"\n\n> LLM 生成失败，已回退模板: {exc}"


def describe_image(image_path, prompt="请描述这张图片的内容，提取所有可见的文字、图表、产品或关键信息。"):
    """Describe an image using a vision LLM (VLM) via the same OpenAI-compatible channel.

    Reuses LLM_BASE_URL / LLM_API_KEY; model is VLM_MODEL (default Qwen-VL on SiliconFlow).
    Returns a text description, or raises on failure.
    """
    import base64

    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise RuntimeError("LLM_API_KEY 未配置")

    base_url = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    if not base_url:
        base_url = "https://api.siliconflow.cn/v1"
    model = os.environ.get("VLM_MODEL", "Qwen/Qwen3-VL-8B-Instruct")

    b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": data_url}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()
