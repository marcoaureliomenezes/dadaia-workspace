"""SQLite schema migrations for the telemetry store.

Uses PRAGMA user_version to track applied migrations linearly (1 → 6).
Every migration step is idempotent: CREATE TABLE IF NOT EXISTS, DROP TABLE IF EXISTS, etc.

Decision references:
    D-AM-08  — PRAGMA user_version + linear Python migrations
    D-AM-15  — WAL + synchronous=NORMAL + foreign_keys=ON
"""

from __future__ import annotations

import pathlib
import sqlite3

SCHEMA_VERSION: int = 6

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
    # DEAD: replaced by canonical workflow reader in panel-r3; do not extend.
    "CREATE TABLE IF NOT EXISTS workflows ("
    "    name           TEXT PRIMARY KEY,"
    "    source_path    TEXT NOT NULL,"
    "    description    TEXT,"
    "    apply_to       TEXT,"
    "    discovered_at  TEXT NOT NULL,"
    "    last_seen_at   TEXT NOT NULL"
    ");\n"
    # DEAD: replaced by canonical workflow reader in panel-r3; do not extend.
    "CREATE TABLE IF NOT EXISTS workflow_agents ("
    "    workflow_name  TEXT NOT NULL,"
    "    agent_name     TEXT NOT NULL,"
    "    PRIMARY KEY (workflow_name, agent_name),"
    "    FOREIGN KEY (workflow_name) REFERENCES workflows(name) ON DELETE CASCADE,"
    "    FOREIGN KEY (agent_name)    REFERENCES agents(name)"
    ");\n"
)

_MIGRATION_6 = (
    # Drop the DEAD tables created in migration 5 (replaced by canonical workflow
    # reader in panel-r3). FK child (workflow_agents) must be dropped before parent
    # (workflows) to satisfy referential integrity constraints.
    "DROP TABLE IF EXISTS workflow_agents;\nDROP TABLE IF EXISTS workflows;\n"
)

_MIGRATIONS: list[str] = [
    _MIGRATION_1,
    _MIGRATION_2,
    _MIGRATION_3,
    _MIGRATION_4,
    _MIGRATION_5,
    _MIGRATION_6,
]


# Milliseconds a connection waits on a locked table before raising
# ``sqlite3.OperationalError: database is locked``.  WAL keeps readers and the
# single writer off each other's backs; busy_timeout covers the brief exclusive
# lock a checkpoint takes so bursty concurrent access degrades to a short wait
# rather than a hard error.
_BUSY_TIMEOUT_MS: int = 5000


def open_connection(db_path: pathlib.Path, *, read_only: bool = False) -> sqlite3.Connection:
    """Open a pragma'd SQLite connection to *db_path*.

    This is the single sanctioned way to open a telemetry-store connection
    (v0.1.52 FR3).  Two modes:

    Writable (default) — applies the recommended write PRAGMAs:
        - journal_mode = WAL       (concurrent readers, one writer)
        - synchronous  = NORMAL    (durability trade-off, safe with WAL)
        - foreign_keys = ON        (referential integrity enforced)
        - busy_timeout = 5000 ms   (wait, don't fail, on a transient lock)

    Read-only (``read_only=True``) — opens ``file:{db_path}?mode=ro`` via a URI
    and applies ONLY ``busy_timeout``.  WAL is a *write* (it flips journal mode),
    so a read-only open must never set it; ``synchronous``/``foreign_keys`` are
    write-durability / mutation concerns irrelevant to a pure reader.  Read-only
    connections are what the panel's per-call store queries use so concurrent
    ThreadingHTTPServer worker threads never share a connection.
    """
    if read_only:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        return conn
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
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
