-- ============================================================================
-- 行动计划模块 · PostgreSQL 建表 SQL
-- 对应 SQLAlchemy 模型（server/models.py）：
--   Plan / PlanNode / PlanLog
--
-- ⚠️ 仅用于 PostgreSQL（生产）。本地 SQLite 会自动建表，无需执行本文件。
-- 上云时在 PostgreSQL 上执行本文件即可（可重复执行需配合 IF NOT EXISTS）。
-- 后文附"清空重来"的 DROP 语句（慎用）。
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1) plans —— 行动计划
--    一个计划 = 一棵树 + 一条进展流
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plans (
    id         TEXT PRIMARY KEY,               -- 计划唯一 id（UUID hex）
    title      TEXT NOT NULL,                  -- 计划标题
    goal       TEXT,                           -- 目标
    domain     TEXT,                           -- 领域分类（漫剧/博客/安全…）
    status     TEXT NOT NULL DEFAULT 'active', -- active/done/onhold/abandoned
    priority   TEXT,                           -- 高/中/低
    created_at DOUBLE PRECISION NOT NULL,      -- 创建时间（毫秒时间戳）
    updated_at DOUBLE PRECISION NOT NULL       -- 最近更新时间（毫秒时间戳）
);

-- 按更新时间倒序查列表
CREATE INDEX IF NOT EXISTS idx_plans_updated_at ON plans (updated_at DESC);

-- ----------------------------------------------------------------------------
-- 2) plan_nodes —— 计划树节点（分支）
--    靠 parent_id 表达层级；parent_id 为 NULL 表示根节点
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plan_nodes (
    id           TEXT PRIMARY KEY,
    plan_id      TEXT NOT NULL,                -- 所属计划（FK -> plans.id）
    parent_id    TEXT,                         -- 父节点（NULL = 根；FK -> plan_nodes.id）
    title        TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active', -- active/done/onhold/abandoned
    completed_at DOUBLE PRECISION,             -- 完成时间（毫秒时间戳）
    created_at   DOUBLE PRECISION NOT NULL,
    updated_at   DOUBLE PRECISION NOT NULL
);

-- 按计划取全部节点（树渲染）
CREATE INDEX IF NOT EXISTS idx_plan_nodes_plan_id ON plan_nodes (plan_id);
-- 按父节点取子节点（展开/状态推进）
CREATE INDEX IF NOT EXISTS idx_plan_nodes_parent_id ON plan_nodes (parent_id);

-- 外键约束：删除计划时级联删除其节点
ALTER TABLE plan_nodes
    ADD CONSTRAINT fk_plan_nodes_plan
    FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE;

-- parent_id 自引用外键（可选项：DELETE 时置 NULL 以防子节点悬挂）
-- 说明：SQLite 的 create_all 不建外键；此处为生产库增强数据完整性。
-- 若你的 PostgreSQL 已建过本表且报"column already has a constraint"，
-- 请删掉本 ALTER 语句或先 DROP 旧表再执行。
ALTER TABLE plan_nodes
    ADD CONSTRAINT fk_plan_nodes_parent
    FOREIGN KEY (parent_id) REFERENCES plan_nodes (id) ON DELETE SET NULL;

-- ----------------------------------------------------------------------------
-- 3) plan_logs —— 进展流（时间线）
--    每次操作自动追加一条；历史永不覆盖
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS plan_logs (
    id         TEXT PRIMARY KEY,
    plan_id    TEXT NOT NULL,                  -- 所属计划（FK -> plans.id）
    node_id    TEXT,                           -- 关联节点（可选；FK -> plan_nodes.id）
    action     TEXT NOT NULL,                  -- create/add/complete/onhold/resume/abandon/note
    content    TEXT,                           -- 具体描述
    created_at DOUBLE PRECISION NOT NULL       -- 时间（毫秒时间戳）
);

-- 按计划按时间取进展流
CREATE INDEX IF NOT EXISTS idx_plan_logs_plan_time ON plan_logs (plan_id, created_at);

-- 外键约束：删除计划时级联删除其日志
ALTER TABLE plan_logs
    ADD CONSTRAINT fk_plan_logs_plan
    FOREIGN KEY (plan_id) REFERENCES plans (id) ON DELETE CASCADE;

-- ============================================================================
-- (可选) 清空/重建计划模块三张表 —— 仅用于出错重来，生产请勿随意执行
-- ============================================================================
-- DROP TABLE IF EXISTS plan_logs;
-- DROP TABLE IF EXISTS plan_nodes;
-- DROP TABLE IF EXISTS plans;
