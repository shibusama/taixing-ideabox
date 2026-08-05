#!/usr/bin/env node
/**
 * IdeaBox Server — Node.js 24 (node:sqlite)
 * Serves API + frontend static files from a single port.
 */

const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const { DatabaseSync } = require("node:sqlite");

const PORT = parseInt(process.env.DEPLOY_RUN_PORT || "5000", 10);
const ROOT = __dirname;
const DIST = path.join(ROOT, "dist");
const DB_PATH = path.join(ROOT, "server", "ideabox.db");

// ── Database ────────────────────────────────────────────────────────────────
const serverDir = path.dirname(DB_PATH);
if (!fs.existsSync(serverDir)) {
  fs.mkdirSync(serverDir, { recursive: true });
}
const db = new DatabaseSync(DB_PATH);
db.exec("PRAGMA journal_mode=WAL");
db.exec("PRAGMA busy_timeout=5000");
db.exec("PRAGMA foreign_keys=ON");

db.exec(`
  CREATE TABLE IF NOT EXISTS ideas (
    id         TEXT PRIMARY KEY,
    content    TEXT NOT NULL,
    tags       TEXT DEFAULT '[]',
    pinned     INTEGER DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    deleted_at REAL
  )
`);
db.exec(`
  CREATE TABLE IF NOT EXISTS tags (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT UNIQUE NOT NULL,
    count INTEGER DEFAULT 0
  )
`);
db.exec(`
  CREATE TABLE IF NOT EXISTS mindmaps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    url_hash   TEXT UNIQUE NOT NULL,
    url        TEXT NOT NULL,
    mindmap_md TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
  )
`);
db.exec(`
  CREATE TABLE IF NOT EXISTS tasks (
    task_id    TEXT PRIMARY KEY,
    url        TEXT NOT NULL,
    status     TEXT DEFAULT 'pending',
    result     TEXT,
    error      TEXT,
    created_at TEXT DEFAULT (datetime('now'))
  )
`);

// ── Helpers ─────────────────────────────────────────────────────────────────
const _now = () => Date.now();
const _newId = () => crypto.randomBytes(6).toString("hex");
const _cacheKey = (url) =>
  crypto.createHash("sha256").update(url.trim()).digest("hex").slice(0, 16);
const _parseTags = (raw) => {
  try {
    return JSON.parse(raw || "[]");
  } catch {
    return [];
  }
};

function _rebuildTags() {
  const rows = db
    .prepare("SELECT tags FROM ideas WHERE deleted_at IS NULL")
    .all();
  const counts = {};
  for (const row of rows) {
    const tags = _parseTags(row.tags);
    for (const t of tags) counts[t] = (counts[t] || 0) + 1;
  }
  db.exec("DELETE FROM tags");
  const ins = db.prepare("INSERT INTO tags (name, count) VALUES (?, ?)");
  for (const [name, count] of Object.entries(counts)) {
    ins.run(name, count);
  }
}

function _rowToIdea(row) {
  if (!row) return null;
  return {
    id: row.id,
    content: row.content,
    tags: _parseTags(row.tags),
    pinned: !!row.pinned,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    ...(row.deleted_at != null ? { deletedAt: row.deleted_at } : {}),
  };
}

// ── MIME types ──────────────────────────────────────────────────────────────
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".map": "application/json",
};

// ── API Router ──────────────────────────────────────────────────────────────
function sendJSON(res, data, status = 200) {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

function sendError(res, msg, status = 400) {
  sendJSON(res, { error: msg }, status);
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      try {
        resolve(JSON.parse(Buffer.concat(chunks).toString()));
      } catch {
        resolve({});
      }
    });
    req.on("error", reject);
  });
}

// Parse URL pathname and searchParams
function parseURL(req) {
  const u = new URL(req.url, `http://localhost:${PORT}`);
  return { pathname: u.pathname, searchParams: u.searchParams };
}

async function handleAPI(req, res, pathname) {
  const method = req.method;
  const { searchParams } = parseURL(req);

  // ── Health ──
  if (pathname === "/api/health" && method === "GET") {
    return sendJSON(res, { ok: true });
  }

  // ── Ideas: list ──
  if (pathname === "/api/ideas" && method === "GET") {
    const tag = searchParams.get("tag");
    const q = searchParams.get("q");
    let sql = "SELECT * FROM ideas WHERE deleted_at IS NULL";
    const params = [];
    if (tag) {
      sql += " AND tags LIKE ?";
      params.push(`%"${tag}"%`);
    }
    sql += " ORDER BY pinned DESC, created_at DESC";
    const rows = db.prepare(sql).all(...params);
    let ideas = rows.map(_rowToIdea);
    if (q) {
      const lq = q.toLowerCase();
      ideas = ideas.filter(
        (i) =>
          i.content.toLowerCase().includes(lq) ||
          i.tags.some((t) => t.toLowerCase().includes(lq))
      );
    }
    return sendJSON(res, ideas);
  }

  // ── Ideas: archived list ──
  if (pathname === "/api/ideas/archived" && method === "GET") {
    const rows = db
      .prepare("SELECT * FROM ideas WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")
      .all();
    return sendJSON(res, rows.map(_rowToIdea));
  }

  // ── Ideas: create ──
  if (pathname === "/api/ideas" && method === "POST") {
    const body = await readBody(req);
    const now = _now();
    const id = body.id || _newId();
    const idea = {
      id,
      content: (body.content || "").trim(),
      tags: [...new Set(body.tags || [])],
      pinned: body.pinned ? 1 : 0,
      created_at: body.createdAt || now,
      updated_at: body.updatedAt || now,
      deleted_at: null,
    };
    db.prepare(
      "INSERT INTO ideas (id, content, tags, pinned, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    ).run(idea.id, idea.content, JSON.stringify(idea.tags), idea.pinned, idea.created_at, idea.updated_at, idea.deleted_at);
    _rebuildTags();
    return sendJSON(res, _rowToIdea(db.prepare("SELECT * FROM ideas WHERE id = ?").get(idea.id)));
  }

  // ── Ideas: update ──
  const updateMatch = pathname.match(/^\/api\/ideas\/([^/]+)$/);
  if (updateMatch && method === "PUT") {
    const id = updateMatch[1];
    const body = await readBody(req);
    const row = db.prepare("SELECT * FROM ideas WHERE id = ? AND deleted_at IS NULL").get(id);
    if (!row) return sendError(res, "idea not found", 404);
    const tags = body.tags !== undefined ? [...new Set(body.tags)] : _parseTags(row.tags);
    const content = body.content !== undefined ? body.content.trim() : row.content;
    const pinned = body.pinned !== undefined ? (body.pinned ? 1 : 0) : row.pinned;
    const now = _now();
    db.prepare("UPDATE ideas SET content=?, tags=?, pinned=?, updated_at=? WHERE id=?").run(
      content, JSON.stringify(tags), pinned, now, id
    );
    _rebuildTags();
    return sendJSON(res, _rowToIdea(db.prepare("SELECT * FROM ideas WHERE id = ?").get(id)));
  }

  // ── Ideas: delete (soft) ──
  if (updateMatch && method === "DELETE") {
    const id = updateMatch[1];
    const row = db.prepare("SELECT * FROM ideas WHERE id = ?").get(id);
    if (!row) return sendError(res, "idea not found", 404);
    const now = _now();
    db.prepare("UPDATE ideas SET deleted_at=?, updated_at=? WHERE id=?").run(now, now, id);
    _rebuildTags();
    return sendJSON(res, { ok: true });
  }

  // ── Ideas: restore ──
  const restoreMatch = pathname.match(/^\/api\/ideas\/([^/]+)\/restore$/);
  if (restoreMatch && method === "POST") {
    const id = restoreMatch[1];
    const row = db.prepare("SELECT * FROM ideas WHERE id = ?").get(id);
    if (!row) return sendError(res, "idea not found", 404);
    const now = _now();
    db.prepare("UPDATE ideas SET deleted_at=NULL, updated_at=? WHERE id=?").run(now, id);
    _rebuildTags();
    return sendJSON(res, _rowToIdea(db.prepare("SELECT * FROM ideas WHERE id = ?").get(id)));
  }

  // ── Ideas: toggle pin ──
  const pinMatch = pathname.match(/^\/api\/ideas\/([^/]+)\/pin$/);
  if (pinMatch && method === "POST") {
    const id = pinMatch[1];
    const row = db.prepare("SELECT * FROM ideas WHERE id = ? AND deleted_at IS NULL").get(id);
    if (!row) return sendError(res, "idea not found", 404);
    const now = _now();
    db.prepare("UPDATE ideas SET pinned=?, updated_at=? WHERE id=?").run(row.pinned ? 0 : 1, now, id);
    return sendJSON(res, _rowToIdea(db.prepare("SELECT * FROM ideas WHERE id = ?").get(id)));
  }

  // ── Purge archived ──
  if (pathname === "/api/archived" && method === "DELETE") {
    db.exec("DELETE FROM ideas WHERE deleted_at IS NOT NULL");
    _rebuildTags();
    return sendJSON(res, { ok: true });
  }

  // ── Tags ──
  if (pathname === "/api/tags" && method === "GET") {
    const rows = db.prepare("SELECT name, count FROM tags ORDER BY count DESC, name").all();
    return sendJSON(res, rows);
  }

  // ── Export ──
  if (pathname === "/api/export" && method === "GET") {
    const all = db.prepare("SELECT * FROM ideas").all();
    const ideas = all.filter((r) => r.deleted_at === null).map(_rowToIdea);
    const archived = all.filter((r) => r.deleted_at !== null).map(_rowToIdea);
    return sendJSON(res, { ideas, archived, exportedAt: new Date().toISOString() });
  }

  // ── Import ──
  if (pathname === "/api/import" && method === "POST") {
    const body = await readBody(req);
    const ideasIn = body.ideas || [];
    const archivedIn = body.archived || [];
    const now = _now();
    db.exec("DELETE FROM ideas");
    const ins = db.prepare(
      "INSERT INTO ideas (id, content, tags, pinned, created_at, updated_at, deleted_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    );
    for (const item of [...ideasIn, ...archivedIn]) {
      const deleted = item.deletedAt;
      ins.run(
        item.id || _newId(),
        (item.content || "").trim(),
        JSON.stringify([...new Set(item.tags || [])]),
        item.pinned ? 1 : 0,
        item.createdAt || now,
        item.updatedAt || now,
        deleted != null ? deleted : null
      );
    }
    _rebuildTags();
    return sendJSON(res, { ok: true, imported: ideasIn.length + archivedIn.length });
  }

  // ── Mindmap: create ──
  if (pathname === "/api/mindmap" && method === "POST") {
    const body = await readBody(req);
    const url = (body.url || "").trim();
    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      return sendJSON(res, { task_id: null, error: "请提供有效的视频链接" });
    }
    const key = _cacheKey(url);
    // Check cache
    const cached = db.prepare("SELECT * FROM mindmaps WHERE url_hash = ?").get(key);
    if (cached) {
      return sendJSON(res, { task_id: null, result: { id: key, cached: true, mindmap_md: cached.mindmap_md } });
    }
    // Create task (stub - will be processed async)
    const taskId = _newId();
    db.prepare("INSERT INTO tasks (task_id, url, status) VALUES (?, ?, 'pending')").run(taskId, url);
    // Return sample mindmap immediately
    const sampleMd = `# ${url}\n\n## 视频分析\n\n由于部署环境限制，视频自动解析功能暂不可用。\n\n### 建议\n- 请本地运行 Python 后端以使用完整功能\n- 或在开发环境下使用视频导图`;
    db.prepare("INSERT OR IGNORE INTO mindmaps (url_hash, url, mindmap_md) VALUES (?, ?, ?)").run(key, url, sampleMd);
    return sendJSON(res, { task_id: taskId });
  }

  // ── Mindmap: get result ──
  const mindmapGetMatch = pathname.match(/^\/api\/mindmap\/([^/]+)$/);
  if (mindmapGetMatch && method === "GET") {
    const taskId = mindmapGetMatch[1];
    const task = db.prepare("SELECT * FROM tasks WHERE task_id = ?").get(taskId);
    if (!task) return sendError(res, "task not found", 404);
    const result = task.result ? JSON.parse(task.result) : null;
    return sendJSON(res, { status: task.status, result, error: task.error || undefined });
  }

  // ── Admin: regenerate mindmaps ──
  if (pathname === "/api/admin/regenerate-mindmaps" && method === "POST") {
    return sendJSON(res, { ok: true, message: "Not available in serverless deployment" });
  }

  // ── 404 for unknown API routes ──
  return sendError(res, "not found", 404);
}

// ── Static file serving ────────────────────────────────────────────────────
function serveStatic(req, res, pathname) {
  let filePath = pathname === "/" ? "/index.html" : pathname;
  const fullPath = path.join(DIST, filePath);

  fs.readFile(fullPath, (err, data) => {
    if (err) {
      // SPA fallback: serve index.html for all non-file routes
      const indexPath = path.join(DIST, "index.html");
      fs.readFile(indexPath, (err2, data2) => {
        if (err2) {
          res.writeHead(404, { "Content-Type": "text/plain" });
          res.end("Not Found");
          return;
        }
        res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
        res.end(data2);
      });
      return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, { "Content-Type": MIME[ext] || "application/octet-stream" });
    res.end(data);
  });
}

// ── Server ─────────────────────────────────────────────────────────────────
const server = http.createServer((req, res) => {
  const { pathname } = parseURL(req);

  // CORS headers
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, PATCH, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    res.end();
    return;
  }

  if (pathname.startsWith("/api/")) {
    handleAPI(req, res, pathname).catch((err) => {
      console.error("API Error:", err);
      sendError(res, "Internal Server Error", 500);
    });
  } else {
    serveStatic(req, res, pathname);
  }
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`IdeaBox server running on http://0.0.0.0:${PORT}`);
});