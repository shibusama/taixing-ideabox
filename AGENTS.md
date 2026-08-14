# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台，波普艺术漫画书风格。数据存储在后端 PostgreSQL（部署环境）/ SQLite（开发环境），前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 PostgreSQL（部署）/ SQLite（开发），前端 `useIdeas` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频工具（Tab：思维导图 / 信息海报）
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
│   ├── app.py              # FastAPI 入口（注册路由 + 静态文件）
│   ├── config.py           # 环境变量 + 全局对象
│   ├── helpers.py          # 工具函数（时间/ID/缓存/数据迁移）
│   ├── cover.py            # 封面生成工作流（video2image）
│   ├── db.py               # SQLAlchemy 配置
│   ├── models.py           # 数据模型
│   ├── llm.py              # LLM 接口（Coze 平台默认，siliconflow 备选）
│   ├── requirements.txt    # Python 依赖（14 个包）
│   ├── ideabox.db          # SQLite 数据库（自动创建，已 gitignore）
│   ├── start.sh            # 启动脚本（部署用）
│   ├── dev.sh              # 本地开发启动脚本
│   ├── regenerate_mindmaps.py  # 思维导图重生成脚本
│   ├── routers/            # 路由模块
│   │   ├── ideas.py        # 灵感 CRUD / 标签 / 导出导入
│   │   ├── video.py        # 导图/封面
│   │   └── admin.py        # 健康检查 / 管理 / sph
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
        ├── VideoTools.jsx      # 视频工具 Tab 容器（导图/封面切换）
        ├── VideoMindmap.jsx    # 视频导图
        ├── VideoCover.jsx      # 视频封面图（轮询 /api/cover/{task_id}）
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
- 服务端 `server/app.py` 注册三个路由模块（`routers/ideas.py`、`routers/video.py`、`routers/admin.py`），统一端口服务：`/api/*` 路由到 API 处理，其余路由返回前端 `dist/` 静态文件

## API 路由一览

### 灵感 CRUD
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/ideas` | 获取所有灵感 |
| GET | `/api/ideas/archived` | 获取已归档灵感 |
| POST | `/api/ideas` | 创建灵感 |
| PUT | `/api/ideas/{idea_id}` | 更新灵感 |
| DELETE | `/api/ideas/{idea_id}` | 删除灵感（软删） |
| POST | `/api/ideas/{idea_id}/restore` | 恢复已删除 |
| POST | `/api/ideas/{idea_id}/pin` | 置顶/取消置顶 |
| DELETE | `/api/archived` | 清空归档 |
| GET | `/api/tags` | 获取标签列表 |
| GET | `/api/export` | 导出 JSON |
| POST | `/api/import` | 导入 JSON |

### 视频工具
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/mindmap` | 创建思维导图任务 |
| GET | `/api/mindmap/{task_id}` | 查询导图任务状态 |
| POST | `/api/cover` | 创建 AI 封面任务（调用 video2image 工作流） |
| GET | `/api/cover/{task_id}` | 查询封面任务状态 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/admin/regenerate-mindmaps` | 管理：重生成所有缓存导图 |
| POST | `/api/sph/resolve` | 视频号链接解析（需 HY_TOKEN） |

## 核心功能
1. 快速捕捉灵感，支持 `#标签` 语法
2. 卡片按日期分组展示，支持置顶
3. 标签系统（8 种颜色自动分配）
4. 全文搜索（`/` 快捷键聚焦）
5. 编辑/删除/置顶
6. 数据导入/导出（JSON）
7. 响应式布局
8. 看板视图：按标签分列，拖拽卡片到列 = 添加标签，拖到「未标签」列 = 清空标签（可撤销）
9. 视频工具：粘贴视频号/抖音链接 → 后端解析下载 → ASR 转写 + VLM 视觉理解 → 两种输出（思维导图 / AI 封面）

### AI 封面生成流程

```
用户发视频链接
  → POST /api/cover {url}
  → 后台 _run_cover_task() 调用 _call_video2image_workflow()
  → POST https://video2image.coze.site/run（Bearer Token 认证）
  → 工作流返回 card_image_url + card_content（标题/要点/摘要/标签）
  → 存入 Cover 缓存表，前端轮询 GET /api/cover/{task_id} 拿 image_url 显示
```

**不再需要**：本地下载视频、ASR 转写、VLM 帧分析、LLM 生成提示词、文生图 API —— 全部由工作流一站式完成。

## 思维导图流程

```
视频号/抖音链接
  → 解析直链（视频号走元宝 /api/sph/resolve，需 HY_TOKEN；抖音走 aweme detail）
  → 下载 input.mp4
  → ffmpeg 拆解：提取 audio.wav + 场景检测抽关键帧（720px，scene 阈值 0.3）
  → 信息提取：
      ├─ ASR 语音转写（Coze 云）→ transcript.txt
      └─ VLM 视觉理解（转写为空时触发）→ Qwen-VL/豆包逐帧理解 → ocr_result.txt
  → 组装 low_cost_material.json → LLM 生成 markmap 思维导图
```

- **VLM**：`server/llm.py` 的 `describe_image()`，`LLM_PROVIDER=coze` 时用豆包模型，`siliconflow` 时用 Qwen-VL
- **降级**：VLM 不可用 → 回退 tesseract OCR（仅开发环境）→ 都不可用则跳过
- **场景检测**：`extract_media` 用 `select='gt(scene,0.3)'` + `-vsync vfr` 只抽画面变化的帧
- **ASR**：使用 Coze 平台云 ASR 服务（`coze_coding_dev_sdk.ASRClient`），上传音频到对象存储 → 调用云端语音识别

## 环境变量（server/.env，已 gitignore）

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `PGDATABASE_URL` | PostgreSQL 连接串（生产必需，不设回退 SQLite） | — |
| `HY_TOKEN` | 腾讯元宝 cookie（视频号解析） | — |
| `LLM_PROVIDER` | 模型提供商：`coze`（默认，部署）/ `siliconflow`（本地）/ `none`（模板） | `coze` |
| `LLM_API_KEY` / `LLM_BASE_URL` | 硅基流动（siliconflow 模式，文本 + VLM + 文生图共用） | — |
| `LLM_MODEL` | 文本模型（Coze 模式默认豆包，siliconflow 模式默认 GLM-5.2） | `doubao-seed-2-0-pro-260215` |
| `VLM_MODEL` | 视觉理解模型（siliconflow 模式） | `Qwen/Qwen3-VL-8B-Instruct` |
| `VLM_MAX_FRAMES` | VLM 最大帧数（默认 8） | `8` |
| `VIDEO2IMAGE_BASE_URL` | 视频封面工作流地址 | `https://video2image.coze.site` |
| `VIDEO2IMAGE_TOKEN` | 工作流 Bearer Token（必填） | — |

## 代码规范
- 组件使用函数式组件 + Hooks
- 样式使用 Tailwind CSS 原子类
- 状态管理使用自定义 Hooks
- 文件命名：组件 PascalCase，工具函数 camelCase

## 常见问题与修复记录

### 1. 部署环境没有 Node.js，前端必须在本地构建
- `dist/` 必须在本地构建并提交到 Git，部署时 `.coze` 的 build 只装 Python 依赖
- 不要把 `dist/` 加到 `.gitignore`

### 2. 生产环境使用 PostgreSQL，开发环境用 SQLite
- `server/db.py` 检测 `PGDATABASE_URL` 环境变量：有则连 PostgreSQL，没有则回退 SQLite
- 表结构由 SQLAlchemy ORM 自动创建

### 3. 健康检查端点不是 `/v1/ping`
- 项目提供 `/api/health` 作为健康检查接口
- 部署平台可能发 `GET /v1/ping` 探活，返回 404 是正常的

### 4. 前端 API 地址解析
- `src/config.js` 按优先级：`window.APP_CONFIG.apiBase` > `VITE_API_BASE` 环境变量 > 默认值
- 开发环境默认：`http://127.0.0.1:8000`（Python FastAPI 开发服务器）
- 生产环境默认：`/api`（同源，由 Python 服务统一提供）

### 5. 部署环境 server/ 目录只读，WORK_ROOT 不能放 server/ 下
- `WORK_ROOT` 通过环境变量注入，部署时设为 `/tmp/ideabox/work`（`/tmp` 可写）
- `server/start.sh` 中已设置 `export WORK_ROOT=/tmp/ideabox/work`

### 6. AI 封面使用 video2image 工作流
- 封面生成走 `POST https://video2image.coze.site/run`（工作流一站式处理）
- 需配置 `VIDEO2IMAGE_BASE_URL` 和 `VIDEO2IMAGE_TOKEN`

### 7. LLM 模型已从硅基流动迁移到 Coze 平台
- `LLM_PROVIDER=coze`（默认）使用 Coze SDK 的 `LLMClient`
- `LLM_PROVIDER=siliconflow` 仍可切换回硅基流动
- 文本模型：`doubao-seed-2-0-pro-260215`

### 8. faster-whisper 已移除
- 生产环境不再需要 faster-whisper（461MB），ASR 使用 Coze 云端服务
- `requirements.txt` 精简为 14 个包

### 9. 视频号解析（元宝）生产环境不可用
- `sph.litao.workers.dev`（Cloudflare Workers）在 Coze 生产环境被屏蔽
- 开发环境可配 `HY_TOKEN` 使用，生产环境需通过 Coze 工作流或联网节点解析