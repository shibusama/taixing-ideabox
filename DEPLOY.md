# Coze 部署清单（IdeaBox 灵感匣）

本文档记录 IdeaBox 部署到 Coze 平台的关键步骤与注意事项。
部署环境是 Python 单运行时，前端由 FastAPI 托管 `dist/` 静态文件；Coze build 阶段会执行 `pnpm run build`。

## 一、部署前（本地）

### 1. 前端代码改动 → 重新构建 + 提交 dist/

```bash
# 在项目根目录
pnpm run build          # 或 node node_modules/vite/bin/vite.js build
git add dist/
git commit -m "update frontend dist build"
git push
```

- 判断是否要重新构建：`git status` 看 `src/` 是否改过；没改过则 `dist/` 与仓库一致，无需提交。
- 新构建产物的哈希（`index-*.css` / `index-*.js`）与仓库一致 = 无需提交。

### 2. 后端代码改动 → 提交 + 推送

```bash
git add server/
git commit -m "fix: ..."
git push
```

## 二、Coze 平台配置

### 环境变量（部署环境设置）

| 变量 | 值 | 必需 |
|---|---|---|
| `PGDATABASE_URL` | Postgres 连接串 | ✅ 不设则回退 SQLite，数据不共享/易丢 |
| `HY_TOKEN` | 腾讯元宝 cookie（视频号解析用） | 用视频号解析功能才需要 |
| `LLM_API_KEY` | 硅基流动 API key（文本 + VLM + 文生图共用） | 深度导图 / 笔记 / AI 封面 |
| `LLM_BASE_URL` | 硅基流动地址（默认 https://api.siliconflow.cn/v1） | — |
| `LLM_MODEL` | 文本模型（默认 zai-org/GLM-5.2） | — |
| `VLM_MODEL` | 视觉理解模型（默认 Qwen/Qwen3-VL-32B-Instruct） | — |
| `IMAGE_MODEL` | 文生图模型（默认 Tongyi-MAI/Z-Image） | AI 封面 |
| `VLM_MAX_FRAMES` | VLM 处理最大帧数（默认 8） | — |
| `WORK_ROOT` | `/tmp/ideabox/work`（start.sh 已默认） | 默认即可 |
| `DEPLOY_RUN_PORT` | Coze 自动注入 | 自动 |
| `COZE_ASR_BASE_URL` | 视频导图云端 ASR | 用视频功能才需要 |

#### HY_TOKEN（视频号解析凭据）

`/api/sph/resolve`（视频号链接解析 API）依赖 `HY_TOKEN`——腾讯元宝的登录 cookie：

1. 浏览器打开并登录 https://yuanbao.tencent.com
2. F12 → Application → Cookies，找到元宝域名下的 cookie（含 token 的那条）
3. 把整个 cookie 字符串复制为 `HY_TOKEN` 的值

⚠️ **安全**：`HY_TOKEN` 是登录凭据，只能放 `server/.env` 或 Coze 环境变量，**绝不能提交 Git**。
⚠️ **稳定性**：该接口是**非官方**的（元宝 + 微信频道），`server/app.py` 里硬编码了特定账号的请求头，腾讯侧接口变动/风控会导致解析失败，需更新代码。

### 数据库

- Postgres 表需**手动建表**（`Base.metadata.create_all()`，SQLite 才自动建）。
- 表结构：`ideas` / `tags` / `mindmaps` / `notes` / `covers` / `tasks`。
- `notes` / `covers` 为新增表，建表 SQL 在 `server/migrations/`（`create_notes.sql` / `create_covers.sql`），部署时需在生产库执行。
- 本地和 Coze 连**同一个库**才能共享数据。

## 三、部署流程（Coze 平台）

1. 本地改代码 → `pnpm run build`（如改了前端）→ `git commit` → `git push`
2. Coze 平台触发部署：
   - build：`pip install -r server/requirements.txt`
   - run：`sh server/start.sh` → `uvicorn app:app --port ${DEPLOY_RUN_PORT}`
3. 验证：访问 `/api/health`，正常返回 `{"ok":true}`

## 四、已知坑

| 坑 | 说明 |
|---|---|
| **`server/.env` 不随 Git 走** | `.env` 在 gitignore，Coze 上不存在。靠环境变量注入 `PGDATABASE_URL`、`HY_TOKEN` |
| **`coze_coding_dev_sdk` 仅 Coze 环境有** | `prepare_video.py` 的 `S3SyncStorage` / `ASRClient` 是平台内建，本地无此包 |
| **`server/` 目录只读** | `WORK_ROOT` 必须指向可写目录（默认 `/tmp/ideabox/work`） |
| **视频号解析依赖 HY_TOKEN + 非官方接口** | `/api/sph/resolve` 走元宝 + 微信频道接口，HY_TOKEN 未配置会返回 400 |
| **前端产物大（868KB）** | Vite 有 chunk 警告，属正常，暂不影响功能 |
| **VLM 需要 LLM_API_KEY** | 图片/音乐视频的视觉理解走 Qwen-VL，未配 key 时回退 tesseract OCR，见下方"视觉理解部署" |

### 视觉理解部署（图片/背景音乐视频的信息提取）

视频无语音时（ASR 转写为空），后端从关键帧提取图片内容。**主方案：VLM 视觉模型**，兜底：tesseract OCR。

**方案一：VLM（推荐，无需装系统软件）**
- 配置 `LLM_API_KEY` + `VLM_MODEL`（默认 `Qwen/Qwen3-VL-32B-Instruct`，硅基流动）
- 关键帧用 ffmpeg **场景检测**抽取，VLM 逐帧理解画面语义 + 提取文字
- 每视频最多 `VLM_MAX_FRAMES`（默认 8）次调用

**方案二：tesseract OCR（兜底，需装系统软件）**
```bash
# Ubuntu / Debian
apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
```
- Python 依赖 `pytesseract` + `Pillow` 已在 `server/requirements.txt`
- **都不配置不影响主流程**：图片信息提取自动跳过，视频导图照常工作（优雅降级）

## 五、本地 vs 生产差异速查

| 项 | 本地（Windows） | Coze 生产（Linux） |
|---|---|---|
| 数据库 | 火山开发库（`server/.env`） | 环境变量 `PGDATABASE_URL` |
| 前端 | FastAPI 托管 `dist/`（单进程） | `dist/` 静态文件（后端挂载） |
| 视频 ASR | ❌ 无 SDK | ✅ 平台内建 |
| 视频号解析 | 需本地 `.env` 配 `HY_TOKEN` | 环境变量 `HY_TOKEN` |
| 视觉理解 | `LLM_API_KEY` + `VLM_MODEL` | 环境变量 `LLM_API_KEY` + `VLM_MODEL` |
| 启动 | `start-server.bat` / `start-dev.sh` | `sh server/start.sh` |
