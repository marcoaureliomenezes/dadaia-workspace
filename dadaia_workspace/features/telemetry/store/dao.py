"""TelemetryDao — repository for the telemetry SQLite store.

All read methods return dataclass instances from store/models.py.
sqlite3.Row is used internally for safe column access and is never
returned to callers.

Write operations use INSERT OR REPLACE (upsert semantics) except for
events which uses INSERT OR IGNORE to guarantee idempotency on event_id.
"""

from __future__ import annotations

import sqlite3

from dadaia_workspace.features.telemetry.store.models import (
    Agent,
    Event,
    ReaderState,
    Session,
    Workflow,
    WorkflowAgent,
)


class TelemetryDao:
    """Repository over a single SQLite connection.

    The connection is held for the lifetime of this object.  Callers are
    responsible for calling apply_migrations() before constructing a DAO.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # Write methods
    # ------------------------------------------------------------------

    def upsert_reader_state(self, state: ReaderState) -> None:
        """Insert or replace a reader_state row."""
        self._conn.execute(
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
        self._conn.commit()

    def upsert_session(self, session: Session) -> None:
        """Insert or replace a sessions row."""
        self._conn.execute(
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
        self._conn.commit()

    def upsert_agent(self, agent: Agent) -> None:
        """Insert or replace an agents row."""
        self._conn.execute(
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
        self._conn.commit()

    def insert_event(self, event: Event) -> None:
        """Insert an event; silently skip if event_id already exists (idempotent)."""
        self._conn.execute(
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
        self._conn.commit()

    def upsert_workflow(self, workflow: Workflow) -> None:
        """Insert or replace a workflows row."""
        self._conn.execute(
            """
            INSERT OR REPLACE INTO workflows
                (name, source_path, description, apply_to,
                 discovered_at, last_seen_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                workflow.name,
                workflow.source_path,
                workflow.description,
                workflow.apply_to,
                workflow.discovered_at,
                workflow.last_seen_at,
            ),
        )
        self._conn.commit()

    def upsert_workflow_agent(self, link: WorkflowAgent) -> None:
        """Insert or ignore a workflow_agents link row."""
        self._conn.execute(
            """
            INSERT OR IGNORE INTO workflow_agents (workflow_name, agent_name)
            VALUES (?, ?)
            """,
            (link.workflow_name, link.agent_name),
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Read methods — always return dataclass instances, never sqlite3.Row
    # ------------------------------------------------------------------

    def get_reader_state(self, file_path: str) -> ReaderState | None:
        """Return the ReaderState for *file_path*, or None if not found."""
        row = self._conn.execute(
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
        rows = self._conn.execute("SELECT * FROM agents ORDER BY name").fetchall()
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

    def list_workflows(self) -> list[Workflow]:
        """Return all workflows ordered by name."""
        rows = self._conn.execute("SELECT * FROM workflows ORDER BY name").fetchall()
        return [
            Workflow(
                name=r["name"],
                source_path=r["source_path"],
                description=r["description"],
                apply_to=r["apply_to"],
                discovered_at=r["discovered_at"],
                last_seen_at=r["last_seen_at"],
            )
            for r in rows
        ]

    def list_sessions_by_agent(self, agent_name: str) -> list[Session]:
        """Return sessions for *agent_name* ordered by first_event_at ascending."""
        rows = self._conn.execute(
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
