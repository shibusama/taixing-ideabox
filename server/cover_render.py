"""COVER_METHOD=svg 的 AI 封面渲染：AI 生成无文字背景 + SVG 叠字。

文字由 SVG 真实渲染（100% 准确），AI 只负责背景图。
渲染后端按顺序尝试：
1. cairosvg（生产 Linux 装 libcairo2 后可用）
2. 本机 Edge/Chrome 无头截图（Windows 本地开发）
"""
from __future__ import annotations

import base64
import os
import pathlib
import shutil
import subprocess
import urllib.request

CARD_W = 1080
CARD_H = 1920

FONT_FAMILY = "Microsoft YaHei, SimHei, PingFang SC, Noto Sans CJK SC, sans-serif"


def download_image(url: str, dest) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as resp, open(dest, "wb") as f:
        f.write(resp.read())
    return dest


def _xml_escape(s) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _wrap_lines(text: str, max_chars: int = 16) -> list[str]:
    """按字符数折行（中文按字切）。"""
    text = str(text).strip()
    if not text:
        return [""]
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def build_card_svg(card: dict, bg_b64: str | None = None, mime: str = "image/jpeg") -> str:
    """生成 1080x1920 知识卡片 SVG。bg_b64 为背景图 base64（缺省用渐变）。"""
    title = str(card.get("title") or "视频知识卡片").strip()
    points = [str(p).strip() for p in (card.get("points") or []) if str(p).strip()][:5]
    summary = str(card.get("summary") or "").strip()

    parts = [f'<svg width="{CARD_W}" height="{CARD_H}" xmlns="http://www.w3.org/2000/svg">']

    if bg_b64:
        parts.append(
            f'<image href="data:{mime};base64,{bg_b64}" width="{CARD_W}" height="{CARD_H}" '
            f'preserveAspectRatio="xMidYMid slice"/>'
        )
        parts.append(f'<rect width="{CARD_W}" height="{CARD_H}" fill="#000000" fill-opacity="0.12"/>')
    else:
        parts.append(
            '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            '<stop offset="0" stop-color="#f5e1ff"/><stop offset="1" stop-color="#fff2cd"/>'
            "</linearGradient></defs>"
        )
        parts.append(f'<rect width="{CARD_W}" height="{CARD_H}" fill="url(#bg)"/>')

    # 标题
    parts.append(
        f'<text x="{CARD_W // 2}" y="330" text-anchor="middle" font-family="{FONT_FAMILY}" '
        f'font-size="84" font-weight="bold" fill="#ffffff">{_xml_escape(title)}</text>'
    )
    parts.append(
        f'<line x1="{CARD_W // 2 - 120}" y1="372" x2="{CARD_W // 2 + 120}" y2="372" '
        f'stroke="#ffffff" stroke-width="4" stroke-opacity="0.8"/>'
    )

    # 要点卡片
    top_y, gap, card_x, card_w = 470, 40, 80, CARD_W - 160
    n = max(len(points), 1)
    card_h = (CARD_H - top_y - 300 - (n - 1) * gap) // n
    for i, p in enumerate(points):
        y = top_y + i * (card_h + gap)
        parts.append(
            f'<rect x="{card_x}" y="{y}" width="{card_w}" height="{card_h}" rx="24" '
            f'fill="#ffffff" fill-opacity="0.93"/>'
        )
        parts.append(f'<circle cx="{card_x + 56}" cy="{y + card_h // 2}" r="34" fill="#7c6cf0"/>')
        parts.append(
            f'<text x="{card_x + 56}" y="{y + card_h // 2 + 14}" text-anchor="middle" '
            f'font-family="{FONT_FAMILY}" font-size="40" font-weight="bold" fill="#ffffff">{i + 1}</text>'
        )
        lines = _wrap_lines(p, 16)[:2]
        base_y = y + card_h // 2 - (14 if len(lines) == 2 else 0)
        for li, ln in enumerate(lines):
            parts.append(
                f'<text x="{card_x + 124}" y="{base_y + li * 50 + 14}" '
                f'font-family="{FONT_FAMILY}" font-size="42" fill="#333333">{_xml_escape(ln)}</text>'
            )

    # 总结
    if summary:
        sy = top_y + n * (card_h + gap) + 46
        parts.append(
            f'<text x="{CARD_W // 2}" y="{sy}" text-anchor="middle" font-family="{FONT_FAMILY}" '
            f'font-size="38" fill="#ffffff">{_xml_escape(summary[:24])}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def _find_edge() -> str | None:
    for p in (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ):
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("chrome")


def _render_svg_via_cairo(svg: str, out_png) -> None:
    import cairosvg
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out_png), output_width=CARD_W, output_height=CARD_H)


def _render_svg_via_edge(svg: str, out_png) -> None:
    edge = _find_edge()
    if not edge:
        raise RuntimeError("Edge/Chrome not found for SVG rendering")
    out_png = pathlib.Path(out_png)
    work = out_png.parent
    svg_path = work / "card_render.svg"
    svg_path.write_text(svg, encoding="utf-8")
    profile = work / "edge_profile"
    cmd = [
        edge, "--headless=new", "--disable-gpu", "--hide-scrollbars",
        f"--user-data-dir={profile}", f"--window-size={CARD_W},{CARD_H}",
        f"--screenshot={out_png}", svg_path.resolve().as_uri(),
    ]
    subprocess.run(cmd, timeout=90, capture_output=True)
    if not out_png.exists():
        raise RuntimeError("Edge screenshot failed")


def render_card(bg_source, card: dict, out_png) -> str:
    """bg_source: 背景图 URL 或本地文件路径；card: {title, points[], summary}。返回最终 PNG 路径。"""
    out_png = pathlib.Path(out_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)

    if str(bg_source).startswith(("http://", "https://")):
        tmp = out_png.parent / "bg_raw"
        download_image(bg_source, tmp)
        data = tmp.read_bytes()
    else:
        data = pathlib.Path(bg_source).read_bytes()
    mime = "image/png" if data[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
    bg_b64 = base64.b64encode(data).decode("ascii")

    svg = build_card_svg(card, bg_b64=bg_b64, mime=mime)
    try:
        _render_svg_via_cairo(svg, out_png)
    except Exception:
        _render_svg_via_edge(svg, out_png)
    return str(out_png)
