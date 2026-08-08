# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台，波普艺术漫画书风格。数据存储在后端 PostgreSQL（部署环境）/ SQLite（开发环境），前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 PostgreSQL（部署）/ SQLite（开发），前端 `useIdeas` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频工具（Tab：思维导图 / Markdown 笔记 / AI 封面）
- 后端：Python FastAPI + PostgreSQL（部署）/ SQLite（开发）
- 包管理器：pnpm

## 构建与运行
```bash
# 安装依赖
pnpm install

# 开发模式（前端 Vite HMR）
pnpm run dev

# 生产构建
pnpm run build
```

## 目录结构
```
├── index.html              # HTML 入口
├── package.json            # 依赖配置
├── vite.config.js          # Vite 配置
├── tailwind.config.js      # Tailwind 主题配置
├── postcss.config.js       # PostCSS 配置
├── build-and-commit.sh     # 构建+提交脚本（可选）
├── public/
│   └── favicon.svg         # 图标
├── server/                 # Python 后端
│   ├── app.py              # FastAPI 入口（含 API 路由）
│   ├── db.py               # SQLAlchemy 配置
│   ├── models.py           # 数据模型
│   ├── llm.py              # LLM 接口（可选）
│   ├── requirements.txt    # Python 依赖
│   ├── ideabox.db          # SQLite 数据库（自动创建，已 gitignore）
│   ├── start.sh            # 启动脚本（部署用）
│   ├── regenerate_mindmaps.py  # 思维导图重生成脚本
│   └── skills/             # 视频解析技能脚本
│       └── prepare_video.py
└── src/
    ├── main.jsx            # React 入口
    ├── App.jsx             # 主应用
    ├── index.css           # 全局样式 + Tailwind
    ├── config.js           # 配置（API 地址等）
    ├── hooks/
    │   └── useIdeas.js         # 灵感 CRUD hook
    ├── utils/
    │   └── helpers.js          # 工具函数
    ├── data/
    │   └── tags.js             # 标签颜色配置
    └── components/
        ├── Header.jsx          # 顶部导航栏
        ├── IdeaInput.jsx       # 快速捕捉输入框
        ├── IdeaCard.jsx        # 灵感卡片
        ├── IdeaList.jsx        # 列表视图
        ├── BoardView.jsx       # 看板视图
        ├── VideoTools.jsx      # 视频工具 Tab 容器（导图/笔记/封面切换）
        ├── VideoMindmap.jsx    # 视频导图
        ├── VideoNote.jsx       # 链接转 Markdown 笔记
        ├── VideoCover.jsx      # 链接转 AI 封面图
        ├── Sidebar.jsx         # 侧边栏
        ├── SearchBar.jsx       # 搜索栏
        └── EmptyState.jsx      # 空状态
```

## 部署架构
- `.coze` 配置：`requires = ["python3-3.12"]`（Python 3.12 运行时）
- `dist/` 已构建并提交到 Git，部署时无需前端构建（‼️ `dist/` 不能加 `.gitignore`）
- 部署流程：
  1. `build` → `pip install -r server/requirements.txt`（安装 Python 依赖）
  2. `run` → `sh server/start.sh` → `cd server && WORK_ROOT=/tmp/ideabox/work uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT}`（启动服务）
- 服务端 `server/app.py` 使用 FastAPI + PostgreSQL（部署）/ SQLite（开发），统一端口服务：`/api/*` 路由到 API 处理，其余路由返回前端 `dist/` 静态文件

## 核心功能
1. 快速捕捉灵感，支持 `#标签` 语法
2. 卡片按日期分组展示，支持置顶
3. 标签系统（10 种颜色自动分配）
4. 全文搜索（`/` 快捷键聚焦）
5. 编辑/删除/置顶
6. 数据导入/导出（JSON）
7. 响应式布局
8. 看板视图：按标签分列，拖拽卡片到列 = 添加标签，拖到「未标签」列 = 清空标签（可撤销）
9. 视频工具：粘贴视频号/抖音链接 → 后端解析下载 → ASR 转写 + VLM 视觉理解 → 三种输出（markmap 思维导图 / Markdown 笔记 / AI 封面图）

## 视频工具链路

```
视频号/抖音链接
  → 解析直链（视频号走元宝 /api/sph/resolve，需 HY_TOKEN；抖音走 aweme detail）
  → 下载 input.mp4
  → ffmpeg 拆解：提取 audio.wav + 场景检测抽关键帧（720px，scene 阈值 0.3）
  → 信息提取：
      ├─ ASR 语音转写（Coze 云，说的话）→ transcript.txt
      └─ VLM 视觉理解（转写为空时触发）→ Qwen3-VL 逐帧理解 → ocr_result.txt
  → 组装 low_cost_material.json → LLM 生成三种输出之一：
      ├─ generate_mindmap()      → markmap 思维导图
      ├─ generate_note()         → Markdown 笔记（detail 参数切详细模式）
      └─ generate_image_prompt() → 文生图提示词 → 火山方舟 seedream 出图（AI 封面）
```

- **VLM**：`server/llm.py` 的 `describe_image()`，图片转 base64，调 `VLM_MODEL`（默认 `Qwen/Qwen3-VL-32B-Instruct`），上限 `VLM_MAX_FRAMES`（默认 8 帧）
- **降级**：VLM 未配 key → 回退 tesseract OCR（`ocr_frames_tesseract`）→ 都不可用则跳过
- **场景检测**：`extract_media` 用 `select='gt(scene,0.3)'` + `-vsync vfr` 只抽画面变化的帧

## 环境变量（server/.env，已 gitignore）

| 变量 | 用途 |
|---|---|
| `PGDATABASE_URL` | PostgreSQL 连接串（生产必需，不设回退 SQLite） |
| `HY_TOKEN` | 腾讯元宝 cookie（视频号解析） |
| `LLM_PROVIDER` | 模型提供商：`coze`（默认，部署）/ `siliconflow`（本地）/ `none`（模板） |
| `LLM_API_KEY` / `LLM_BASE_URL` | 硅基流动（siliconflow 模式，文本 + VLM + 文生图共用） |
| `LLM_MODEL` | 文本模型（默认 zai-org/GLM-5.2） |
| `VLM_MODEL` | 视觉理解模型（默认 Qwen/Qwen3-VL-32B-Instruct） |
| `IMAGE_MODEL` | siliconflow 文生图模型（默认 Tongyi-MAI/Z-Image） |
| `ARK_API_KEY` | 火山方舟 Agent Plan key（默认生图，走 /api/plan 不计费） |
| `ARK_IMAGE_MODEL` | 火山生图模型（默认 doubao-seedream-5.0-lite） |
| `VLM_MAX_FRAMES` | VLM 最大帧数（默认 8） |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token（收链接 → 自动入库） |

## 代码规范
- 组件使用函数式组件 + Hooks
- 样式使用 Tailwind CSS 原子类
- 状态管理使用自定义 Hooks
- 文件命名：组件 PascalCase，工具函数 camelCase

## 常见问题与修复记录

### 1. 部署环境没有 Node.js，前端必须在本地构建
- **问题**：部署环境（Coze Vefaas）只有 Python 3.12，没有 Node.js/pnpm
- **修复**：`dist/` 必须在本地构建并提交到 Git，部署时 `.coze` 的 build 只装 Python 依赖
- **工作流**：改代码 → `pnpm run build` → 提交 Git（含 `dist/`）→ 部署
- 不要把 `dist/` 加到 `.gitignore`

### 2. 生产环境使用 PostgreSQL，开发环境用 SQLite
- `server/db.py` 检测 `PGDATABASE_URL` 环境变量：有则连 PostgreSQL，没有则回退 SQLite
- 生产环境日志中 `PGDATABASE_URL=SET` 表示正使用 PostgreSQL
- 表结构由 SQLAlchemy ORM 自动创建（SQLite 下 `init_db()` 触发建表）
- ⚠️ `COZE_SUPABASE_URL` 是 Supabase API 的 HTTPS 地址，**不是**数据库连接串，SQLAlchemy 无法识别。必须用 `PGDATABASE_URL`

### 3. 健康检查端点不是 `/v1/ping`
- 项目提供 `/api/health` 作为健康检查接口
- 部署平台可能发 `GET /v1/ping` 探活，返回 404 是正常的，不影响功能
- 如需消除 404 日志，可加一个 `/v1/ping` 路由：`@app.get("/v1/ping")`

### 4. 前端 API 地址解析
- `src/config.js` 按优先级：`window.APP_CONFIG.apiBase` > `VITE_API_BASE` 环境变量 > 默认值
- 开发环境默认：`http://127.0.0.1:8000`（Python FastAPI 开发服务器）
- 生产环境默认：`/api`（同源，由 Python 服务统一提供）

### 5. 部署环境 server/ 目录只读，WORK_ROOT 不能放 server/ 下
- **问题**：`app.py` 中 `WORK_ROOT = BASE_DIR / "work"`，部署时 `server/` 目录是只读文件系统，`mkdir` 报错 `OSError: [Errno 30] Read-only file system`
- **修复**：`WORK_ROOT` 通过环境变量注入，部署时设为 `/tmp/ideabox/work`（`/tmp` 可写）
- **`server/start.sh`** 中已设置 `export WORK_ROOT=/tmp/ideabox/work`
- 本地开发时 `WORK_ROOT` 默认为 `server/work/`（无环境变量时）

### 6. 数据库连接变量用错：COZE_SUPABASE_URL ≠ PGDATABASE_URL
- **问题**：`db.py` 之前读取 `COZE_SUPABASE_URL`，但该变量值是 Supabase API 的 HTTPS 地址（如 `https://br-cosy-cow-...`），SQLAlchemy 不认识，报错 `Can't load plugin: sqlalchemy.dialects:https`
- **修复**：改为读取 `PGDATABASE_URL`（真正的 PostgreSQL 连接串，如 `postgresql://user:pass@host:5432/db`）
- 两个变量在沙箱中都存在，但部署环境只有 `PGDATABASE_URL` 有效

### 7. pip install -q 静默标志导致看不见安装错误
- **问题**：`.coze` 中 `pip install -q` 会隐藏所有安装输出，部署失败时无法判断是否包没装上
- **修复**：去掉 `-q` 标志，让 `pip install` 输出完整日志
- 部署日志现在会显示每个包的下载和安装状态

### 8. 视频解析模型太大，部署环境下载超时
- **问题**：`faster-whisper` 模型约 461MB，部署环境 build 阶段只有 30 秒超时，根本下载不完
- **尝试修复**：使用 ModelScope 镜像下载，但缓存格式不兼容
- **最终修复**：改用 Coze 平台云 ASR 服务（`coze_coding_dev_sdk.ASRClient`），上传音频到对象存储 → 调用云端语音识别，无需本地模型

### 9. 项目清理记录（已执行）
- `src/hooks/useLocalStorage.js` — 已废弃的死代码，已删除
- 根目录 `ideabox.db*` — 误生成的数据库文件，已删除
- `package-lock.json` — 混用 npm 导致的 lock 文件，已删除
- `assets/` — 临时截图，已删除
- `server/__init__.py` — 空文件，已删除
- `server/migrate_cache.py` / `server/migrate_db.py` — 一次性迁移脚本，已删除
- `server/test_transcribe.py` — 测试脚本，已删除
- `server/work/` — 空目录，已删除

### 10. Qwen2.5-VL 已下线，用 Qwen3-VL
- **问题**：硅基流动上 `Qwen/Qwen2.5-VL-7B-Instruct` 返回 "Model does not exist"，32B/72B 返回 "Model disabled"
- **原因**：账号实际可访问的视觉模型是 **Qwen3-VL 系列**（Qwen2.5-VL 已下线/不可用）
- **修复**：`VLM_MODEL` 设为 `Qwen/Qwen3-VL-8B-Instruct`（轻量）或 `Qwen/Qwen3-VL-32B-Instruct`（更强）
- 查询账号可用模型：`GET /v1/models`（Bearer 用 LLM_API_KEY），过滤 VL/Vision 关键词

### 11. 图片/背景音乐视频（无语音）信息在图片里
- **问题**：ASR 转写为空（视频只有图+音乐），导图没有内容
- **修复**：`ocr_frames()` 在转写为空时触发，VLM（Qwen-VL）逐帧理解画面语义 + 提取文字，并入 `low_cost_material.json` 的 `ocr_text` 字段
- **关键帧**：`extract_media` 用 ffmpeg 场景检测（`select='gt(scene,0.3)'`）只抽画面变化的帧，720px
- **性能**：VLM 逐帧调用较慢，用 `VLM_MAX_FRAMES`（默认 8）限制；成本随帧数增加