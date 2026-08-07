-- 灵感匣 IdeaBox: covers 表 (文生图封面缓存)
-- 在 Supabase / Volces PostgreSQL 生产库执行一次即可。
-- 与 notes 表同构: url_hash 主键, 存生成的图片 URL 与提示词。

CREATE TABLE IF NOT EXISTS covers (
    url_hash   VARCHAR PRIMARY KEY,
    url        TEXT NOT NULL,
    image_url  TEXT NOT NULL,
    prompt     TEXT,
    created_at DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_covers_created_at ON covers (created_at);
