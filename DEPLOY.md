# Coze 部署清单（IdeaBox 灵感匣）

本文档记录 IdeaBox 部署到 Coze 平台的关键步骤与注意事项。
核心机制：**Coze 环境没有 Node.js，前端必须在本地构建并提交 `dist/`**。

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
| `WORK_ROOT` | `/tmp/ideabox/work`（start.sh 已默认） | 默认即可 |
| `DEPLOY_RUN_PORT` | Coze 自动注入 | 自动 |
| `COZE_ASR_BASE_URL` | 视频导图云端 ASR | 用视频功能才需要 |

### 数据库

- Postgres 表需**手动建表**（`Base.metadata.create_all()`，SQLite 才自动建）。
- 表结构：`ideas` / `tags` / `mindmaps` / `tasks`。
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
| **`server/.env` 不随 Git 走** | `.env` 在 gitignore，Coze 上不存在。靠环境变量注入 `PGDATABASE_URL` |
| **`coze_coding_dev_sdk` 仅 Coze 环境有** | `prepare_video.py` 的 `S3SyncStorage` / `ASRClient` 是平台内建，本地无此包 |
| **`server/` 目录只读** | `WORK_ROOT` 必须指向可写目录（默认 `/tmp/ideabox/work`） |
| **视频解析依赖第三方接口** | 微信解析用 `sph.litao.workers.dev`，抖音用官方接口，可能不稳定 |
| **前端产物大（868KB）** | Vite 有 chunk 警告，属正常，暂不影响功能 |

## 五、本地 vs 生产差异速查

| 项 | 本地（Windows） | Coze 生产（Linux） |
|---|---|---|
| 数据库 | Docker Postgres 容器 + `server/.env` | 环境变量 `PGDATABASE_URL` |
| 前端 | Vite dev server（5174） | `dist/` 静态文件（后端挂载） |
| 视频 ASR | ❌ 无 SDK | ✅ 平台内建 |
| 启动 | `python -m uvicorn app:app` | `sh server/start.sh` |
