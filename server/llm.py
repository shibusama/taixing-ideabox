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

NOTE_SYSTEM_PROMPT = (
    "你是内容分析师。根据提供的视频/图文元信息与转录文本，生成一份结构化的 Markdown 笔记。\n"
    "要求：\n"
    "- 以 `# 标题` 开头（概括内容主题）\n"
    "- 必须包含：来源信息、一句话总结、要点归纳\n"
    "- 时间线、金句、行动建议仅在转录文本充分时补充；转录不足时明确标注“转录不完整”\n"
    "- 只输出 Markdown 笔记本身，不要任何多余解释或代码块包裹\n"
)

# 标准笔记 vs 详细笔记：detail=True 时追加结构分析部分
NOTE_TEMPLATE = """\
# {title}

> 来源：{url}

## 基本信息

- 平台：{platform}
- 作者：{author}
- 时长：{duration}

## 一句话总结

{summary}

## 要点归纳

{key_points}

## 转录情况

- 状态：{transcript_status}
{transcript_detail}
"""


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


def _template_note(low_cost, url, detail=False):
    """Fallback: build a standard note from metadata + sampled transcript only."""
    meta = low_cost.get("metadata", {})
    segments = low_cost.get("selected_segments", [])
    media = low_cost.get("media_info") or {}
    fmt = media.get("format") or {}
    transcript_stats = low_cost.get("transcript") or {}
    has_transcript = bool(transcript_stats.get("available") or segments)

    duration = ""
    if fmt.get("duration"):
        try:
            duration = f"{round(float(fmt['duration']))} 秒"
        except (TypeError, ValueError):
            duration = ""
    if not duration and transcript_stats.get("duration"):
        duration = f"{transcript_stats['duration']} 秒"

    title = (meta.get("description") or "视频笔记").strip()[:80] or "视频笔记"
    lines = [
        f"# {title}",
        "",
        f"> 来源：{url}",
        "",
        "## 基本信息",
        "",
        f"- 平台: {meta.get('platform') or '未知'}",
        f"- 作者: {meta.get('author') or '未知'}",
        f"- 时长: {duration or '未知'}",
        "",
        "## 一句话总结",
        "",
        "- （未配置 LLM，暂无法生成总结）",
        "",
        "## 要点归纳",
        "",
    ]
    if has_transcript and segments:
        lines.append("- 转录采样：")
        for row in segments:
            stamp = f"{row.get('start', 0):.0f}s"
            text = (row.get("text") or "").strip()
            if text:
                lines.append(f"  - [{stamp}] {text[:80]}")
    else:
        lines.append("- 暂无转写文本（未安装转写服务或转写失败）")

    lines.append("")
    lines.append("## 说明")
    lines.append("- 配置 LLM_API_KEY 后可生成更详细的笔记")
    lines.append("- 设置环境变量 LLM_PROVIDER + LLM_BASE_URL + LLM_MODEL 即可启用")
    if detail:
        lines.append("")
        lines.append("## 结构分析")
        lines.append("- （未配置 LLM，暂无法生成结构分析）")
    return "\n".join(lines)


def generate_note(low_cost, url, transcript_preview="", detail=False):
    """Return a structured Markdown note for the given content."""
    provider = os.environ.get("LLM_PROVIDER", "none").lower()
    api_key = os.environ.get("LLM_API_KEY", "")

    meta = low_cost.get("metadata", {})
    segments = low_cost.get("selected_segments", [])
    transcript_stats = low_cost.get("transcript") or {}
    has_transcript = bool(transcript_stats.get("available") or segments)

    media = low_cost.get("media_info") or {}
    fmt = media.get("format") or {}
    duration = ""
    if fmt.get("duration"):
        try:
            duration = f"{round(float(fmt['duration']))} 秒"
        except (TypeError, ValueError):
            duration = ""
    if not duration and transcript_stats.get("duration"):
        duration = f"{transcript_stats['duration']} 秒"

    title = (meta.get("description") or "视频笔记").strip()[:80] or "视频笔记"

    if provider == "none" or not api_key:
        return _template_note(low_cost, url, detail=detail)

    sections = (
        "按以下 Markdown 结构生成（只输出笔记正文）：\n"
        f"# {title}\n\n"
        f"> 来源：{url}\n\n"
        "## 基本信息\n"
        "- 平台/作者/时长（用给出的元信息填充）\n\n"
        "## 一句话总结\n"
        "- 用 1-2 句话概括内容\n\n"
        "## 要点归纳\n"
        "- 3-7 条核心要点，每条一行\n"
    )
    if detail:
        sections += (
            "## 结构分析\n"
            "- 分析内容结构：开场如何抓人、信息如何推进、高潮与结尾\n"
            "## 可复用方法\n"
            "- 提炼可迁移的表达/方法，附失败边界\n"
        )
    sections += (
        f"## 转录情况\n"
        f"- 状态：{'完整转录' if has_transcript else '转录不完整'}\n"
    )
    if not has_transcript:
        sections += "- 转录文本不足，要点仅基于元信息，请明确标注“转录不完整”\n"

    user_prompt = (
        f"视频/图文信息:\n"
        f"- 平台: {meta.get('platform')}\n"
        f"- 作者: {meta.get('author')}\n"
        f"- 描述: {meta.get('description')}\n"
        f"- 时长: {duration}\n\n"
        f"转录采样文本:\n{transcript_preview or '(无)'}\n\n"
        f"{sections}"
    )
    try:
        return _chat_completion(
            provider,
            [
                {"role": "system", "content": NOTE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
    except Exception as exc:
        # Fall back to template so the pipeline never hard-fails on LLM issues.
        return _template_note(low_cost, url, detail=detail) + f"\n\n> LLM 生成失败，已回退模板: {exc}"
