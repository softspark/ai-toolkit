#!/usr/bin/env python3
"""Initialize SQLite memory database for ai-toolkit memory-pack.

Creates ~/.ai-toolkit/memory.db with sessions, observations, and FTS5 tables.
Safe to run multiple times (uses IF NOT EXISTS).

Usage: python3 app/plugins/memory-pack/scripts/init_db.py
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

DB_DIR = Path.home() / ".ai-toolkit"
DB_PATH = DB_DIR / "memory.db"

SCHEMA = """
-- Sessions table: one row per Claude Code session
CREATE TABLE IF NOT EXISTS sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT UNIQUE NOT NULL,
  project_dir TEXT,
  started_at TEXT DEFAULT (datetime('now')),
  ended_at TEXT,
  summary TEXT
);

-- Observations table: captured tool actions within a session
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL,
  tool_name TEXT,
  content TEXT NOT NULL,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Full-text search index on observations
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
  content,
  tool_name,
  content='observations',
  content_rowid='id'
);

-- Trigger: keep FTS index in sync on INSERT
CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
  INSERT INTO observations_fts(rowid, content, tool_name)
  VALUES (new.id, new.content, new.tool_name);
END;

-- Trigger: keep FTS index in sync on DELETE
CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
  INSERT INTO observations_fts(observations_fts, rowid, content, tool_name)
  VALUES ('delete', old.id, old.content, old.tool_name);
END;

-- Trigger: keep FTS index in sync on UPDATE
CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
  INSERT INTO observations_fts(observations_fts, rowid, content, tool_name)
  VALUES ('delete', old.id, old.content, old.tool_name);
  INSERT INTO observations_fts(rowid, content, tool_name)
  VALUES (new.id, new.content, new.tool_name);
END;
"""


def main() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    existed = DB_PATH.is_file()
    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)
    conn.close()
    if existed:
        print(f"memory-pack: database verified at {DB_PATH} (data preserved)")
    else:
        print(f"memory-pack: database created at {DB_PATH}")


if __name__ == "__main__":
    main()
