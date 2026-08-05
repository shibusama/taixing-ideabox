# 灵感匣后端 (server/)

灵感匣「视频链接 → 思维导图」功能 + 数据存储后端，FastAPI + SQLite (SQLAlchemy)。

## 架构

```
前端 React (markmap 渲染)
   │  POST /api/mindmap {url}  → {task_id}   （后台线程执行）
   │  GET  /api/mindmap/{task_id}            （轮询：pending/running/done/error）
   │  GET/POST/PUT/DELETE /api/ideas         （灵感 CRUD）
   ▼
FastAPI (server/app.py)
   │  调用 skill 脚本 prepare_video.py
   ▼
解析管线（下载 MP4 → 提取音频/关键帧 → faster-whisper 转写）
   │  产出 low_cost_material.json / transcript_preview.txt
   ▼
LLM 生成思维导图 Markdown（markmap 格式）   ← 未配置 key 时用模板
   ▼
SQLite 持久化（mindmaps 表，按 URL sha256 缓存，重复解析秒回）
```

## 数据存储（SQLite）

所有业务数据存在 `server/ideabox.db`（首次启动自动建表），4 张表：

| 表 | 用途 | 说明 |
|----|------|------|
| `ideas` | 灵感主表 | 软删除（`deleted_at`），置顶/标签 JSON 数组 |
| `tags` | 标签冗余表 | name 唯一 + count 计数，写操作后重建 |
| `mindmaps` | 视频导图缓存 | 替代旧 `cache/*.json`，url_hash 唯一索引 |
| `tasks` | 解析任务状态 | 持久化，服务重启后 pending/running 置为 error |

前端数据从 LocalStorage 迁移到后端 API（`src/hooks/useIdeas.js`），首次加载时若数据库为空且浏览器仍有旧 LocalStorage 数据会自动导入一次。

旧文件缓存迁移（一次性）：`.venv/Scripts/python.exe migrate_cache.py`（幂等，可重复跑）。

## 启动

```bash
cd server
python -m venv .venv            # 首次
./.venv/Scripts/pip install -r requirements.txt   # 首次
./.venv/Scripts/python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

> ℹ️ **关于 safe-delete**：本环境的 safe-delete 包装只拦截「删除文件」操作（rm/覆盖已存在文件），
> **SQLite 行级写入不受影响**。因此数据库固定使用 `server/ideabox.db`（由后端进程创建后持续写入），
> 无需每次换库名。唯一注意点：**不要在后端运行期间手动删/覆盖 ideabox.db 文件本身**；
> 数据操作一律通过后端 API。导图重生成走内部端点：`POST /api/admin/regenerate-mindmaps`。

## 依赖 skill

后端依赖用户已有的 Codex skill 脚本：
`C:\Users\13191\.codex\skills\video-link-summarizer\scripts\prepare_video.py`

系统依赖：`ffmpeg` / `ffprobe`（已在 PATH）。转写可选装 `faster-whisper`（未装时跳过转写，导图仅基于元信息）。

## 启用 LLM 思维导图（可选）

未配置时后端输出模板导图（元信息 + 转录采样），用于跑通全流程。
要启用 AI 深度分析导图，创建 `server/.env`（已 gitignore，注意**不要提交 key**）：

```bash
# 硅基流动（当前已配置，模型 DeepSeek-V4-Flash）
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash

# 或任何 OpenAI 兼容接口
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=sk-xxx
LLM_MODEL=your-model
```

> 备注：早期使用 Qwen/Qwen2.5-7B-Instruct 时发现该免费模型在硅基流动上输出大量乱码，
> 已切换为 deepseek-ai/DeepSeek-V4-Flash（输出干净、质量好）。

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
| GET | `/api/health` | 健康检查 |

## 目录

```
server/
├── app.py               # FastAPI 入口（任务管理 + 数据 API）
├── db.py                # SQLAlchemy engine / session / init
├── models.py            # 4 张表模型（Idea/Tag/Mindmap/Task）
├── llm.py               # LLM 接口位（none / openai-compatible / siliconflow）
├── migrate_cache.py     # 一次性：旧 cache/*.json → mindmaps 表
├── requirements.txt
├── ideabox.db           # SQLite 数据库（自动创建）
├── cache/               # 旧版文件缓存（已废弃，迁移后可删除）
└── work/                # prepare_video.py 中间产物（按 URL sha256）
```
