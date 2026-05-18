"""SQLite schema migrations for the telemetry store.

Uses PRAGMA user_version to track applied migrations linearly (1 → 5).
Every migration step is idempotent: CREATE TABLE IF NOT EXISTS, etc.

Decision references:
    D-AM-08  — PRAGMA user_version + linear Python migrations
    D-AM-15  — WAL + synchronous=NORMAL + foreign_keys=ON
"""

from __future__ import annotations

import pathlib
import sqlite3

SCHEMA_VERSION: int = 5

# ---------------------------------------------------------------------------
# Individual migration SQL blocks — indexed by the version they produce.
# ---------------------------------------------------------------------------

_MIGRATION_1 = """
CREATE TABLE IF NOT EXISTS reader_state (
    file_path     TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    byte_offset   INTEGER NOT NULL DEFAULT 0,
    last_mtime    REAL    NOT NULL DEFAULT 0.0,
    last_inode    INTEGER NOT NULL DEFAULT 0,
    error_count   INTEGER NOT NULL DEFAULT 0,
    last_ingest_at TEXT   NOT NULL
);
"""

_MIGRATION_2 = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id     TEXT PRIMARY KEY,
    provider       TEXT NOT NULL,
    agent_name     TEXT,
    ai_title       TEXT,
    entrypoint     TEXT,
    cwd            TEXT,
    git_branch     TEXT,
    is_sidechain   INTEGER NOT NULL DEFAULT 0,
    sub_slug       TEXT,
    first_event_at TEXT NOT NULL,
    last_event_at  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'closed'
);
CREATE INDEX IF NOT EXISTS idx_sessions_agent
    ON sessions(agent_name);
CREATE INDEX IF NOT EXISTS idx_sessions_provider_first
    ON sessions(provider, first_event_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_cwd
    ON sessions(cwd);
"""

_MIGRATION_3 = """
CREATE TABLE IF NOT EXISTS agents (
    name           TEXT PRIMARY KEY,
    provider       TEXT NOT NULL,
    is_subagent    INTEGER NOT NULL DEFAULT 0,
    first_seen_at  TEXT NOT NULL,
    last_seen_at   TEXT NOT NULL
);
"""

_MIGRATION_4 = """
CREATE TABLE IF NOT EXISTS events (
    event_id            TEXT PRIMARY KEY,
    session_id          TEXT NOT NULL,
    agent_name          TEXT NOT NULL,
    model               TEXT NOT NULL,
    occurred_at         TEXT NOT NULL,
    tokens_input        INTEGER NOT NULL DEFAULT 0,
    tokens_cache_read   INTEGER NOT NULL DEFAULT 0,
    tokens_cache_create INTEGER NOT NULL DEFAULT 0,
    tokens_output       INTEGER NOT NULL DEFAULT 0,
    cost_micro_usd      INTEGER,
    pricing_version     TEXT,
    suspect             INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (agent_name) REFERENCES agents(name)
);
CREATE INDEX IF NOT EXISTS idx_events_session
    ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_agent_time
    ON events(agent_name, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_occurred
    ON events(occurred_at DESC);
"""

_MIGRATION_5 = (
    # DEAD: replaced by canonical workflow reader in panel-r3; do not extend; see backlog/candidates.md
    "CREATE TABLE IF NOT EXISTS workflows ("
    "    name           TEXT PRIMARY KEY,"
    "    source_path    TEXT NOT NULL,"
    "    description    TEXT,"
    "    apply_to       TEXT,"
    "    discovered_at  TEXT NOT NULL,"
    "    last_seen_at   TEXT NOT NULL"
    ");\n"
    # DEAD: replaced by canonical workflow reader in panel-r3; do not extend; see backlog/candidates.md
    "CREATE TABLE IF NOT EXISTS workflow_agents ("
    "    workflow_name  TEXT NOT NULL,"
    "    agent_name     TEXT NOT NULL,"
    "    PRIMARY KEY (workflow_name, agent_name),"
    "    FOREIGN KEY (workflow_name) REFERENCES workflows(name) ON DELETE CASCADE,"
    "    FOREIGN KEY (agent_name)    REFERENCES agents(name)"
    ");\n"
)

_MIGRATIONS: list[str] = [
    _MIGRATION_1,
    _MIGRATION_2,
    _MIGRATION_3,
    _MIGRATION_4,
    _MIGRATION_5,
]


def open_connection(db_path: pathlib.Path) -> sqlite3.Connection:
    """Open a SQLite connection to *db_path* with recommended PRAGMAs set.

    PRAGMAs applied:
        - journal_mode = WAL       (concurrent readers, one writer)
        - synchronous  = NORMAL    (durability trade-off, safe with WAL)
        - foreign_keys = ON        (referential integrity enforced)
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply outstanding migrations to *conn* using PRAGMA user_version.

    Migrations are linear: version N applies SQL block N and sets
    PRAGMA user_version = N.  Already-applied blocks are skipped so the
    function is safe to call repeatedly (idempotent).
    """
    current_version: int = conn.execute("PRAGMA user_version").fetchone()[0]

    for idx, sql_block in enumerate(_MIGRATIONS):
        target_version = idx + 1
        if current_version >= target_version:
            continue
        conn.executescript(sql_block)
        # user_version must be set outside a transaction via executescript;
        # use execute to set it in a dedicated statement.
        conn.execute(f"PRAGMA user_version = {target_version}")
        conn.commit()
        current_version = target_version
