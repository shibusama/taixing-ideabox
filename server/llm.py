# LLM 接口模块
# 支持两种 Provider：
#   LLM_PROVIDER=coze（默认）→ 使用 Coze 平台内置模型（LLMClient）
#   LLM_PROVIDER=siliconflow → 使用硅基流动（urllib 直调）
#   LLM_PROVIDER=none        → 模板回退（无网络请求）

import json
import os
import pathlib
import re
import base64
import urllib.request
import urllib.error

# ---------- 工具函数 ----------

_BASE_DIR = pathlib.Path(__file__).resolve().parent

def _load_dotenv():
    """加载 server/.env 文件"""
    env_path = _BASE_DIR / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def _get_provider():
    """获取 LLM 提供者（coze / siliconflow / none）"""
    return os.environ.get("LLM_PROVIDER", "coze").lower().strip()


def _strip_code_fence(text: str) -> str:
    """去掉 LLM 输出首尾可能包裹的 ```markdown / ``` 代码块标记，避免 markmap 解析失败。"""
    stripped = (text or "").strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        lines = lines[1:] if lines[0].startswith("```") else lines
        # 去掉结尾的 ```
        while lines and lines[-1].strip() == "```":
            lines.pop()
        stripped = "\n".join(lines).strip()
    return stripped


# ---------- Coze 平台 Provider ----------

def _chat_completion_coze(messages, temperature=0.4):
    """使用 Coze SDK 的 LLMClient 调用豆包模型"""
    from coze_coding_dev_sdk import LLMClient
    from coze_coding_utils.runtime_ctx.context import new_context
    from langchain_core.messages import HumanMessage, SystemMessage

    ctx = new_context(method="invoke")
    client = LLMClient(ctx=ctx)

    model = os.environ.get("LLM_MODEL", "doubao-seed-2-0-pro-260215")

    lc_messages = []
    for msg in messages:
        if msg["role"] == "system":
            lc_messages.append(SystemMessage(content=msg["content"]))
        elif msg["role"] == "user":
            lc_messages.append(HumanMessage(content=msg["content"]))

    resp = client.invoke(messages=lc_messages, model=model, temperature=temperature)
    return resp.content


def _describe_image_coze(image_path, prompt="请描述这张图片的内容，包括画面元素、文字、颜色和构图。"):
    """使用 Coze SDK 的 LLMClient 调用豆包模型分析图片"""
    from coze_coding_dev_sdk import LLMClient
    from coze_coding_utils.runtime_ctx.context import new_context
    from langchain_core.messages import HumanMessage

    ctx = new_context(method="invoke")
    client = LLMClient(ctx=ctx)

    model = os.environ.get("VLM_MODEL", "doubao-seed-2-0-pro-260215")

    b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    messages = [
        HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": data_url}},
        ])
    ]

    resp = client.invoke(messages=messages, model=model, temperature=0.2)
    return resp.content


# ---------- 硅基流动 Provider ----------

def _chat_completion(messages, temperature=0.4):
    """调用硅基流动 OpenAI 兼容 API"""
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = os.environ.get("LLM_BASE_URL", "https://api.siliconflow.cn/v1/chat/completions").rstrip("/")
    # 兼容 base URL（…/v1）与完整端点（…/v1/chat/completions）两种写法
    if not base_url.endswith("/chat/completions"):
        base_url += "/chat/completions"
    model = os.environ.get("LLM_MODEL", "zai-org/GLM-5.2")

    payload = json.dumps({"model": model, "messages": messages, "temperature": temperature}).encode()
    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def describe_image(image_path, prompt="请描述这张图片的内容，包括画面元素、文字、颜色和构图。"):
    """调用 VLM 视觉模型分析图片"""
    provider = _get_provider()
    if provider == "coze":
        return _describe_image_coze(image_path, prompt)

    # 硅基流动 VLM
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise ValueError("LLM_API_KEY not set for VLM image analysis")

    base_url = os.environ.get("LLM_BASE_URL", "https://api.siliconflow.cn/v1/chat/completions").rstrip("/")
    if not base_url.endswith("/chat/completions"):
        base_url += "/chat/completions"
    model = os.environ.get("VLM_MODEL", "Qwen/Qwen3-VL-32B-Instruct")

    b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode("utf-8")
    data_url = f"data:image/jpeg;base64,{b64}"

    payload = json.dumps({
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def _describe_images_coze(image_paths, prompt):
    """一次请求带多张图片，用 Coze SDK 调豆包 VLM 逐张分析。"""
    from coze_coding_dev_sdk import LLMClient
    from coze_coding_utils.runtime_ctx.context import new_context
    from langchain_core.messages import HumanMessage

    ctx = new_context(method="invoke")
    client = LLMClient(ctx=ctx)
    model = os.environ.get("VLM_MODEL", "doubao-seed-2-0-pro-260215")

    content = [{"type": "text", "text": prompt}]
    for image_path in image_paths:
        b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })
    messages = [HumanMessage(content=content)]
    resp = client.invoke(messages=messages, model=model, temperature=0.2)
    return resp.content


def describe_images(image_paths, prompt="请逐张描述这些图片的内容。"):
    """一次请求带多张图片让 VLM 逐张分析（省往返/成本），返回合并后的文本。

    image_paths: 按时间顺序排列的图片路径列表。
    """
    provider = _get_provider()
    if provider == "coze":
        return _describe_images_coze(image_paths, prompt)

    # 硅基流动 VLM（OpenAI 兼容：一条消息多个 image_url）
    api_key = os.environ.get("LLM_API_KEY", "")
    if not api_key:
        raise ValueError("LLM_API_KEY not set for VLM image analysis")

    base_url = os.environ.get("LLM_BASE_URL", "https://api.siliconflow.cn/v1/chat/completions").rstrip("/")
    if not base_url.endswith("/chat/completions"):
        base_url += "/chat/completions"
    model = os.environ.get("VLM_MODEL", "Qwen/Qwen3-VL-32B-Instruct")

    content = [{"type": "text", "text": prompt}]
    for image_path in image_paths:
        b64 = base64.b64encode(pathlib.Path(image_path).read_bytes()).decode("utf-8")
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
        })

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.2,
    }).encode()

    req = urllib.request.Request(
        base_url,
        data=payload,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


# ---------- 模板回退（无网络） ----------

def _template_mindmap(low_cost_material):
    """基于视频元数据生成简易思维导图"""
    title = low_cost_material.get("title", "未知视频")
    desc = low_cost_material.get("desc", "")
    author = low_cost_material.get("author", "未知作者")
    return f"""# {title}

## 基本信息
- **作者**: {author}
- **描述**: {desc}

## 视频概要
（视频内容摘要需要通过 ASR 转写获得，当前为无网络回退模式）
"""


def _template_note(low_cost_material):
    title = low_cost_material.get("title", "未知视频")
    desc = low_cost_material.get("desc", "")
    author = low_cost_material.get("author", "未知作者")
    return f"""# 视频笔记：{title}

**作者**: {author}  
**描述**: {desc}

---

> 笔记内容需要通过 ASR 转写获得，当前为无网络回退模式。
"""


# ---------- 公开接口 ----------

def generate_mindmap(low_cost_material, _preview=""):
    """
    根据视频素材生成 Markmap 思维导图
    返回: Markdown 格式的思维导图文本
    """
    provider = _get_provider()
    if provider == "none":
        return _template_mindmap(low_cost_material)

    meta = low_cost_material.get("metadata", {})
    title = meta.get("title") or meta.get("description") or "未知视频"
    desc = meta.get("description") or ""
    author = meta.get("author") or "未知作者"
    ocr = low_cost_material.get("ocr_text") or ""
    segments = low_cost_material.get("selected_segments") or []
    transcript = "\n".join(
        f"[{s.get('start', 0)}-{s.get('end', 0)}] {s.get('text', '')}"
        for s in segments
        if s.get("text")
    )

    system_prompt = """你是一个思维导图生成专家。请根据视频信息生成一个 Markmap 格式的思维导图。
要求：
1. 使用 Markdown 标题层级（# ## ###）表示树形结构
2. 根节点为视频标题
3. 第二层为：基本信息、视频内容、关键要点、总结
4. 内容要具体、有信息量，不要空洞
5. 如果提供了逐字稿，请基于逐字稿内容生成详细要点
6. 如果只有元数据，则基于标题和描述合理推断内容结构"""

    user_prompt = f"""视频标题：{title}
作者：{author}
描述：{desc}
{'逐字稿：' + transcript if transcript else ''}
{'画面文字：' + ocr if ocr else ''}
"""

    try:
        if provider == "coze":
            result = _chat_completion_coze([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        else:
            # siliconflow
            result = _chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        return _strip_code_fence(result)
    except Exception as e:
        return _template_mindmap(low_cost_material) + f"\n\n> LLM 生成失败: {e}"


def generate_note(low_cost_material, detail=False):
    """
    根据视频素材生成 Markdown 笔记
    detail=True → 详细笔记
    detail=False → 精简笔记
    """
    provider = _get_provider()
    if provider == "none":
        return _template_note(low_cost_material)

    meta = low_cost_material.get("metadata", {})
    title = meta.get("title") or meta.get("description") or "未知视频"
    desc = meta.get("description") or ""
    author = meta.get("author") or "未知作者"
    ocr = low_cost_material.get("ocr_text") or ""
    segments = low_cost_material.get("selected_segments") or []
    transcript = "\n".join(
        f"[{s.get('start', 0)}-{s.get('end', 0)}] {s.get('text', '')}"
        for s in segments
        if s.get("text")
    )

    if detail:
        system_prompt = """你是一个笔记整理专家。请根据视频信息生成一份详细的 Markdown 笔记。
要求：
1. 包含：标题、作者、时间、核心观点、详细内容、关键引述、个人思考
2. 结构清晰，使用标题和列表
3. 如果有逐字稿，请提取关键信息并整理成连贯的笔记"""
    else:
        system_prompt = """你是一个笔记整理专家。请根据视频信息生成一份精简的 Markdown 笔记。
要求：
1. 包含：标题、核心观点、关键要点
2. 简洁明了，控制在 300 字以内
3. 以要点列表形式呈现"""

    user_prompt = f"""视频标题：{title}
作者：{author}
描述：{desc}
{'逐字稿：' + transcript if transcript else ''}
{'画面文字：' + ocr if ocr else ''}
"""

    try:
        if provider == "coze":
            return _chat_completion_coze([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        else:
            return _chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
    except Exception as e:
        return _template_note(low_cost_material) + f"\n\n> LLM 生成失败: {e}"


def generate_image_prompt(video_metadata):
    """
    根据视频素材生成文生图提示词（用于 AI 封面图）
    从 low_cost_material.json 结构化字段读取标题/描述/逐字稿/画面文字，不截断。
    """
    provider = _get_provider()
    if provider == "none":
        return "信息图知识卡，包含标题、要点、模块化布局，中文文案清晰可读"

    meta = video_metadata.get("metadata", {})
    title = meta.get("title") or meta.get("description") or "视频"
    desc = meta.get("description") or ""
    segments = video_metadata.get("selected_segments") or []
    ocr = video_metadata.get("ocr_text") or ""
    transcript = "\n".join(
        f"[{s.get('start', 0)}-{s.get('end', 0)}] {s.get('text', '')}"
        for s in segments
        if s.get("text")
    )

    system_prompt = """You are a prompt engineer for generating content-rich infographic / knowledge-card images. The image MUST carry real readable text and structured information — NOT a decorative poster or movie cover.

Requirements:
1. The image is a vertical infographic / knowledge card with real Chinese text content
2. Extract the core message into a clear title + 3-6 key points / structured sections
3. Use a modular card layout: title area, key-point blocks, maybe a simple diagram or icon
4. All text must be short, accurate Chinese phrases (the model will render them into the image)
5. Include a simple, clean visual style appropriate to the topic — modern, organized, readable
6. Specify concrete layout and color direction (e.g. "clean light background, rounded info cards, soft colors")
7. Under 200 words, English instructions only, no explanations. The rendered text should be Chinese."""


    user_prompt = f"""视频标题：{title}
描述：{desc}
逐字稿：
{transcript}
画面文字：
{ocr}
请生成封面图提示词。"""

    try:
        if provider == "coze":
            return _chat_completion_coze([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        else:
            return _chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
    except Exception as e:
        return "信息图知识卡，竖版，标题 + 3-6 个要点模块，中文文案清晰，简洁现代配色，浅色背景圆角卡片"


def _parse_card_json(text: str) -> dict | None:
    """从 LLM 输出解析 {title, points, summary}。"""
    text = _strip_code_fence(text or "")
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            data = json.loads(text[start : end + 1])
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return None


def generate_cover_content(low_cost_material, transcript_preview=""):
    """从素材提炼知识卡片内容：{title, points(4-5), summary}。COVER_METHOD=svg 用。"""
    provider = _get_provider()
    meta = low_cost_material.get("metadata", {})
    title = meta.get("title") or meta.get("description") or "视频知识卡片"
    desc = meta.get("description") or ""
    segments = low_cost_material.get("selected_segments") or []
    transcript = "\n".join(
        f"[{s.get('start', 0)}-{s.get('end', 0)}] {s.get('text', '')}"
        for s in segments
        if s.get("text")
    )
    ocr = low_cost_material.get("ocr_text") or ""

    def _template():
        pts = []
        for s in segments[:5]:
            t = (s.get("text") or "").strip()
            if t:
                pts.append(t[:22])
        if not pts:
            pts = ["从视频中提炼的核心要点", "结构化呈现关键信息", "适合快速阅读的知识卡片"]
        return {"title": title, "points": pts[:5], "summary": (desc or "AI 生成的知识卡片")[:30]}

    if provider == "none":
        return _template()

    system_prompt = """你是知识卡片文案专家。根据视频素材提炼竖版知识卡片内容，只输出 JSON（不要 markdown 代码块）：
{"title": "不超过12个字的标题", "points": ["4到5个要点，每个不超过16字"], "summary": "一句话总结，不超过24字"}
要点要具体、有信息量，基于逐字稿/画面文字提炼。"""
    user_prompt = f"""视频标题：{title}
描述：{desc}
{'逐字稿：' + transcript if transcript else ''}
{'画面文字：' + ocr if ocr else ''}
请提炼知识卡片内容。"""

    try:
        if provider == "coze":
            result = _chat_completion_coze([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        else:
            result = _chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        data = _parse_card_json(result)
        if data and data.get("points"):
            return {
                "title": str(data.get("title") or title)[:24],
                "points": [str(p)[:40] for p in data.get("points", []) if str(p).strip()][:5],
                "summary": str(data.get("summary") or "")[:48],
            }
    except Exception as e:
        print(f"[cover] generate_cover_content failed: {e}", file=sys.stderr)
    return _template()


def generate_bg_prompt(low_cost_material, card=None):
    """生成无文字背景图提示词（竖版，供 COVER_METHOD=svg 叠字用）。"""
    provider = _get_provider()
    meta = low_cost_material.get("metadata", {})
    title = meta.get("title") or meta.get("description") or "知识卡片"

    fallback = "现代简约渐变背景，柔和低饱和配色，竖版 9:16，无任何文字、无字母、无数字、无水印，纯背景图，中央留白适合叠加文字卡片"
    if provider == "none":
        return fallback

    system_prompt = """You generate a VERTICAL background image prompt for an infographic knowledge card.
The background must be a clean, modern, abstract scene WITHOUT ANY TEXT/letters/numbers/watermarks (real text will be overlaid later).
Specify: abstract gradient/soft shapes, low-saturation harmonious colors, vertical 9:16, generous blank center area for text overlay.
English, under 120 words, no explanations. End with: 无任何文字、无字母、无数字、无水印，纯背景图。"""
    user_prompt = f"主题：{title}\n请生成竖版无文字背景图提示词。"

    try:
        if provider == "coze":
            return _chat_completion_coze([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
        else:
            return _chat_completion([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ])
    except Exception as e:
        print(f"[cover] generate_bg_prompt failed: {e}", file=sys.stderr)
        return fallback


# 启动时自动加载 .env
_load_dotenv()