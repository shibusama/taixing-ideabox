-- 灵感匣 IdeaBox: notes 表 (Markdown 笔记缓存)
-- 在 Supabase / Volces PostgreSQL 生产库执行一次即可。
-- 与 mindmaps 表同构: url_hash 主键, 内容为 Markdown 文本。

CREATE TABLE IF NOT EXISTS notes (
    url_hash   VARCHAR PRIMARY KEY,
    url        TEXT NOT NULL,
    note_md    TEXT NOT NULL,
    detail     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at DOUBLE PRECISION NOT NULL
);

-- 可选: 与 mindmaps 一致, 按创建时间索引便于清理过期缓存
CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes (created_at);
