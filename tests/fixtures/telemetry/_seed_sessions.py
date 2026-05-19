"""Seed script for tests/fixtures/telemetry/sessions_seeded.sqlite.

Creates (or re-creates) the fixture SQLite database deterministically.
Run with the dadaia venv:

    /home/marco/workspace/dadaia/.dadaia/.venv/bin/python \
        tests/fixtures/telemetry/_seed_sessions.py

Schema is applied via the production schema module to keep the fixture
in sync with any future migrations.

Seed layout (PR5-B4 requirements):
- >= 3 Claude sessions across two projects (dadaia-workspace, redacted-slug)
- >= 2 Codex sessions
- Mix of active / idle / ended statuses controlled by last_activity_at delta
- events rows with meaningful token counts so context_size_tokens is non-trivial
"""

from __future__ import annotations

import pathlib
import sqlite3
import sys

# Allow importing from the workspace package without installing.
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT))

from dadaia_workspace.features.telemetry.store.schema import apply_migrations  # noqa: E402

_FIXTURE_PATH = pathlib.Path(__file__).parent / "sessions_seeded.sqlite"

# ---------------------------------------------------------------------------
# Seed data
# ---------------------------------------------------------------------------
# Timestamps are deterministic fixed UTC strings.  Status in sessions table
# is "active", "open", or "closed"; queries.py maps: active→active,
# closed→ended, other→idle.

_SESSIONS: list[dict] = [
    # Claude session 1 — project: dadaia-workspace — status: active
    {
        "session_id": "claude-session-aaa111bbb222ccc3",
        "provider": "claude",
        "agent_name": "software-engineer",
        "ai_title": "Panel r5 Phase B implementation",
        "entrypoint": "cli",
        "cwd": "/home/user/workspace/dadaia/repos/dadaia-workspace",
        "git_branch": "release/panel-r5-v1",
        "is_sidechain": 0,
        "sub_slug": "dadaia-workspace",
        "first_event_at": "2026-05-19T07:00:00Z",
        "last_event_at": "2026-05-19T09:55:00Z",
        "status": "active",
    },
    # Claude session 2 — project: dadaia-workspace — status: idle (open)
    {
        "session_id": "claude-session-ddd444eee555fff6",
        "provider": "claude",
        "agent_name": "product-engineer",
        "ai_title": "SPEC authoring for panel-r5-v1",
        "entrypoint": "cli",
        "cwd": "/home/user/workspace/dadaia/repos/dadaia-workspace",
        "git_branch": "main",
        "is_sidechain": 0,
        "sub_slug": "dadaia-workspace",
        "first_event_at": "2026-05-19T05:00:00Z",
        "last_event_at": "2026-05-19T06:00:00Z",
        "status": "open",  # maps to idle
    },
    # Claude session 3 — project: redacted-slug — status: ended (closed)
    {
        "session_id": "claude-session-ggg777hhh888iii9",
        "provider": "claude",
        "agent_name": "game-developer",
        "ai_title": None,
        "entrypoint": "cli",
        "cwd": "/home/user/workspace/dadaia/repos/redacted-slug",
        "git_branch": "feature/aero-physics",
        "is_sidechain": 0,
        "sub_slug": "redacted-slug",
        "first_event_at": "2026-05-18T10:00:00Z",
        "last_event_at": "2026-05-18T12:30:00Z",
        "status": "closed",  # maps to ended
    },
    # Codex session 1 — project: dadaia-workspace — status: ended (closed)
    {
        "session_id": "codex-session-jjj000kkk111lll2",
        "provider": "codex",
        "agent_name": None,
        "ai_title": None,
        "entrypoint": "cli",
        "cwd": "/home/user/workspace/dadaia/repos/dadaia-workspace",
        "git_branch": "main",
        "is_sidechain": 0,
        "sub_slug": "dadaia-workspace",
        "first_event_at": "2026-05-19T04:00:00Z",
        "last_event_at": "2026-05-19T04:45:00Z",
        "status": "closed",  # maps to ended
    },
    # Codex session 2 — project: redacted-slug — status: idle (open)
    {
        "session_id": "codex-session-mmm333nnn444ooo5",
        "provider": "codex",
        "agent_name": None,
        "ai_title": None,
        "entrypoint": "cli",
        "cwd": "/home/user/workspace/dadaia/repos/redacted-slug",
        "git_branch": "main",
        "is_sidechain": 0,
        "sub_slug": "redacted-slug",
        "first_event_at": "2026-05-19T03:00:00Z",
        "last_event_at": "2026-05-19T03:30:00Z",
        "status": "open",  # maps to idle
    },
]

# agent_name must be registered in agents table (FK constraint)
_AGENTS: list[dict] = [
    {"name": "software-engineer", "provider": "claude", "is_subagent": 0,
     "first_seen_at": "2026-05-01T00:00:00Z", "last_seen_at": "2026-05-19T09:55:00Z"},
    {"name": "product-engineer", "provider": "claude", "is_subagent": 0,
     "first_seen_at": "2026-05-01T00:00:00Z", "last_seen_at": "2026-05-19T06:00:00Z"},
    {"name": "game-developer", "provider": "claude", "is_subagent": 0,
     "first_seen_at": "2026-05-01T00:00:00Z", "last_seen_at": "2026-05-18T12:30:00Z"},
]

# Events — each session gets multiple events with token counts.
# Codex events have cost_micro_usd = NULL (cost not tracked).
_EVENTS: list[dict] = [
    # ---- Claude session 1 (software-engineer, active) ----
    {
        "event_id": "evt-a1-1",
        "session_id": "claude-session-aaa111bbb222ccc3",
        "agent_name": "software-engineer",
        "model": "claude-sonnet-4-6",
        "occurred_at": "2026-05-19T07:05:00Z",
        "tokens_input": 8000,
        "tokens_cache_read": 12000,
        "tokens_cache_create": 3000,
        "tokens_output": 1200,
        "cost_micro_usd": 45000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    {
        "event_id": "evt-a1-2",
        "session_id": "claude-session-aaa111bbb222ccc3",
        "agent_name": "software-engineer",
        "model": "claude-sonnet-4-6",
        "occurred_at": "2026-05-19T07:30:00Z",
        "tokens_input": 10000,
        "tokens_cache_read": 18000,
        "tokens_cache_create": 2000,
        "tokens_output": 2000,
        "cost_micro_usd": 58000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    {
        "event_id": "evt-a1-3",
        "session_id": "claude-session-aaa111bbb222ccc3",
        "agent_name": "software-engineer",
        "model": "claude-sonnet-4-6",
        "occurred_at": "2026-05-19T09:55:00Z",
        "tokens_input": 12000,
        "tokens_cache_read": 22000,
        "tokens_cache_create": 4000,
        "tokens_output": 3000,
        "cost_micro_usd": 75000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    # ---- Claude session 2 (product-engineer, idle) ----
    {
        "event_id": "evt-a2-1",
        "session_id": "claude-session-ddd444eee555fff6",
        "agent_name": "product-engineer",
        "model": "claude-opus-4-7",
        "occurred_at": "2026-05-19T05:10:00Z",
        "tokens_input": 5000,
        "tokens_cache_read": 8000,
        "tokens_cache_create": 1000,
        "tokens_output": 800,
        "cost_micro_usd": 32000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    {
        "event_id": "evt-a2-2",
        "session_id": "claude-session-ddd444eee555fff6",
        "agent_name": "product-engineer",
        "model": "claude-opus-4-7",
        "occurred_at": "2026-05-19T06:00:00Z",
        "tokens_input": 7000,
        "tokens_cache_read": 14000,
        "tokens_cache_create": 2000,
        "tokens_output": 1500,
        "cost_micro_usd": 52000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    # ---- Claude session 3 (game-developer, ended) ----
    {
        "event_id": "evt-a3-1",
        "session_id": "claude-session-ggg777hhh888iii9",
        "agent_name": "game-developer",
        "model": "claude-sonnet-4-6",
        "occurred_at": "2026-05-18T10:05:00Z",
        "tokens_input": 3000,
        "tokens_cache_read": 4000,
        "tokens_cache_create": 500,
        "tokens_output": 600,
        "cost_micro_usd": 15000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    {
        "event_id": "evt-a3-2",
        "session_id": "claude-session-ggg777hhh888iii9",
        "agent_name": "game-developer",
        "model": "claude-sonnet-4-6",
        "occurred_at": "2026-05-18T12:30:00Z",
        "tokens_input": 6000,
        "tokens_cache_read": 9000,
        "tokens_cache_create": 1500,
        "tokens_output": 1200,
        "cost_micro_usd": 28000,
        "pricing_version": "2026-02-12",
        "suspect": 0,
    },
    # ---- Codex session 1 (ended) — cost_micro_usd = NULL ----
    {
        "event_id": "evt-c1-1",
        "session_id": "codex-session-jjj000kkk111lll2",
        "agent_name": "software-engineer",
        "model": "gpt-4o",
        "occurred_at": "2026-05-19T04:10:00Z",
        "tokens_input": 4000,
        "tokens_cache_read": 0,
        "tokens_cache_create": 0,
        "tokens_output": 800,
        "cost_micro_usd": None,  # Codex: no cost tracking
        "pricing_version": None,
        "suspect": 0,
    },
    {
        "event_id": "evt-c1-2",
        "session_id": "codex-session-jjj000kkk111lll2",
        "agent_name": "software-engineer",
        "model": "gpt-4o",
        "occurred_at": "2026-05-19T04:45:00Z",
        "tokens_input": 6000,
        "tokens_cache_read": 0,
        "tokens_cache_create": 0,
        "tokens_output": 1200,
        "cost_micro_usd": None,
        "pricing_version": None,
        "suspect": 0,
    },
    # ---- Codex session 2 (idle) — cost_micro_usd = NULL ----
    {
        "event_id": "evt-c2-1",
        "session_id": "codex-session-mmm333nnn444ooo5",
        "agent_name": "software-engineer",
        "model": "gpt-4o",
        "occurred_at": "2026-05-19T03:10:00Z",
        "tokens_input": 3000,
        "tokens_cache_read": 0,
        "tokens_cache_create": 0,
        "tokens_output": 500,
        "cost_micro_usd": None,
        "pricing_version": None,
        "suspect": 0,
    },
]


def seed(db_path: pathlib.Path) -> None:
    """(Re-)create the fixture database at *db_path*."""
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    apply_migrations(conn)

    # Insert agents first (FK dependency from events).
    conn.executemany(
        """
        INSERT INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)
        VALUES (:name, :provider, :is_subagent, :first_seen_at, :last_seen_at)
        """,
        _AGENTS,
    )

    conn.executemany(
        """
        INSERT INTO sessions (
            session_id, provider, agent_name, ai_title, entrypoint, cwd,
            git_branch, is_sidechain, sub_slug, first_event_at, last_event_at, status
        )
        VALUES (
            :session_id, :provider, :agent_name, :ai_title, :entrypoint, :cwd,
            :git_branch, :is_sidechain, :sub_slug, :first_event_at, :last_event_at, :status
        )
        """,
        _SESSIONS,
    )

    conn.executemany(
        """
        INSERT INTO events (
            event_id, session_id, agent_name, model, occurred_at,
            tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,
            cost_micro_usd, pricing_version, suspect
        )
        VALUES (
            :event_id, :session_id, :agent_name, :model, :occurred_at,
            :tokens_input, :tokens_cache_read, :tokens_cache_create, :tokens_output,
            :cost_micro_usd, :pricing_version, :suspect
        )
        """,
        _EVENTS,
    )
    conn.commit()
    conn.close()
    print(f"Seeded fixture: {db_path}")
    print(f"  Sessions: {len(_SESSIONS)} ({sum(1 for s in _SESSIONS if s['provider']=='claude')} claude, {sum(1 for s in _SESSIONS if s['provider']=='codex')} codex)")
    print(f"  Events:   {len(_EVENTS)}")


if __name__ == "__main__":
    seed(_FIXTURE_PATH)
