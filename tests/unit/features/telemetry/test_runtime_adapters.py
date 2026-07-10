"""Unit tests for ClaudeRuntimeAdapter and CodexRuntimeAdapter.

Tests verify:
- ClaudeRuntimeAdapter.enrich_row: sets cumulative_cost_usd and cost_known=True
  when cost is present; pricing.compute_cost is NOT called (cost is computed by
  the aggregator from event-level micro-USD; the adapter only validates it).
- CodexRuntimeAdapter.enrich_row: sets cumulative_cost_usd=None, cost_known=False;
  pricing.compute_cost is NOT called.
- Liveness classification for ClaudeRuntimeAdapter (with filesystem fakes) and for
  CodexRuntimeAdapter (state_5.sqlite + history.jsonl fakes, incl. graceful
  degradation on missing/malformed/unknown-session input).
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import tempfile
import time as _time
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from dadaia_workspace.features.telemetry.aggregator.models import (
    SessionDetail,
    SessionRow,
)
from dadaia_workspace.features.telemetry.aggregator.runtimes import (
    ClaudeRuntimeAdapter,
    CodexRuntimeAdapter,
)

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
# Kept: read-path purity — claude enrich never recomputes cost from scratch.
# ---------------------------------------------------------------------------


def test_claude_enrich_row_and_detail_never_call_compute_cost() -> None:
    """pricing.compute_cost must NOT be called by enrich_row/enrich_detail.

    The aggregator already summed event-level micro-USD before calling the adapter;
    the adapter only validates/relabels it (read-path purity)."""
    adapter = ClaudeRuntimeAdapter()
    row = _make_row(cumulative_cost_usd=0.0065, cost_known=False)
    detail = _make_detail(cumulative_cost_usd=0.0065, cost_known=False)

    with patch("dadaia_workspace.features.telemetry.pricing.compute_cost") as mock_compute:
        enriched_row = adapter.enrich_row(row)
        enriched_detail = adapter.enrich_detail(detail)
        mock_compute.assert_not_called()

    assert enriched_row.cost_known is True
    assert enriched_row.cumulative_cost_usd == pytest.approx(0.0065)
    assert enriched_detail.cost_known is True


# ---------------------------------------------------------------------------
# Enrich row/detail per runtime — claude value-vs-none, codex always-none — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("runtime", "cumulative_cost_usd", "cost_known", "expect_cost", "expect_known"),
    [
        pytest.param(
            "claude", 0.0065, False, pytest.approx(0.0065), True, id="claude-cost-present"
        ),
        pytest.param("claude", None, False, None, False, id="claude-cost-none-unknown-model"),
        pytest.param("codex", 99.99, True, None, False, id="codex-always-clears-cost"),
        pytest.param("codex", None, False, None, False, id="codex-none-stays-none"),
    ],
)
def test_enrich_row_and_detail_matrix(
    runtime: str,
    cumulative_cost_usd: float | None,
    cost_known: bool,
    expect_cost: object,
    expect_known: bool,
) -> None:
    adapter = ClaudeRuntimeAdapter() if runtime == "claude" else CodexRuntimeAdapter()
    row = _make_row(runtime=runtime, cumulative_cost_usd=cumulative_cost_usd, cost_known=cost_known)
    detail = _make_detail(
        runtime=runtime, cumulative_cost_usd=cumulative_cost_usd, cost_known=cost_known
    )

    enriched_row = adapter.enrich_row(row)
    enriched_detail = adapter.enrich_detail(detail)

    assert enriched_row.cumulative_cost_usd == expect_cost
    assert enriched_row.cost_known is expect_known
    assert enriched_detail.cumulative_cost_usd == expect_cost
    assert enriched_detail.cost_known is expect_known
    # returns a SessionRow with non-cost fields preserved.
    assert isinstance(enriched_row, SessionRow)
    assert enriched_row.session_id == row.session_id
    assert enriched_row.project == row.project
    assert enriched_row.model == row.model


# ---------------------------------------------------------------------------
# ClaudeRuntimeAdapter.liveness thresholds — 1 param
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("session_id", "age_minutes", "file_exists", "expected"),
    [
        pytest.param("nonexistent-session", None, False, "ended", id="absent-file-ended"),
        pytest.param("active-session", 0, True, "active", id="recent-mtime-active"),
        pytest.param("idle-session", 30, True, "idle", id="idle-mtime-6-to-60min"),
        pytest.param("old-session", 90, True, "ended", id="old-mtime-over-60min-ended"),
    ],
)
def test_claude_liveness_thresholds(
    tmp_path: pathlib.Path,
    session_id: str,
    age_minutes: int | None,
    file_exists: bool,
    expected: str,
) -> None:
    adapter = ClaudeRuntimeAdapter()
    if file_exists:
        sessions_dir = tmp_path / ".claude" / "sessions"
        sessions_dir.mkdir(parents=True)
        session_file = sessions_dir / f"{session_id}.json"
        session_file.write_text("{}")
        if age_minutes:
            ts = (datetime.now(tz=UTC) - timedelta(minutes=age_minutes)).timestamp()
            os.utime(session_file, (ts, ts))

    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness(session_id, "/workspace")
    assert result == expected


# ---------------------------------------------------------------------------
# CodexRuntimeAdapter.liveness — state_5.sqlite + history.jsonl fakes — 1 param
# ---------------------------------------------------------------------------


def _make_codex_home(
    tmp: pathlib.Path,
    session_id: str,
    *,
    updated_at_offset_seconds: int = 0,
    archived: int = 0,
    history_ts_offset_seconds: int | None = None,
) -> pathlib.Path:
    """Build a fake ~/.codex/ directory under *tmp* with state_5.sqlite + history.jsonl."""
    codex_dir = tmp / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)

    now_unix = int(_time.time())
    updated_at = now_unix + updated_at_offset_seconds

    db_path = codex_dir / "state_5.sqlite"
    con = sqlite3.connect(str(db_path))
    con.execute(
        """CREATE TABLE threads (
            id TEXT PRIMARY KEY,
            rollout_path TEXT NOT NULL DEFAULT '',
            created_at INTEGER NOT NULL DEFAULT 0,
            updated_at INTEGER NOT NULL DEFAULT 0,
            source TEXT NOT NULL DEFAULT '',
            model_provider TEXT NOT NULL DEFAULT '',
            cwd TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL DEFAULT '',
            sandbox_policy TEXT NOT NULL DEFAULT '',
            approval_mode TEXT NOT NULL DEFAULT '',
            tokens_used INTEGER NOT NULL DEFAULT 0,
            has_user_event INTEGER NOT NULL DEFAULT 0,
            archived INTEGER NOT NULL DEFAULT 0,
            archived_at INTEGER
        )"""
    )
    con.execute(
        "INSERT INTO threads (id, updated_at, archived) VALUES (?, ?, ?)",
        (session_id, updated_at, archived),
    )
    con.commit()
    con.close()

    history_path = codex_dir / "history.jsonl"
    lines: list[str] = []
    if history_ts_offset_seconds is not None:
        ts = now_unix + history_ts_offset_seconds
        lines.append(json.dumps({"session_id": session_id, "ts": ts, "text": "hello"}))
    history_path.write_text("\n".join(lines) + ("\n" if lines else ""))

    return tmp


@pytest.mark.parametrize(
    ("case", "session_id", "kwargs", "query_id", "expected"),
    [
        pytest.param(
            "archived-ended-regardless-of-delta",
            "sess-archived",
            {"updated_at_offset_seconds": 0, "archived": 1},
            "sess-archived",
            "ended",
            id="archived-returns-ended",
        ),
        pytest.param(
            "fresh-delta-active",
            "sess-active",
            {"updated_at_offset_seconds": -1, "archived": 0},
            "sess-active",
            "active",
            id="fresh-delta-1s-active",
        ),
        pytest.param(
            "history-ts-wins-if-more-recent",
            "sess-hist-wins",
            {
                "updated_at_offset_seconds": -3600,
                "archived": 0,
                "history_ts_offset_seconds": -30,
            },
            "sess-hist-wins",
            "active",
            id="history-ts-wins-max-of-both",
        ),
        pytest.param(
            "30min-delta-idle",
            "sess-idle",
            {"updated_at_offset_seconds": -(30 * 60), "archived": 0},
            "sess-idle",
            "idle",
            id="30min-delta-idle",
        ),
        pytest.param(
            "90min-delta-ended",
            "sess-ended",
            {"updated_at_offset_seconds": -(90 * 60), "archived": 0},
            "sess-ended",
            "ended",
            id="90min-delta-ended",
        ),
        pytest.param(
            "unknown-session-idle",
            "known-session",
            {"updated_at_offset_seconds": -30, "archived": 0},
            "completely-unknown-id",
            "idle",
            id="unknown-session-not-in-db-idle",
        ),
    ],
)
def test_codex_liveness_matrix(
    tmp_path: pathlib.Path,
    case: str,
    session_id: str,
    kwargs: dict[str, int | None],
    query_id: str,
    expected: str,
) -> None:
    _make_codex_home(tmp_path, session_id, **kwargs)  # type: ignore[arg-type]
    adapter = CodexRuntimeAdapter()
    with patch("pathlib.Path.home", return_value=tmp_path):
        result = adapter.liveness(query_id, "/workspace")
    assert result == expected

    if case != "unknown-session-idle":
        return

    # Graceful degradation, folded onto the last matrix case: no ~/.codex at all ->
    # idle; malformed history.jsonl lines are skipped without raising (the
    # threads.updated_at value still drives the verdict).
    with (
        tempfile.TemporaryDirectory() as empty_home,
        patch("pathlib.Path.home", return_value=pathlib.Path(empty_home)),
    ):
        no_home_result = adapter.liveness("any-session", "/workspace")
    assert no_home_result == "idle"

    with tempfile.TemporaryDirectory() as home:
        home_path = pathlib.Path(home)
        codex_dir = home_path / ".codex"
        codex_dir.mkdir(parents=True)
        now_unix = int(_time.time())
        db_path = codex_dir / "state_5.sqlite"
        con = sqlite3.connect(str(db_path))
        con.execute(
            """CREATE TABLE threads (
                id TEXT PRIMARY KEY,
                updated_at INTEGER NOT NULL DEFAULT 0,
                archived INTEGER NOT NULL DEFAULT 0
            )"""
        )
        con.execute(
            "INSERT INTO threads (id, updated_at, archived) VALUES (?, ?, ?)",
            ("sess-parse-fail", now_unix - 10, 0),
        )
        con.commit()
        con.close()
        (codex_dir / "history.jsonl").write_text("not-valid-json\n{bad json\n")

        with patch("pathlib.Path.home", return_value=home_path):
            malformed_result = adapter.liveness("sess-parse-fail", "/workspace")
        assert malformed_result in ("active", "idle")
