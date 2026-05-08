"""SQLite database bootstrap and connection factory."""

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS workspaces (
    root_path TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spec_context_projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    state TEXT NOT NULL CHECK(state IN ('inativo', 'standby', 'ativo')),
    context_dir TEXT,
    specs_dir TEXT,
    created_at TEXT NOT NULL,
    activated_at TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS spec_context_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_id INTEGER NOT NULL REFERENCES spec_context_projects(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK(role IN ('primary', 'secondary')),
    repo_ref TEXT NOT NULL,
    source_kind TEXT NOT NULL CHECK(source_kind IN ('remote_url', 'local_path')),
    repo_slug TEXT NOT NULL,
    materialized_path TEXT,
    has_specs_dir INTEGER NOT NULL DEFAULT 0 CHECK(has_specs_dir IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(context_id, repo_ref)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_one_active_context
ON spec_context_projects(state)
WHERE state = 'ativo';
"""


def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def bootstrap_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = get_connection(db_path)
    with conn:
        conn.executescript(SCHEMA)
    conn.close()
