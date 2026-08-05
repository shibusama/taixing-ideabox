# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台，波普艺术漫画书风格。数据存储在后端 SQLite（`server/ideabox.db`），前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 SQLite（`server/ideabox.db`），前端 `useIdeas` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频导图（markmap 渲染）
- 后端：Python FastAPI + SQLite（`server/app.py`）
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
        ├── VideoMindmap.jsx    # 视频导图
        ├── Sidebar.jsx         # 侧边栏
        ├── SearchBar.jsx       # 搜索栏
        └── EmptyState.jsx      # 空状态
```

## 部署架构
- `.coze` 配置：`requires = ["python-312"]`（Python 运行时）
- `dist/` 已构建并提交到 Git，部署时无需前端构建
- 部署流程：
  1. `build` → `pip install -r server/requirements.txt`（安装 Python 依赖）
  2. `run` → `sh server/start.sh` → `cd server && uvicorn app:app --host 0.0.0.0 --port ${DEPLOY_RUN_PORT}`（启动服务）
- 服务端 `server/app.py` 使用 FastAPI + SQLite/PostgreSQL，统一端口服务：`/api/*` 路由到 API 处理，其余路由返回前端 `dist/` 静态文件

## 核心功能
1. 快速捕捉灵感，支持 `#标签` 语法
2. 卡片按日期分组展示，支持置顶
3. 标签系统（10 种颜色自动分配）
4. 全文搜索（`/` 快捷键聚焦）
5. 编辑/删除/置顶
6. 数据导入/导出（JSON）
7. 响应式布局
8. 看板视图：按标签分列，拖拽卡片到列 = 添加标签，拖到「未标签」列 = 清空标签（可撤销）
9. 视频导图：粘贴视频号/抖音链接 → 后端解析转写 → LLM/模板生成 markmap 思维导图渲染

## 代码规范
- 组件使用函数式组件 + Hooks
- 样式使用 Tailwind CSS 原子类
- 状态管理使用自定义 Hooks
- 文件命名：组件 PascalCase，工具函数 camelCase