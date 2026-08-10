# 灵感匣后端 (server/)

灵感匣「视频链接 → 思维导图 / Markdown 笔记 / AI 封面」功能 + 数据存储后端，FastAPI + SQLAlchemy（PostgreSQL 生产 / SQLite 本地）。

## 架构

```
前端 React (markmap 渲染 / Markdown 渲染 / 图片展示)
   │  POST /api/mindmap|note|cover {url}  → {task_id}   （后台线程执行）
   │  GET  /api/mindmap|note|cover/{task_id}            （轮询：pending/running/done/error）
   │  GET/POST/PUT/DELETE /api/ideas                    （灵感 CRUD）
   ▼
FastAPI (server/app.py)
   │  调用 skill 脚本 prepare_video.py
   ▼
解析管线（下载 MP4 → 提取音频 → Coze 云 ASR 转写 → 抽帧 VLM/OCR）
   │  产出 transcript.txt / transcript.json
   ▼
LLM 生成（三种出口，共用同一份材料）：
   ├─ generate_mindmap()      → markmap 思维导图
   ├─ generate_note()         → Markdown 笔记（detail 可切详细模式）
   └─ generate_image_prompt() → 文生图提示词 → 火山方舟 seedream 出图（AI 封面）
   ▼
数据库持久化（mindmaps / notes / covers 表，按 URL sha256 缓存，重复解析秒回）
```

## 数据存储

| 环境 | 数据库 | 配置方式 |
|------|--------|----------|
| 本地开发 | SQLite（`server/ideabox.db`，首次启动自动建表） | 无 `PGDATABASE_URL` 时默认 |
| 生产（Coze） | PostgreSQL | 环境变量 `PGDATABASE_URL` |

6 张表：

| 表 | 用途 | 说明 |
|----|------|------|
| `ideas` | 灵感主表 | 软删除（`deleted_at`），置顶/标签 JSON 数组 |
| `tags` | 标签冗余表 | name 唯一 + count 计数，写操作后重建 |
| `mindmaps` | 视频导图缓存 | url_hash 唯一索引，存 markmap MD |
| `notes` | Markdown 笔记缓存 | url_hash 唯一索引，存结构化笔记 + detail 标记 |
| `covers` | AI 封面缓存 | url_hash 唯一索引，存图片 URL + 提示词 |
| `tasks` | 解析任务状态 | 持久化，服务重启后 pending/running 置为 error |

> PostgreSQL 表需手动建表（`Base.metadata.create_all()`，仅 SQLite 自动建）。本地和线上连同一个库才能共享数据。
> 新增表的建表 SQL 见 `server/migrations/`（`create_notes.sql` / `create_covers.sql`），生产库需手动执行。

前端数据从 LocalStorage 迁移到后端 API（`src/hooks/useIdeas.js`），首次加载时若数据库为空且浏览器仍有旧 LocalStorage 数据会自动导入一次。

## 启动

```bash
cd server
pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
# → http://127.0.0.1:8000/api/health（同源托管前端 dist/，单进程）
```

后端会自动读取 `server/.env`（若存在）注入环境变量，无需手动设置。`.env` 已 gitignore，**不要提交密钥**。常用变量：

```bash
# 连接 PostgreSQL（不设则回退 SQLite）
PGDATABASE_URL=postgresql://user:pass@host:5432/db

# 视频号解析凭据（/api/sph/resolve 必需，元宝 cookie）
HY_TOKEN=your_cookie_string

# 语音转文字：coze(默认) / groq(云端 Whisper) / local(faster-whisper 本地兜底)
ASR_PROVIDER=groq
GROQ_API_KEY=gsk_xxx
# WHISPER_MODEL=Systran/faster-whisper-small

# AI 封面方式：ai(默认，AI 画带文字整图) / svg(AI 画无文字背景 + SVG 叠字，文字 100% 准确)
COVER_METHOD=svg
```

## 视频号解析（/api/sph/resolve）

解析视频号分享链接为可播放/下载的视频直链。两步纯 HTTP：
1. 腾讯元宝 API 换取 exportId/token（需 `HY_TOKEN` cookie）
2. 微信频道 API 换取 videoUrl

- **必需**：`HY_TOKEN`（腾讯元宝登录 cookie），未配置返回 400
- **非官方接口**：`server/app.py` 硬编码了特定账号的请求头，腾讯侧变动/风控会导致失败
- **安全**：`HY_TOKEN` 是登录凭据，只能放 `.env` / Coze 环境变量，绝不提交 Git

## 依赖 skill

后端解析视频需要 `prepare_video.py`（视频号/抖音链接 → 下载/转写）。位置解析：

1. 环境变量 `SKILL_SCRIPT_PATH`（可指向任意路径）
2. 默认回退到仓库内副本 `server/skills/prepare_video.py`（已随仓库提交，开箱即用）

系统依赖：`ffmpeg` / `ffprobe`（需在 PATH）。转写由 `ASR_PROVIDER` 决定：`coze`（默认，仅 Coze 环境可用）/ `groq`（Groq Whisper API，需 `GROQ_API_KEY`）/ `local`（faster-whisper 本地模型，离线可用；groq 失败自动回退本地）。

## 视频信息提取（ASR + VLM）

`prepare_video.py` 从视频提取信息，两条路径：

| 路径 | 用途 | 说明 |
|---|---|---|
| **ASR 语音转写** | 提取视频里"说的话" | `ASR_PROVIDER=coze`（默认）/ `groq` / `local`，带时间戳 |
| **VLM 视觉理解** | 提取图片/画面内容（转写为空时触发） | Qwen-VL 理解关键帧语义 + 提取文字 |

**VLM（视觉语言模型）**：当 ASR 转写为空（如图片 + 背景音乐视频），`prepare_video.py` 用 Qwen-VL（`server/llm.py` 的 `describe_image()`）逐帧理解图片内容。关键帧用 ffmpeg **场景检测**抽取（只保留画面变化的帧，上限 `VLM_MAX_FRAMES` 默认 8）。

**降级**：VLM 未配置 key 时回退 tesseract OCR（需系统装 tesseract + 中文包）；都不可用时跳过，不影响主流程。

## 前端 API 地址配置

前端 `src/config.js` 按优先级解析后端地址：
1. `window.APP_CONFIG.apiBase`（生产最灵活：在 index.html 里注入，改一行即可切换后端）
2. `VITE_API_BASE` 环境变量（Vite 构建期）
3. 默认：开发环境 `http://127.0.0.1:8000`；生产环境同源 `/api`（由后端统一服务）

## 启用 LLM 深度功能（可选）

未配置时后端输出模板（元信息 + 转录采样），用于跑通全流程。
要启用 AI 分析（导图/笔记/封面），配置 `LLM_PROVIDER` 选择模型提供商：

**两种 Provider（`LLM_PROVIDER`，默认 `coze`）+ 独立生图**

| Provider | 适用环境 | 模型 |
|----------|---------|------|
| `coze` | Coze 部署（有 `coze_coding_dev_sdk`）| 豆包文本 / seedream 文生图 |
| `siliconflow` | 本地开发（需 API key）| GLM-5.2 / Qwen3-VL-32B / Z-Image |
| `none` | 无网络 | 模板回退 |

**AI 封面出图（`_text_to_image`）默认走火山方舟 Agent Plan**（配置了 `ARK_API_KEY` 时优先，走 `/api/plan/v3` 端点，用套餐额度不计费），否则回退 SiliconFlow / Coze。

本地开发用 `server/.env`（已 gitignore，注意**不要提交 key**）：

```bash
# 硅基流动（文本 + VLM 共用 key）
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-xxx
LLM_MODEL=zai-org/GLM-5.2               # 文本生成（导图/笔记/封面提示词）
VLM_MODEL=Qwen/Qwen3-VL-32B-Instruct     # 关键帧视觉理解

# 火山方舟 Agent Plan 生图（默认生图方式）
ARK_API_KEY=ark-xxx
ARK_IMAGE_MODEL=doubao-seedream-5.0-lite
ARK_IMAGE_SIZE=1920x1920
ARK_IMAGE_ENDPOINT=https://ark.cn-beijing.volces.com/api/plan/v3/images/generations
```

> 代码默认值（`server/llm.py` / `server/app.py`）：`LLM_MODEL` = `zai-org/GLM-5.2`，`VLM_MODEL` = `Qwen/Qwen3-VL-32B-Instruct`（siliconflow 分支）；生图默认走火山方舟 `doubao-seedream-5.0-lite`（配置 ARK_API_KEY 时）。早期默认的 `Qwen2.5-7B-Instruct` 输出大量乱码，已弃用。未配置 key 时全部回退模板。
> 本地与 Coze 互不影响：`.env` 显式设 `siliconflow` 走硅基流动，Coze 无 `.env` 默认 `coze`。`_text_to_image`（AI 封面出图）优先火山方舟，其次按 provider 分叉。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ideas` | 灵感列表（不含归档） |
| GET | `/api/ideas/archived` | 归档列表 |
| POST | `/api/ideas` | 创建灵感 |
| PUT | `/api/ideas/{id}` | 更新灵感（content/tags/pinned） |
| DELETE | `/api/ideas/{id}` | 软删除 → 移入归档 |
| POST | `/api/ideas/{id}/restore` | 从归档恢复 |
| POST | `/api/ideas/{id}/pin` | 切换置顶 |
| DELETE | `/api/archived` | 清空回收站（物理删除） |
| GET | `/api/tags` | 标签计数 |
| GET | `/api/export` | 导出全部数据 JSON |
| POST | `/api/import` | 整体导入替换（ideas+archived） |
| POST | `/api/mindmap` | `{"url"}` → `{"task_id"}` 或缓存命中 `{"result"}` |
| GET | `/api/mindmap/{task_id}` | `{"status", "result": {"mindmap_md", "cached"}, "error"}` |
| POST | `/api/note` | `{"url", "detail"}` → `{"task_id"}` 或缓存命中 `{"result"}`；`detail=true` 输出详细笔记 |
| GET | `/api/note/{task_id}` | `{"status", "result": {"note_md", "detail", "cached"}, "error"}` |
| POST | `/api/cover` | `{"url"}` → `{"task_id"}` 或缓存命中 `{"result"}` |
| GET | `/api/cover/{task_id}` | `{"status", "result": {"image_url", "prompt", "cached"}, "error"}` |
| POST | `/api/inbox` | `{"url"}` → 批量触发三种生成（导图/笔记/封面），返回 `{key, allCached, tasks, cached}` |
| GET | `/api/inbox/{key}` | 聚合三种生成状态：`{key, url, allDone, kinds}`（缓存兜底） |
| GET | `/api/inbox-list` | 收件箱列表：按链接聚合的最近收进记录 + 三种状态 |
| POST | `/api/sph/resolve` | `{"url"}` → 解析视频号分享链接，返回可播放/下载直链（需 `HY_TOKEN`） |
| POST | `/api/admin/regenerate-mindmaps` | 后台重新生成全部缓存思维导图（真实转写），返回 `{ok, queued}` |
| GET | `/api/health` | 健康检查 |

## 收件箱（链接自动入库）

调用 `POST /api/inbox` 传入链接，后端批量触发三种生成（思维导图 / 笔记 / AI 封面），网站「视频导图 → 收件箱」Tab 查看。

纯云端，不依赖本地电脑常开：后台轮询 `GET /api/inbox/{key}` 聚合三种生成状态，直至 `allDone`。

## 目录

```
server/
├── app.py               # FastAPI 入口（任务管理 + 数据 API）
├── db.py                # SQLAlchemy engine / session / init（读取 server/.env）
├── models.py            # 6 张表模型（Idea/Tag/Mindmap/Note/Cover/Task，JSONB/JSON 按环境切换）
├── llm.py               # LLM 接口（文本/VLM/文生图提示词）
├── regenerate_mindmaps.py  # 思维导图重生成脚本（SKILL_SCRIPT_PATH 或仓库内副本）
├── migrations/          # 生产库建表 SQL（create_notes.sql / create_covers.sql / task_kind.sql）
├── requirements.txt     # Python 依赖
├── requirements-dev.txt # 开发依赖
├── ideabox.db           # SQLite 数据库（自动创建，已 gitignore）
├── .env                 # 环境变量（本地，已 gitignore，不提交）
├── start.sh             # 启动脚本（Coze 部署用）
├── dev.sh               # 本地开发启动脚本（Coze dev 环境用）
├── README.md            # 本文档
└── skills/
    └── prepare_video.py # 视频解析技能脚本
```
