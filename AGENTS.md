# AGENTS.md - 灵感匣 IdeaBox

## 项目概览
个人灵感与想法记录平台，波普艺术漫画书风格。数据存储在后端 SQLite（`server/ideabox.db`），前端通过 API 读写；旧 LocalStorage 数据首次加载时自动迁移一次。

## 技术栈
- **React 18** + **Vite 6** + **Tailwind CSS 3**
- 数据存储：后端 SQLite（`node:sqlite`，`server/ideabox.db`），前端 `useIdeas` hook 调 REST API
- 视图切换：列表 / 看板（标签分列 + 拖拽打标签）/ 视频导图（markmap 渲染）
- 后端：Node.js 24（`server.cjs`，内置 `node:sqlite`）
- 包管理器：pnpm

## 构建与运行
```bash
# 安装依赖
pnpm install

# 开发模式（前端 Vite HMR）
pnpm run dev

# 生产构建
pnpm run build

# 一键启动生产服务（前端 + API）
node server.cjs

# 或使用脚本
sh start.sh
```

## 目录结构
```
├── index.html              # HTML 入口
├── package.json            # 依赖配置
├── vite.config.js          # Vite 配置
├── tailwind.config.js      # Tailwind 主题配置
├── postcss.config.js       # PostCSS 配置
├── server.cjs              # Node.js 服务端（API + 静态文件托管）
├── build.sh                # 构建脚本（部署用）
├── start.sh                # 启动脚本（部署用）
├── public/
│   └── favicon.svg         # 图标
├── server/                 # Python 开发后端（可选，本地开发用）
│   ├── app.py              # FastAPI 入口
│   ├── db.py               # SQLAlchemy 配置
│   ├── models.py           # 数据模型
│   ├── llm.py              # LLM 接口
│   ├── requirements.txt
│   ├── ideabox.db          # SQLite 数据库（自动创建）
│   └── skills/             # 视频解析技能脚本
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
- `.coze` 配置：`requires = ["nodejs-24"]`（仅需 Node.js）
- 部署流程：
  1. `build` → `sh build.sh` → `pnpm install && pnpm run build`（生成 `dist/`）
  2. `run` → `sh start.sh` → `node server.cjs`（启动服务）
- 服务端 `server.cjs` 使用 Node.js 24 内置 `node:sqlite` 模块，无需额外依赖
- 统一端口服务：`/api/*` 路由到 API 处理，其余路由返回前端 `dist/` 静态文件

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