"""TelemetryStore — the ONE owner of the telemetry SQLite connection.

Merges the former ``store/dao.py`` (CRUD) and ``store/schema.py`` (migrations
+ the pragma'd connection factory) into a single class so no other module
ever touches a ``sqlite3.Connection`` against this database (K8 / bug
``panel-telemetry-sqlite-corrupts-under-concurrent-access``, deferred for lack
of an owner — this class is that owner).

Connection discipline:
    * ``open_write()`` opens (or reopens) THE write connection this store
      instance holds — WAL + synchronous=NORMAL + foreign_keys=ON +
      busy_timeout.  Every CRUD method below operates on it.
    * ``open_read()`` returns a **new, standalone** read-only connection on
      every call — callers (the aggregator's per-HTTP-request queries) each
      get their own handle so concurrent ``ThreadingHTTPServer`` worker
      threads never share one (the exact scenario that corrupted the store).
    * ``migrate()`` / ``integrity_check()`` / ``quarantine()`` / ``close()``
      round out the lifecycle nobody else needs to reach into ``_conn`` for.

Decision references:
    D-AM-08  — PRAGMA user_version + linear Python migrations
    D-AM-15  — WAL + synchronous=NORMAL + foreign_keys=ON
"""

from __future__ import annotations

import datetime
import logging
import pathlib
import sqlite3
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SCHEMA_VERSION: int = 6


# ---------------------------------------------------------------------------
# Frozen dataclasses mirroring each table in the schema below. No content
# fields are present — the privacy invariant (D-AM-03) is enforced at the
# model layer. The ONE model module for row-level shapes (K8): the read-model
# (aggregated/API) shapes live separately in core.models.telemetry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReaderState:
    """Checkpoint per source file (jsonl or Codex sqlite)."""

    file_path: str
    kind: str  # 'claude_jsonl' | 'codex_sqlite'
    byte_offset: int
    last_mtime: float
    last_inode: int
    error_count: int
    last_ingest_at: str


@dataclass(frozen=True)
class Session:
    """One row per sessionId (Claude Code) or thread_id (Codex)."""

    session_id: str
    provider: str  # 'claude' | 'codex'
    agent_name: str | None
    ai_title: str | None
    entrypoint: str | None
    cwd: str | None
    git_branch: str | None
    is_sidechain: int  # 0 | 1
    sub_slug: str | None
    first_event_at: str
    last_event_at: str
    status: str  # 'open' | 'closed'


@dataclass(frozen=True)
class Agent:
    """Distinct agent observed across all sessions."""

    name: str
    provider: str
    is_subagent: int  # 0 | 1
    first_seen_at: str
    last_seen_at: str


@dataclass(frozen=True)
class Event:
    """One usage event per 'assistant' response — no content fields."""

    event_id: str
    session_id: str
    agent_name: str
    model: str
    occurred_at: str
    tokens_input: int
    tokens_cache_read: int
    tokens_cache_create: int
    tokens_output: int
    cost_micro_usd: int | None  # NULL when model unknown or Codex aggregated
    pricing_version: str | None
    suspect: int  # 0 | 1 — devops T7 bounds check


@dataclass(frozen=True)
class EventCostRow:
    """One events row awaiting cost backfill (cost_micro_usd IS NULL)."""

    event_id: str
    model: str
    occurred_at: str
    tokens_input: int
    tokens_cache_read: int
    tokens_cache_create: int
    tokens_output: int


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

_SQLITE_FILENAME = "telemetry.sqlite"


def _open_pragma_connection(db_path: pathlib.Path, *, read_only: bool) -> sqlite3.Connection:
    """Open a pragma'd SQLite connection to *db_path*.

    This function is the ONLY sanctioned ``sqlite3.connect`` call site for the
    telemetry store (v0.1.52 FR3, re-affirmed by K8): every writer and every
    reader of this database routes through it via a ``TelemetryStore`` method.
    Two modes:

    Writable (default) — WAL + synchronous=NORMAL + foreign_keys=ON + busy_timeout.

    Read-only (``read_only=True``) — ``file:{db_path}?mode=ro`` via URI, with
    ONLY ``busy_timeout`` applied (WAL is a write; a read-only open must never
    flip it). Read-only connections are what the aggregator's per-request
    queries use so concurrent ``ThreadingHTTPServer`` worker threads never
    share a connection.
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


class TelemetryStore:
    """Owns the telemetry SQLite connection for one process's use of it.

    Construct with the database path (``TelemetryStore(db_path)``); nothing
    is opened until ``open_write()``/``open_read()`` is called. Every write
    (readers, cost backfill) goes through the connection ``open_write()``
    binds to this instance; every read either reuses that same connection or
    opens its OWN fresh one via ``open_read()`` — never shared across threads.
    """

    def __init__(self, db_path: pathlib.Path) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @classmethod
    def from_connection(cls, conn: sqlite3.Connection) -> TelemetryStore:
        """Wrap an already-open connection (tests: in-memory or pre-seeded files)."""
        store = cls(pathlib.Path(""))
        conn.row_factory = sqlite3.Row
        store._conn = conn
        return store

    @property
    def db_path(self) -> pathlib.Path:
        return self._db_path

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def open_write(self) -> TelemetryStore:
        """Open (or reopen) this store's WRITE connection. Returns self for chaining."""
        self._conn = _open_pragma_connection(self._db_path, read_only=False)
        self._conn.row_factory = sqlite3.Row
        return self

    def open_read(self) -> sqlite3.Connection:
        """Return a NEW read-only connection — caller closes it.

        One per caller (each panel HTTP request thread opens and closes its
        own): concurrent readers must never share a handle.
        """
        return _open_pragma_connection(self._db_path, read_only=True)

    def migrate(self) -> None:
        """Apply outstanding migrations to this store's open write connection."""
        assert self._conn is not None, "open_write() before migrate()"
        apply_migrations(self._conn)

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Integrity + quarantine (T-AM-21 — moved here from TelemetryService so
    # the store, not the service, owns every fact about this file on disk)
    # ------------------------------------------------------------------

    def integrity_check(self) -> bool:
        """Run PRAGMA integrity_check via a throwaway read-only connection.

        Never touches ``self._conn`` — this must be safe to call BEFORE a
        write connection is ever opened against a possibly-corrupt file.
        """
        if not self._db_path.exists():
            return True
        try:
            conn = _open_pragma_connection(self._db_path, read_only=True)
        except sqlite3.DatabaseError:
            return False
        try:
            # sqlite3.connect() is lazy — "file is not a database" surfaces only
            # once a statement actually runs, as DatabaseError (OperationalError's
            # parent), not at connect() time. Catch both here, not just at open.
            result = conn.execute("PRAGMA integrity_check").fetchone()
            return result is not None and result[0] == "ok"
        except sqlite3.DatabaseError:
            return False
        finally:
            conn.close()

    def quarantine(self) -> pathlib.Path | None:
        """Rename the corrupt DB (+ WAL/SHM siblings) to ``*.corrupt.<utc_ts>``.

        Returns the quarantine path on success, ``None`` on an OSError (logged,
        never raised — the caller degrades gracefully either way).
        """
        ts = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%dT%H%M%SZ")
        quarantine_path = self._db_path.parent / f"{self._db_path.name}.corrupt.{ts}"
        try:
            pathlib.Path(self._db_path).replace(quarantine_path)
            # A WAL store is three files (telemetry.sqlite + -wal + -shm). Move
            # the siblings WITH the corrupt main DB so a fresh writer never
            # picks up phantom WAL frames stranded next to a clean file.
            for suffix in ("-wal", "-shm"):
                sibling = self._db_path.parent / f"{self._db_path.name}{suffix}"
                if sibling.exists():
                    sibling.replace(quarantine_path.parent / f"{quarantine_path.name}{suffix}")
        except OSError as exc:
            logger.error(
                "TelemetryStore: could not quarantine corrupt DB %s -> %s: %s",
                self._db_path,
                quarantine_path,
                exc,
            )
            return None
        return quarantine_path

    # ------------------------------------------------------------------
    # Write methods (operate on the connection open_write()/from_connection() bound)
    # ------------------------------------------------------------------

    def upsert_reader_state(self, state: ReaderState) -> None:
        """Insert or replace a reader_state row."""
        conn = self._require_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO reader_state
                (file_path, kind, byte_offset, last_mtime, last_inode,
                 error_count, last_ingest_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.file_path,
                state.kind,
                state.byte_offset,
                state.last_mtime,
                state.last_inode,
                state.error_count,
                state.last_ingest_at,
            ),
        )
        conn.commit()

    def upsert_session(self, session: Session) -> None:
        """Insert or replace a sessions row."""
        conn = self._require_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO sessions
                (session_id, provider, agent_name, ai_title, entrypoint,
                 cwd, git_branch, is_sidechain, sub_slug,
                 first_event_at, last_event_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session.session_id,
                session.provider,
                session.agent_name,
                session.ai_title,
                session.entrypoint,
                session.cwd,
                session.git_branch,
                session.is_sidechain,
                session.sub_slug,
                session.first_event_at,
                session.last_event_at,
                session.status,
            ),
        )
        conn.commit()

    def upsert_agent(self, agent: Agent) -> None:
        """Insert or replace an agents row."""
        conn = self._require_conn()
        conn.execute(
            """
            INSERT OR REPLACE INTO agents
                (name, provider, is_subagent, first_seen_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                agent.name,
                agent.provider,
                agent.is_subagent,
                agent.first_seen_at,
                agent.last_seen_at,
            ),
        )
        conn.commit()

    def insert_event(self, event: Event) -> None:
        """Insert an event; silently skip if event_id already exists (idempotent)."""
        conn = self._require_conn()
        conn.execute(
            """
            INSERT OR IGNORE INTO events
                (event_id, session_id, agent_name, model, occurred_at,
                 tokens_input, tokens_cache_read, tokens_cache_create,
                 tokens_output, cost_micro_usd, pricing_version, suspect)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.session_id,
                event.agent_name,
                event.model,
                event.occurred_at,
                event.tokens_input,
                event.tokens_cache_read,
                event.tokens_cache_create,
                event.tokens_output,
                event.cost_micro_usd,
                event.pricing_version,
                event.suspect,
            ),
        )
        conn.commit()

    def iter_events_missing_cost(self) -> list[EventCostRow]:
        """Return every event whose cost is not yet backfilled."""
        conn = self._require_conn()
        rows = conn.execute(
            """
            SELECT event_id, model, occurred_at,
                   tokens_input, tokens_cache_read, tokens_cache_create, tokens_output
            FROM events
            WHERE cost_micro_usd IS NULL
            """
        ).fetchall()
        return [
            EventCostRow(
                event_id=r["event_id"],
                model=r["model"],
                occurred_at=r["occurred_at"],
                tokens_input=r["tokens_input"],
                tokens_cache_read=r["tokens_cache_read"],
                tokens_cache_create=r["tokens_cache_create"],
                tokens_output=r["tokens_output"],
            )
            for r in rows
        ]

    def update_event_cost(
        self, event_id: str, cost_micro_usd: int, pricing_version: str | None
    ) -> None:
        """Backfill cost_micro_usd/pricing_version for one previously-NULL event."""
        conn = self._require_conn()
        conn.execute(
            "UPDATE events SET cost_micro_usd = ?, pricing_version = ? WHERE event_id = ?",
            (cost_micro_usd, pricing_version, event_id),
        )

    def commit(self) -> None:
        self._require_conn().commit()

    # ------------------------------------------------------------------
    # Read methods — always return dataclass instances, never sqlite3.Row
    # ------------------------------------------------------------------

    def get_reader_state(self, file_path: str) -> ReaderState | None:
        """Return the ReaderState for *file_path*, or None if not found."""
        conn = self._require_conn()
        row = conn.execute(
            "SELECT * FROM reader_state WHERE file_path = ?", (file_path,)
        ).fetchone()
        if row is None:
            return None
        return ReaderState(
            file_path=row["file_path"],
            kind=row["kind"],
            byte_offset=row["byte_offset"],
            last_mtime=row["last_mtime"],
            last_inode=row["last_inode"],
            error_count=row["error_count"],
            last_ingest_at=row["last_ingest_at"],
        )

    def list_agents(self) -> list[Agent]:
        """Return all agents ordered by name."""
        conn = self._require_conn()
        rows = conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
        return [
            Agent(
                name=r["name"],
                provider=r["provider"],
                is_subagent=r["is_subagent"],
                first_seen_at=r["first_seen_at"],
                last_seen_at=r["last_seen_at"],
            )
            for r in rows
        ]

    def list_sessions_by_agent(self, agent_name: str) -> list[Session]:
        """Return sessions for *agent_name* ordered by first_event_at ascending."""
        conn = self._require_conn()
        rows = conn.execute(
            """
            SELECT * FROM sessions
            WHERE agent_name = ?
            ORDER BY first_event_at ASC
            """,
            (agent_name,),
        ).fetchall()
        return [
            Session(
                session_id=r["session_id"],
                provider=r["provider"],
                agent_name=r["agent_name"],
                ai_title=r["ai_title"],
                entrypoint=r["entrypoint"],
                cwd=r["cwd"],
                git_branch=r["git_branch"],
                is_sidechain=r["is_sidechain"],
                sub_slug=r["sub_slug"],
                first_event_at=r["first_event_at"],
                last_event_at=r["last_event_at"],
                status=r["status"],
            )
            for r in rows
        ]

    def _require_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("TelemetryStore: open_write() (or from_connection()) first")
        return self._conn


__all__ = [
    "SCHEMA_VERSION",
    "Agent",
    "Event",
    "EventCostRow",
    "ReaderState",
    "Session",
    "TelemetryStore",
    "apply_migrations",
]
