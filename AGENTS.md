# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台（波普艺术漫画书风格） + **行动计划模块**（树状分叉、进展流、状态自动推进）。数据存储在后端 PostgreSQL（部署环境）/ SQLite（开发环境），由 Alembic 自动迁移建表；前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 PostgreSQL（部署）/ SQLite（开发），由 **Alembic** 自动迁移建表；前端 `useIdeas` / `usePlans` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频工具（Tab：思维导图 / 信息海报）/ **行动计划**
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
├── public/
│   └── favicon.svg         # 图标
├── server/                 # Python 后端
│   ├── app.py              # FastAPI 入口（注册路由 + 静态文件）
│   ├── config.py           # 环境变量 + 全局对象
│   ├── helpers.py          # 工具函数（时间/ID/数据迁移）
│   ├── cover.py            # qwen2image 工作流调用（思维导图 / 信息海报）
│   ├── db.py               # SQLAlchemy 配置
│   ├── models.py           # 数据模型（含计划三表 Plan/PlanNode/PlanLog）
│   ├── requirements.txt    # Python 依赖
│   ├── alembic.ini         # Alembic 数据库迁移配置
│   ├── migrations/         # Alembic 迁移脚本（自动建表/改表）
│   ├── ideabox.db          # SQLite 数据库（自动创建，已 gitignore）
│   ├── start.sh            # 启动脚本（部署用，先跑 alembic 迁移）
│   ├── dev.sh              # 本地开发启动脚本
│   ├── routers/            # 路由模块
│   │   ├── ideas.py        # 灵感 CRUD / 标签 / 导出导入
│   │   ├── plans.py        # 行动计划（计划 CRUD + 树节点 + 进展流 + 状态自动推进）
│   │   ├── video.py        # 思维导图 / 信息海报（后台任务调 qwen2image）
│   │   └── admin.py        # 健康检查
└── src/
    ├── main.jsx            # React 入口
    ├── App.jsx             # 主应用
    ├── index.css           # 全局样式 + Tailwind
    ├── config.js           # 配置（API 地址等）
    ├── hooks/
    │   ├── useIdeas.js         # 灵感 CRUD hook
    │   └── usePlans.js         # 行动计划 hook（计划/节点/进展 + 状态推进）
    ├── utils/
    │   └── helpers.js          # 工具函数
    ├── data/
    │   └── tags.js             # 标签颜色配置
    └── components/
        ├── Header.jsx          # 顶部导航栏（含「行动计划」视图入口）
        ├── IdeaInput.jsx       # 快速捕捉输入框
        ├── IdeaCard.jsx        # 灵感卡片
        ├── IdeaList.jsx        # 列表视图
        ├── BoardView.jsx       # 看板视图
        ├── VideoTools.jsx      # 视频工具 Tab 容器（导图/海报切换）
        ├── VideoMindmap.jsx    # 思维导图（轮询 qwen2image 结果）
        ├── VideoCover.jsx      # 信息海报（轮询 qwen2image 结果）
        ├── PlansView.jsx       # 行动计划视图（计划列表 + 树 + 进展时间线）
        ├── Sidebar.jsx         # 侧边栏
        ├── SearchBar.jsx       # 搜索栏
        └── EmptyState.jsx      # 空状态
```

## 部署架构
- `.coze` 配置：`requires = ["python3-3.12"]`（Python 3.12 运行时）
- `dist/` 已构建并提交到 Git，部署时无需前端构建（‼️ `dist/` 不能加 `.gitignore`）
- 部署流程：
  1. `build` → `pip install -r server/requirements.txt`（安装 Python 依赖，含 alembic）
  2. `run` → `sh server/start.sh` → 先 `alembic upgrade head`（自动迁移建表），再 `cd server && PYTHONPATH=. uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT}`（启动服务）
- 服务端 `server/app.py` 注册四个路由模块（`routers/ideas.py`、`routers/plans.py`、`routers/video.py`、`routers/admin.py`），统一端口服务：`/api/*` 路由到 API 处理，其余路由返回前端 `dist/` 静态文件

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

### 行动计划
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/plans` | 获取所有计划 |
| POST | `/api/plans` | 创建计划（自动生成根节点） |
| GET | `/api/plans/{id}` | 获取计划详情（plan + nodes + logs） |
| PUT | `/api/plans/{id}` | 更新计划 |
| DELETE | `/api/plans/{id}` | 删除计划（连节点+日志） |
| POST | `/api/plans/{id}/nodes` | 新增分支节点（可指定 parent_id） |
| POST | `/api/plans/{id}/nodes/{nid}/{action}` | 节点动作：done/onhold/abandon/resume |
| PUT | `/api/plans/{id}/nodes/{nid}` | 重命名节点 |
| DELETE | `/api/plans/{id}/nodes/{nid}` | 删除节点及其子孙 |
| POST | `/api/plans/{id}/logs` | 追加一条进展记录 |

### 视频工具
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/mindmap` | 创建思维导图任务（调用 qwen2image 工作流） |
| GET | `/api/mindmap/{task_id}` | 查询导图任务状态 |
| POST | `/api/cover` | 创建信息海报任务（调用 qwen2image 工作流） |
| GET | `/api/cover/{task_id}` | 查询海报任务状态 |

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
9. 视频工具：粘贴视频号/抖音链接 → 通过 qwen2image.coze.site 工作流（思维导图 / 信息海报）一站式处理
10. 行动计划：建立计划 → 树状分叉（任意层级子节点）→ 记录进展/完成/搁置/放弃 → **状态自动向上推进**（某节点所有子节点完成则自动完成）→ 全宽版面展示分支树 + 进展时间线

### 工作流调用（思维导图 / 信息海报共用）

思维导图和信息海报都通过 `qwen2image.coze.site` 工作流处理。

```
用户发视频链接
  → POST /api/cover 或 POST /api/mindmap {url}
  → 后台调用 qwen2image.coze.site/api/generate（multipart/form-data）
     参数: mode=url, image_url=..., type=mindmap|poster, style=pop
  → 返回 base64 data URL 图片
  → 存入对应缓存表，前端轮询 GET /api/{kind}/{task_id}
```

**不再需要**：本地下载视频、ASR 转写、VLM 帧分析、LLM 生成提示词/导图、ffmpeg、markmap 渲染 —— 全部由工作流一站式完成。

## 环境变量（server/.env，已 gitignore）

| 变量 | 用途 | 默认值 |
|------|------|--------|
| `PGDATABASE_URL` | PostgreSQL 连接串（生产必需，不设回退 SQLite） | — |
| `QWEN2IMAGE_BASE_URL` | qwen2image 工作流地址 | `https://qwen2image.coze.site` |

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
- 表结构由 **Alembic 自动迁移**（`alembic upgrade head`）创建/更新，无需手动建表
  
### 2.1 数据库迁移（Alembic）
- 配置：`server/alembic.ini` + `server/migrations/`（env.py / script.py.mako / versions/）
- 连接逻辑与 `db.py` 一致（自动降级）：设 `PGDATABASE_URL` → Postgres；否则 → 本地 SQLite
- 改完 `models.py` 后：
  ```bash
  alembic revision --autogenerate -m "描述"
  alembic upgrade head
  ```
- 服务器/部署启动（`server/start.sh`）会自动执行 `alembic upgrade head`
- 首次为已存数据的旧库引入 Alembic 时：先 `alembic stamp head` 标记版本（不动数据），再后续用 `upgrade head` 演进

### 3. 健康检查端点不是 `/v1/ping`
- 项目提供 `/api/health` 作为健康检查接口
- 部署平台可能发 `GET /v1/ping` 探活，返回 404 是正常的

### 4. 前端 API 地址解析
- `src/config.js` 按优先级：`window.APP_CONFIG.apiBase` > `VITE_API_BASE` 环境变量 > 默认值
- 开发环境默认：`http://127.0.0.1:8000`（Python FastAPI 开发服务器）
- 生产环境默认：`/api`（同源，由 Python 服务统一提供）

### 5. 思维导图和信息海报共用 qwen2image 工作流，无需 Token
- 思维导图和海报都走 `POST https://qwen2image.coze.site/api/generate`（multipart/form-data，无需 Token）
- 通过 `type` 参数区分：`"mindmap"`（思维导图）或 `"poster"`（信息海报）
- 返回 `base64 data URL` 图片，前端直接展示

### 6. 本地处理逻辑已全部移除
- 不再需要：ffmpeg、ASR 转写、VLM 帧分析、LLM 生成提示词/导图
- 不再需要：`llm.py`、`skills/prepare_video.py`、`regenerate_mindmaps.py`
- 不再需要：`HY_TOKEN`（元宝 cookie）、`LLM_PROVIDER`、`LLM_API_KEY` 等环境变量
- 视频链接解析全部由工作流处理，不再依赖平台特定解析