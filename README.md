# 灵感匣 IdeaBox

个人灵感与想法记录平台，支持快速捕捉、标签分类、看板管理、视频思维导图。

## 技术栈

- **前端**：React 18 + Vite 6 + Tailwind CSS 3
- **后端**：Python FastAPI + SQLite
- **部署**：Coze 平台（Python 单运行时）

## 目录结构

```
├── src/                    # 前端源码
│   ├── components/         # React 组件
│   │   ├── Header.jsx      # 顶部导航栏
│   │   ├── IdeaInput.jsx   # 快速捕捉输入框
│   │   ├── IdeaCard.jsx    # 灵感卡片
│   │   ├── IdeaList.jsx    # 列表视图
│   │   ├── BoardView.jsx   # 看板视图（按标签分列）
│   │   ├── VideoMindmap.jsx# 视频思维导图
│   │   ├── Sidebar.jsx     # 侧边栏
│   │   ├── SearchBar.jsx   # 搜索栏
│   │   └── EmptyState.jsx  # 空状态
│   ├── hooks/              # 自定义 Hooks
│   │   └── useIdeas.js     # 灵感 CRUD（调 API）
│   ├── utils/helpers.js    # 工具函数
│   ├── data/tags.js        # 标签颜色配置
│   ├── config.js           # 前端配置（API 地址等）
│   ├── App.jsx             # 主应用
│   ├── main.jsx            # 入口
│   └── index.css           # 全局样式 + Tailwind
├── server/                 # Python 后端
│   ├── app.py              # FastAPI 主入口（含 API 路由）
│   ├── db.py               # 数据库配置
│   ├── models.py           # 数据模型
│   ├── llm.py              # LLM 接口（可选）
│   ├── requirements.txt    # Python 依赖
│   ├── start.sh            # 启动脚本
│   ├── regenerate_mindmaps.py  # 思维导图重生成脚本
│   └── skills/             # 视频解析技能脚本
├── .coze                   # 部署配置
├── build-and-commit.sh     # 构建 + 提交脚本
└── package.json            # 前端依赖
```

## 本地开发

### 前端（热更新）

```bash
pnpm install
pnpm run dev
# → http://localhost:5173
```

### 后端

```bash
cd server
pip install -r requirements.txt
python -m uvicorn app:app --reload --port 8000
# → http://localhost:8000/api/health
```

### 开发模式说明

本地开发时，前后端分离运行：

- 前端（Vite）：端口 5173，热更新，调 `http://localhost:8000/api`
- 后端（FastAPI）：端口 8000，处理 API 请求

## 构建与部署

### 构建前端

```bash
pnpm run build
# 生成 dist/ 目录
```

### 提交到 Git

```bash
sh build-and-commit.sh
# 构建 + git add dist/ + git commit
```

### 部署流程（Coze 平台）

1. 推送到 GitHub
2. 平台自动执行：
   - `pip install -r requirements.txt`
   - `uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT}`
3. 一个进程同时提供：
   - `/api/*` → FastAPI 后端
   - `/*` → 前端静态页面（dist/）

## 核心功能

- 快速捕捉灵感，支持 `#标签` 语法
- 卡片按日期分组展示，支持置顶
- 标签系统（10 种颜色自动分配）
- 全文搜索（`/` 快捷键聚焦）
- 编辑/删除/置顶
- 数据导入/导出（JSON）
- 看板视图：按标签分列，拖拽打标签
- 视频导图：粘贴视频链接 → 思维导图
- 响应式布局

## 数据存储

数据存储在 `server/ideabox.db`（SQLite），首次启动时自动创建。