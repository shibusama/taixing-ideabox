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
│   ├── cover.py            # 工作流调用（封面/思维导图共用 url2image.coze.site）
│   ├── db.py               # SQLAlchemy 配置
│   ├── models.py           # 数据模型
│   ├── requirements.txt    # Python 依赖（8 个包）
│   ├── ideabox.db          # SQLite 数据库（自动创建，已 gitignore）
│   ├── start.sh            # 启动脚本（部署用）
│   ├── dev.sh              # 本地开发启动脚本
│   ├── routers/            # 路由模块
│   │   ├── ideas.py        # 灵感 CRUD / 标签 / 导出导入
│   │   ├── video.py        # 导图/封面
│   │   └── admin.py        # 健康检查
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
| POST | `/api/mindmap` | 创建思维导图任务（调用 url2image 工作流） |
| GET | `/api/mindmap/{task_id}` | 查询导图任务状态 |
| POST | `/api/cover` | 创建 AI 封面任务（调用 url2image 工作流） |
| GET | `/api/cover/{task_id}` | 查询封面任务状态 |

### 其他
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |

## 核心功能
1. 快速捕捉灵感，支持 `#标签` 语法
2. 卡片按日期分组展示，支持置顶
3. 标签系统（8 种颜色自动分配）
4. 全文搜索（`/` 快捷键聚焦）
5. 编辑/删除/置顶
6. 数据导入/导出（JSON）
7. 响应式布局
8. 看板视图：按标签分列，拖拽卡片到列 = 添加标签，拖到「未标签」列 = 清空标签（可撤销）
9. 视频工具：粘贴视频号/抖音链接 → 通过 url2image.coze.site 工作流（思维导图 / AI 封面）一站式处理

### 工作流调用（封面 / 思维导图共用）

思维导图和信息海报都通过 `url2image.coze.site` 工作流处理。

```
用户发视频链接
  → POST /api/cover 或 POST /api/mindmap {url}
  → 后台调用 _call_workflow(url, output_type="cover"|"mindmap")
  → POST https://url2image.coze.site/run（Bearer Token 认证）
     参数: {"video_url": {...}, "style": "pop", "type": "cover"|"mindmap"}
  → 工作流返回:
     - cover 模式: card_image_url + card_content
     - mindmap 模式: mindmap_md（markmap 格式）
  → 存入对应缓存表，前端轮询 GET /api/{kind}/{task_id}
```

**不再需要**：本地下载视频、ASR 转写、VLM 帧分析、LLM 生成提示词/导图、ffmpeg —— 全部由工作流一站式完成。

## 环境变量（server/.env，已 gitignore）

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `PGDATABASE_URL` | PostgreSQL 连接串（生产必需，不设回退 SQLite） | — |
| `VIDEO2IMAGE_BASE_URL` | url2image 工作流地址（封面 + 思维导图共用） | `https://url2image.coze.site` |
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

### 6. 封面和思维导图共用 url2image 工作流
- 封面生成和思维导图都走 `POST https://url2image.coze.site/run`（工作流一站式处理，**无本地回退**）
- 通过 `type` 参数区分：`"cover"`（返回 `card_image_url`）或 `"mindmap"`（返回 `mindmap_md`）
- 需配置 `VIDEO2IMAGE_BASE_URL` 和 `VIDEO2IMAGE_TOKEN`

### 7. 本地处理逻辑已全部移除
- 不再需要：ffmpeg、ASR 转写、VLM 帧分析、LLM 生成提示词/导图
- 不再需要：`llm.py`、`skills/prepare_video.py`、`regenerate_mindmaps.py`
- 不再需要：`HY_TOKEN`（元宝 cookie）、`LLM_PROVIDER`、`LLM_API_KEY` 等环境变量
- 视频链接解析全部由工作流处理，不再依赖平台特定解析