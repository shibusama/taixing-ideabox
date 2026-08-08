-- 灵感匣 IdeaBox: tasks 表加 kind / key 列（inbox 批量入口按链接聚合状态）
-- 在 Supabase / Volces PostgreSQL 生产库执行一次即可。
-- kind: mindmap | note | cover；key: url_hash（cache_key 前 16 位）。

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS kind VARCHAR;
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS key  VARCHAR;

CREATE INDEX IF NOT EXISTS idx_tasks_key ON tasks (key);
