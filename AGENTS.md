# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台，波普艺术漫画书风格。数据存储在后端 SQLite（`server/ideabox.db`，SQLAlchemy），前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。
附带一个 FastAPI 后端（`server/`）提供「视频链接 → 思维导图」能力。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 SQLite（SQLAlchemy ORM，`server/ideabox.db`），前端 `useIdeas` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频导图（markmap 渲染）
- 后端：FastAPI（`server/`，依赖用户 Codex skill 的 prepare_video.py）
- 包管理器：pnpm（本地环境无 pnpm 时可用 npm）

## 构建与运行
```bash
# 安装依赖
pnpm install

# 开发模式（前端）
pnpm run dev

# 构建生产版本
pnpm run build

# 预览生产构建
pnpm run preview

# 后端（另开终端）
cd server
./.venv/Scripts/python -m uvicorn app:app --host 127.0.0.1 --port 8000
# 详见 server/README.md
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
├── server/                 # FastAPI 后端（SQLite 存储，详见 server/README.md）
│   ├── app.py              # API 入口：灵感 CRUD + 任务管理 + 导图缓存
│   ├── db.py               # SQLAlchemy engine / session / init
│   ├── models.py           # 4 张表模型（Idea/Tag/Mindmap/Task）
│   ├── llm.py              # LLM 接口位（默认模板，可配硅基流动/OpenAI 兼容）
│   ├── migrate_cache.py    # 一次性：旧 cache/*.json → mindmaps 表
│   ├── requirements.txt
│   ├── ideabox.db          # SQLite 数据库（自动创建）
│   ├── cache/              # 旧版文件缓存（已废弃）
│   └── work/               # 视频解析中间产物
└── src/
    ├── main.jsx            # React 入口
    ├── App.jsx             # 主应用（布局/状态管理/筛选逻辑/视图切换）
    ├── index.css           # 全局样式 + Tailwind
    ├── hooks/
    │   └── useIdeas.js         # 灵感 CRUD hook（调后端 API + 操作队列）
    ├── utils/
    │   └── helpers.js          # 工具函数
    ├── data/
    │   └── tags.js             # 标签颜色配置
    └── components/
        ├── Header.jsx          # 顶部导航栏（列表/看板/视频导图切换）
        ├── IdeaInput.jsx       # 快速捕捉输入框
        ├── IdeaCard.jsx        # 灵感卡片
        ├── IdeaList.jsx        # 列表（日期分组 + 置顶区）
        ├── BoardView.jsx       # 看板视图（标签分列 + 拖拽打标签）
        ├── VideoMindmap.jsx    # 视频导图视图（链接输入 + markmap 渲染）
        ├── Sidebar.jsx         # 侧边栏
        ├── SearchBar.jsx       # 搜索栏
        └── EmptyState.jsx      # 空状态
```

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
