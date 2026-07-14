"""Frozen dataclasses mirroring each table in the telemetry SQLite schema.

Column types follow the SPEC § Schema DDL exactly.  No content fields are
present — the privacy invariant (D-AM-03) is enforced at the model layer.
"""

from __future__ import annotations

from dataclasses import dataclass


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
