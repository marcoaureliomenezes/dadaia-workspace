"""Tests for TelemetryAggregator (T-AM-11).

All tests use a synthetic in-memory SQLite database and a duck-typed
SpecContextService stub — no real operator data is read.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from dadaia_workspace.features.telemetry.aggregator.models import (
    AgentListResult,
    WorkflowListResult,
)
from dadaia_workspace.features.telemetry.aggregator.queries import TelemetryAggregator
from dadaia_workspace.features.telemetry.store.dao import TelemetryDao
from dadaia_workspace.features.telemetry.store.schema import apply_migrations

# ---------------------------------------------------------------------------
# Constants — synthetic fixture paths
# ---------------------------------------------------------------------------

_KNOWN_ROOT = "/home/marco/workspace/dadaia/repos/dadaia-workspace"
_UNKNOWN_ROOT = "/tmp/unknown-project"
_CONTEXT_SLUG = "dadaia-workspace"

_NOW = datetime.now(tz=UTC)
_NOW_ISO = _NOW.isoformat()
_RECENT_ISO = (_NOW - timedelta(days=5)).isoformat()
_OLD_ISO = (_NOW - timedelta(days=200)).isoformat()


# ---------------------------------------------------------------------------
# SpecContextService stub
# ---------------------------------------------------------------------------


class _ContextEntry:
    """Duck-typed context entry for the stub."""

    def __init__(self, slug: str, name: str, repo_root: str) -> None:
        self.slug = slug
        self.name = name
        self.repo_root = repo_root


class _FakeSCS:
    """Minimal duck-typed SpecContextService stub."""

    def __init__(self, entries: list[_ContextEntry] | None = None) -> None:
        self._entries = entries or [
            _ContextEntry(
                slug=_CONTEXT_SLUG,
                name="dadaia-workspace",
                repo_root=_KNOWN_ROOT,
            )
        ]

    def list_all(self) -> list[_ContextEntry]:
        return list(self._entries)


# ---------------------------------------------------------------------------
# Pricing module stub
# ---------------------------------------------------------------------------


class _FakePricing:
    """Minimal pricing stub that returns known values."""

    class _Row:
        def __init__(self, effective_from: date) -> None:
            self.effective_from = effective_from

    PRICING_TABLE: dict[str, list] = {
        "claude-sonnet-4-6": [_Row(date(2025, 1, 1))],
        "claude-opus-4-7": [_Row(date(2025, 1, 1))],
    }

    @staticmethod
    def pricing_age_days(models_used: list[str], when: Any = None) -> int | None:
        if not models_used:
            return None
        known = {"claude-sonnet-4-6", "claude-opus-4-7"}
        used_known = [m for m in models_used if m in known]
        if not used_known:
            return None
        ref = when or date.today()
        return (ref - date(2025, 1, 1)).days


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON")
    apply_migrations(conn)
    conn.row_factory = sqlite3.Row
    return conn


def _seed_db(conn: sqlite3.Connection) -> None:
    """Seed the in-memory DB with controlled test data.

    Layout:
    - Agent "claude (main)": 2 sessions in known root, 0 sidechain.
      - session-1: cwd=_KNOWN_ROOT, 2 events (cost known)
      - session-2: cwd=_KNOWN_ROOT, 1 event (cost known)
    - Agent "software-architect": 1 session in unknown root, is_sidechain=1.
      - session-3: cwd=_UNKNOWN_ROOT, 1 event (cost_micro_usd=NULL)
    - 1 event with suspect=1 (session-1, event-1)
    - 2 workflows: wf-alpha (linked to claude (main)), wf-beta (linked to software-architect)
    """
    # Agents
    conn.executemany(
        "INSERT OR REPLACE INTO agents (name, provider, is_subagent, first_seen_at, last_seen_at)"
        " VALUES (?, ?, ?, ?, ?)",
        [
            ("claude (main)", "claude", 0, _RECENT_ISO, _RECENT_ISO),
            ("software-architect", "claude", 1, _RECENT_ISO, _RECENT_ISO),
        ],
    )
    # Sessions
    conn.executemany(
        "INSERT OR REPLACE INTO sessions"
        " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
        "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                "session-1-abcdefgh",
                "claude",
                "claude (main)",
                None,
                "cli",
                _KNOWN_ROOT,
                "main",
                0,
                None,
                _RECENT_ISO,
                _RECENT_ISO,
                "closed",
            ),
            (
                "session-2-abcdefgh",
                "claude",
                "claude (main)",
                None,
                "cli",
                _KNOWN_ROOT,
                "feat/x",
                0,
                None,
                _RECENT_ISO,
                _RECENT_ISO,
                "closed",
            ),
            (
                "session-3-abcdefgh",
                "claude",
                "software-architect",
                None,
                "cli",
                _UNKNOWN_ROOT,
                None,
                1,
                None,
                _RECENT_ISO,
                _RECENT_ISO,
                "closed",
            ),
        ],
    )
    # Events
    # session-1 event-1: cost known, suspect=1
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ev-s1-1",
            "session-1-abcdefgh",
            "claude (main)",
            "claude-sonnet-4-6",
            _RECENT_ISO,
            1000,
            200,
            50,
            100,
            3000,
            "2025-01-01",
            1,
        ),
    )
    # session-1 event-2: cost known, suspect=0
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ev-s1-2",
            "session-1-abcdefgh",
            "claude (main)",
            "claude-sonnet-4-6",
            _RECENT_ISO,
            500,
            100,
            25,
            50,
            1500,
            "2025-01-01",
            0,
        ),
    )
    # session-2 event-1: cost known
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ev-s2-1",
            "session-2-abcdefgh",
            "claude (main)",
            "claude-sonnet-4-6",
            _RECENT_ISO,
            800,
            150,
            30,
            80,
            2000,
            "2025-01-01",
            0,
        ),
    )
    # session-3 event-1: cost NULL (codex-like)
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ev-s3-1",
            "session-3-abcdefgh",
            "software-architect",
            "claude-opus-4-7",
            _RECENT_ISO,
            2000,
            0,
            0,
            200,
            None,
            None,
            0,
        ),
    )
    # Workflows
    conn.executemany(
        "INSERT OR REPLACE INTO workflows (name, source_path, description, apply_to, discovered_at, last_seen_at)"
        " VALUES (?,?,?,?,?,?)",
        [
            (
                "wf-alpha",
                "/some/path/.claude/skills/wf-alpha/SKILL.md",
                "Alpha workflow",
                None,
                _RECENT_ISO,
                _RECENT_ISO,
            ),
            (
                "wf-beta",
                "/some/path/.agents/skills/wf-beta/SKILL.md",
                "Beta workflow",
                None,
                _RECENT_ISO,
                _RECENT_ISO,
            ),
        ],
    )
    # Workflow agents
    conn.executemany(
        "INSERT OR IGNORE INTO workflow_agents (workflow_name, agent_name) VALUES (?,?)",
        [
            ("wf-alpha", "claude (main)"),
            ("wf-beta", "software-architect"),
            ("wf-beta", "claude (main)"),
        ],
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Aggregator factory
# ---------------------------------------------------------------------------


def _make_aggregator(conn: sqlite3.Connection, scs: _FakeSCS | None = None) -> TelemetryAggregator:
    dao = TelemetryDao(conn)
    return TelemetryAggregator(
        dao=dao,
        spec_context_service=scs or _FakeSCS(),
        pricing_module=_FakePricing(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_agents_basic():
    """Two agents should be returned, sorted by cost desc."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    assert isinstance(result, AgentListResult)
    assert len(result.agents) == 2

    # claude (main) has cost 3000+1500+2000 = 6500 micro-USD = 0.0065 USD
    # software-architect has NULL cost → cost_known=False
    # So claude (main) sorts first.
    first = result.agents[0]
    assert first.agent_id == "claude (main)"
    assert first.session_count == 2
    assert first.cost_known is True
    assert first.total_cost_usd == pytest.approx(6500 / 1_000_000)

    second = result.agents[1]
    assert second.agent_id == "software-architect"
    assert second.cost_known is False
    assert second.total_cost_usd is None


def test_unassigned_bucket():
    """Agent in /tmp/unknown-project has an 'unassigned' context breakdown."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    arch = next(a for a in result.agents if a.agent_id == "software-architect")
    unassigned = next(cb for cb in arch.context_breakdown if cb.context_slug is None)
    assert unassigned.context_name == "unassigned"
    assert unassigned.session_count == 1


def test_assigned_context_breakdown():
    """claude (main) has 2 sessions mapped to the dadaia-workspace context."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    main = next(a for a in result.agents if a.agent_id == "claude (main)")
    dw_bucket = next(cb for cb in main.context_breakdown if cb.context_slug == _CONTEXT_SLUG)
    assert dw_bucket.session_count == 2
    # Cost in bucket should be sum of events from sessions 1 and 2.
    assert dw_bucket.cost_usd == pytest.approx((3000 + 1500 + 2000) / 1_000_000)


def test_cost_known_false_when_all_null():
    """Agent with all NULL cost_micro_usd → cost_known=False, total_cost_usd=None."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    arch = next(a for a in result.agents if a.agent_id == "software-architect")
    assert arch.cost_known is False
    assert arch.total_cost_usd is None


def test_cost_fractions_sum_to_one():
    """For an agent with known costs, context_breakdown fractions sum to 1."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    main = next(a for a in result.agents if a.agent_id == "claude (main)")
    fractions = [cb.cost_fraction for cb in main.context_breakdown if cb.cost_fraction is not None]
    if fractions:
        assert sum(fractions) == pytest.approx(1.0, abs=1e-6)


def test_recent_sessions_ordered_and_truncated():
    """At most 10 recent sessions, most-recent first, session_id_prefix 8 chars."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    main = next(a for a in result.agents if a.agent_id == "claude (main)")
    assert len(main.recent_sessions) <= 10
    for rs in main.recent_sessions:
        assert len(rs.session_id_prefix) == 8


def test_suspect_count():
    """Agent with 1 suspect event has suspect_count == 1."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    main = next(a for a in result.agents if a.agent_id == "claude (main)")
    assert main.suspect_count == 1


def test_pricing_age_days_surfaced():
    """pricing_age_days in result is not None when known models are in events."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_agents()

    assert result.pricing_age_days is not None
    assert result.pricing_age_days > 0


def test_workflow_list():
    """list_workflows returns both workflows with linked agent IDs."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    result = agg.list_workflows()

    assert isinstance(result, WorkflowListResult)
    assert len(result.workflows) == 2

    alpha = next(w for w in result.workflows if w.workflow_id == "wf-alpha")
    assert "claude (main)" in alpha.agent_ids
    assert alpha.source == ".claude/skills/"

    beta = next(w for w in result.workflows if w.workflow_id == "wf-beta")
    assert "software-architect" in beta.agent_ids
    assert beta.source == ".agents/skills/"


def test_sessions_by_agent_pagination():
    """list_sessions_by_agent respects limit and offset."""
    conn = _make_conn()
    _seed_db(conn)
    agg = _make_aggregator(conn)

    # claude (main) has 2 sessions.
    all_sessions = agg.list_sessions_by_agent("claude (main)", limit=50, offset=0)
    assert len(all_sessions) == 2

    # With limit=1, only 1 returned.
    page1 = agg.list_sessions_by_agent("claude (main)", limit=1, offset=0)
    assert len(page1) == 1

    # With offset=1, only remaining session.
    page2 = agg.list_sessions_by_agent("claude (main)", limit=50, offset=1)
    assert len(page2) == 1

    # Different session than page1 (different branch or cost distinguishes them).
    assert page1[0] != page2[0]


def test_window_days_excludes_old():
    """Event older than window_days is not included in totals."""
    conn = _make_conn()
    _seed_db(conn)

    # Add an old session + event for claude (main)
    conn.execute(
        "INSERT OR REPLACE INTO sessions"
        " (session_id, provider, agent_name, ai_title, entrypoint, cwd, git_branch,"
        "  is_sidechain, sub_slug, first_event_at, last_event_at, status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "session-old-abcde",
            "claude",
            "claude (main)",
            None,
            "cli",
            _KNOWN_ROOT,
            "old-branch",
            0,
            None,
            _OLD_ISO,
            _OLD_ISO,
            "closed",
        ),
    )
    conn.execute(
        "INSERT OR IGNORE INTO events"
        " (event_id, session_id, agent_name, model, occurred_at,"
        "  tokens_input, tokens_cache_read, tokens_cache_create, tokens_output,"
        "  cost_micro_usd, pricing_version, suspect)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "ev-old-1",
            "session-old-abcde",
            "claude (main)",
            "claude-sonnet-4-6",
            _OLD_ISO,
            9999999,
            0,
            0,
            0,
            9999000,
            "2025-01-01",
            0,
        ),
    )
    conn.commit()

    agg = _make_aggregator(conn)
    result = agg.list_agents(window_days=180)

    main = next(a for a in result.agents if a.agent_id == "claude (main)")
    # The old event has 9999000 micro-USD; if included it would dominate.
    # Existing cost = 6500 micro-USD = 0.0065 USD
    assert main.total_cost_usd == pytest.approx(6500 / 1_000_000)
