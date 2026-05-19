"""Unit tests for ClaudeRuntimeAdapter and CodexRuntimeAdapter.

Panel-r5-v1 PR5-A5.

Tests verify:
- ClaudeRuntimeAdapter.enrich_row: sets cumulative_cost_usd and cost_known=True
  when cost is present; pricing.compute_cost is NOT called (cost is computed by
  the aggregator from event-level micro-USD; the adapter only validates it).
- CodexRuntimeAdapter.enrich_row: sets cumulative_cost_usd=None, cost_known=False;
  pricing.compute_cost is NOT called.
- Both adapters satisfy the RuntimeAdapter protocol.
- Liveness classification for ClaudeRuntimeAdapter (with filesystem fakes).
- CodexRuntimeAdapter.liveness always returns "idle" in Phase A.
"""

from __future__ import annotations

import pathlib
import time
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionRow,
)
from dadaia_workspace.features.telemetry.aggregator.runtimes import (
    ClaudeRuntimeAdapter,
    CodexRuntimeAdapter,
    RuntimeAdapter,
)

# ---------------------------------------------------------------------------
# Fixtures — minimal SessionRow and SessionDetail
# ---------------------------------------------------------------------------

_NOW_ISO = datetime.now(tz=UTC).isoformat()


def _make_row(
    session_id: str = "sess-abcdefgh",
    runtime: str = "claude",
    cumulative_cost_usd: float | None = 0.006500,
    cost_known: bool = False,
) -> SessionRow:
    return SessionRow(
        session_id=session_id,
        runtime=runtime,
        project="alpha",
        cwd="/workspace",
        model="claude-sonnet-4-6",
        started_at=_NOW_ISO,
        last_activity_at=_NOW_ISO,
        message_count=3,
        context_size_tokens=1200,
        cumulative_cost_usd=cumulative_cost_usd,
        cost_known=cost_known,
        status="ended",
        agent_name="software-engineer",
        ai_title=None,
    )


def _make_detail(
    session_id: str = "sess-abcdefgh",
    runtime: str = "claude",
    cumulative_cost_usd: float | None = 0.006500,
    cost_known: bool = False,
) -> SessionDetail:
    return SessionDetail(
        session_id=session_id,
        runtime=runtime,
        project="alpha",
        cwd="/workspace",
        model="claude-sonnet-4-6",
        started_at=_NOW_ISO,
        last_activity_at=_NOW_ISO,
        message_count=3,
        context_size_tokens=1200,
        cumulative_cost_usd=cumulative_cost_usd,
        cost_known=cost_known,
        status="ended",
        agent_name="software-engineer",
        ai_title=None,
        event_timestamps=(_NOW_ISO,),
    )


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


def test_claude_adapter_satisfies_protocol() -> None:
    """ClaudeRuntimeAdapter must satisfy the RuntimeAdapter protocol."""
    adapter = ClaudeRuntimeAdapter()
    assert isinstance(adapter, RuntimeAdapter)


def test_codex_adapter_satisfies_protocol() -> None:
    """CodexRuntimeAdapter must satisfy the RuntimeAdapter protocol."""
    adapter = CodexRuntimeAdapter()
    assert isinstance(adapter, RuntimeAdapter)


# ---------------------------------------------------------------------------
# ClaudeRuntimeAdapter.enrich_row
# ---------------------------------------------------------------------------


def test_claude_enrich_row_sets_cost_known_true_when_cost_present() -> None:
    """enrich_row sets cost_known=True when cumulative_cost_usd is not None."""
    adapter = ClaudeRuntimeAdapter()
    row = _make_row(cumulative_cost_usd=0.0065, cost_known=False)

    enriched = adapter.enrich_row(row)

    assert enriched.cost_known is True
    assert enriched.cumulative_cost_usd == pytest.approx(0.0065)


def test_claude_enrich_row_preserves_dollar_conversion() -> None:
    """The dollar value on the enriched row equals the input value."""
    adapter = ClaudeRuntimeAdapter()
    # Simulate: aggregator computed 6500 micro-USD → 0.0065 USD
    row = _make_row(cumulative_cost_usd=6500 / 1_000_000, cost_known=False)

    enriched = adapter.enrich_row(row)

    assert enriched.cumulative_cost_usd == pytest.approx(6500 / 1_000_000)
    assert enriched.cost_known is True


def test_claude_enrich_row_cost_none_leaves_cost_known_false() -> None:
    """enrich_row with cumulative_cost_usd=None leaves cost_known=False (unknown model)."""
    adapter = ClaudeRuntimeAdapter()
    row = _make_row(cumulative_cost_usd=None, cost_known=False)

    enriched = adapter.enrich_row(row)

    assert enriched.cumulative_cost_usd is None
    assert enriched.cost_known is False


def test_claude_enrich_row_compute_cost_not_called() -> None:
    """pricing.compute_cost must NOT be called by enrich_row.

    The aggregator already summed event-level micro-USD before calling the adapter.
    The adapter does not recompute from scratch.
    """
    adapter = ClaudeRuntimeAdapter()
    row = _make_row(cumulative_cost_usd=0.0065, cost_known=False)

    with patch(
        "dadaia_workspace.features.telemetry.pricing.compute_cost"
    ) as mock_compute:
        adapter.enrich_row(row)
        mock_compute.assert_not_called()


def test_claude_enrich_row_returns_new_frozen_instance() -> None:
    """enrich_row returns a new SessionRow (frozen dataclass immutability)."""
    adapter = ClaudeRuntimeAdapter()
    row = _make_row(cumulative_cost_usd=0.0065, cost_known=False)

    enriched = adapter.enrich_row(row)

    assert enriched is not row
    assert isinstance(enriched, SessionRow)


# ---------------------------------------------------------------------------
# ClaudeRuntimeAdapter.enrich_detail
# ---------------------------------------------------------------------------


def test_claude_enrich_detail_sets_cost_known_true() -> None:
    """enrich_detail sets cost_known=True when cumulative_cost_usd is not None."""
    adapter = ClaudeRuntimeAdapter()
    detail = _make_detail(cumulative_cost_usd=0.0065, cost_known=False)

    enriched = adapter.enrich_detail(detail)

    assert enriched.cost_known is True
    assert isinstance(enriched, SessionDetail)


# ---------------------------------------------------------------------------
# CodexRuntimeAdapter.enrich_row
# ---------------------------------------------------------------------------


def test_codex_enrich_row_sets_cost_none_and_known_false() -> None:
    """CodexRuntimeAdapter.enrich_row always yields cumulative_cost_usd=None, cost_known=False."""
    adapter = CodexRuntimeAdapter()
    # Even if the aggregator somehow puts a cost on a codex row, the adapter clears it.
    row = _make_row(runtime="codex", cumulative_cost_usd=99.99, cost_known=True)

    enriched = adapter.enrich_row(row)

    assert enriched.cumulative_cost_usd is None
    assert enriched.cost_known is False


def test_codex_enrich_row_compute_cost_not_called() -> None:
    """pricing.compute_cost must NOT be called by CodexRuntimeAdapter.enrich_row."""
    adapter = CodexRuntimeAdapter()
    row = _make_row(runtime="codex", cumulative_cost_usd=None, cost_known=False)

    with patch(
        "dadaia_workspace.features.telemetry.pricing.compute_cost"
    ) as mock_compute:
        adapter.enrich_row(row)
        mock_compute.assert_not_called()


def test_codex_enrich_row_preserves_non_cost_fields() -> None:
    """CodexRuntimeAdapter.enrich_row preserves all non-cost fields."""
    adapter = CodexRuntimeAdapter()
    row = _make_row(
        session_id="codex-sess-xyz",
        runtime="codex",
        cumulative_cost_usd=None,
        cost_known=False,
    )

    enriched = adapter.enrich_row(row)

    assert enriched.session_id == row.session_id
    assert enriched.runtime == row.runtime
    assert enriched.project == row.project
    assert enriched.model == row.model
    assert enriched.message_count == row.message_count
    assert enriched.context_size_tokens == row.context_size_tokens
    assert enriched.status == row.status
    assert enriched.agent_name == row.agent_name


def test_codex_enrich_row_returns_new_frozen_instance() -> None:
    """enrich_row returns a new SessionRow."""
    adapter = CodexRuntimeAdapter()
    row = _make_row(runtime="codex", cumulative_cost_usd=None, cost_known=False)

    enriched = adapter.enrich_row(row)

    assert enriched is not row
    assert isinstance(enriched, SessionRow)


# ---------------------------------------------------------------------------
# CodexRuntimeAdapter.enrich_detail
# ---------------------------------------------------------------------------


def test_codex_enrich_detail_sets_cost_none_and_known_false() -> None:
    """CodexRuntimeAdapter.enrich_detail yields cumulative_cost_usd=None, cost_known=False."""
    adapter = CodexRuntimeAdapter()
    detail = _make_detail(runtime="codex", cumulative_cost_usd=5.0, cost_known=True)

    enriched = adapter.enrich_detail(detail)

    assert enriched.cumulative_cost_usd is None
    assert enriched.cost_known is False
    assert isinstance(enriched, SessionDetail)


# ---------------------------------------------------------------------------
# ClaudeRuntimeAdapter.liveness — filesystem fake via tmp_path
# ---------------------------------------------------------------------------


def test_claude_liveness_absent_file_returns_ended(tmp_path: pathlib.Path) -> None:
    """liveness returns 'ended' when ~/.claude/sessions/<id>.json does not exist."""
    adapter = ClaudeRuntimeAdapter()
    # Patch home() to point to tmp_path so we don't read real fs.
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness("nonexistent-session", "/workspace")
    assert result == "ended"


def test_claude_liveness_recent_mtime_returns_active(tmp_path: pathlib.Path) -> None:
    """liveness returns 'active' when session file mtime is within 5 minutes."""
    sessions_dir = tmp_path / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True)
    session_file = sessions_dir / "active-session.json"
    session_file.write_text("{}")

    # mtime is "now" by default for a newly created file — within 5 min.
    adapter = ClaudeRuntimeAdapter()
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness("active-session", "/workspace")

    assert result == "active"


def test_claude_liveness_old_mtime_returns_ended(tmp_path: pathlib.Path) -> None:
    """liveness returns 'ended' when session file mtime is older than 60 minutes."""
    sessions_dir = tmp_path / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True)
    session_file = sessions_dir / "old-session.json"
    session_file.write_text("{}")

    # Set mtime to 90 minutes ago.
    old_ts = (datetime.now(tz=UTC) - timedelta(minutes=90)).timestamp()
    import os
    os.utime(session_file, (old_ts, old_ts))

    adapter = ClaudeRuntimeAdapter()
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness("old-session", "/workspace")

    assert result == "ended"


def test_claude_liveness_idle_mtime_returns_idle(tmp_path: pathlib.Path) -> None:
    """liveness returns 'idle' when session file mtime is 6-60 minutes ago."""
    sessions_dir = tmp_path / ".claude" / "sessions"
    sessions_dir.mkdir(parents=True)
    session_file = sessions_dir / "idle-session.json"
    session_file.write_text("{}")

    # Set mtime to 30 minutes ago (> 5 min, <= 60 min → idle).
    idle_ts = (datetime.now(tz=UTC) - timedelta(minutes=30)).timestamp()
    import os
    os.utime(session_file, (idle_ts, idle_ts))

    adapter = ClaudeRuntimeAdapter()
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness("idle-session", "/workspace")

    assert result == "idle"


# ---------------------------------------------------------------------------
# CodexRuntimeAdapter.liveness — Phase A stub
# ---------------------------------------------------------------------------


def test_codex_liveness_returns_idle_stub() -> None:
    """CodexRuntimeAdapter.liveness returns 'idle' in Phase A (stub)."""
    adapter = CodexRuntimeAdapter()
    result = adapter.liveness("any-session", "/workspace")
    assert result == "idle"
