"""``context show`` displays advisory presence (v0.1.76 T-4, FR7).

FR7: "``context show`` reads presence instead of lease/incumbent state" — the incumbent
pointer / bound-session display (FR4-era ``session`` field) stays: it answers "what is
MY session bound to". This is an ADDITIVE ``presence`` field answering a different
question — "who else is currently active on this context" — sourced from
``features/spec_context/presence.py`` (the ONLY concurrency-signal surface post-doctrine),
never from the retired lease/incumbent-authority machinery.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadaia_workspace.cli.main import app
from dadaia_workspace.features.spec_context import presence

_runner = CliRunner()
_CTX = "presence-ctx"


def _make_workspace(root: Path) -> Path:
    ws = root / "ws"
    states = ws / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": _CTX,
                        "state": "alive",
                        "repo_slug": _CTX,
                        "repo_url": "https://example.invalid/presence-ctx.git",
                        "created_at": "2026-07-01T00:00:00+00:00",
                        "alive_since": "2026-07-01T00:00:00+00:00",
                        "dead_since": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return ws


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "DADAIA_CONTEXT",
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        monkeypatch.delenv(var, raising=False)


def test_context_show_json_carries_empty_presence_list_when_nobody_active(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _make_workspace(tmp_path)
    monkeypatch.chdir(ws)

    result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["presence"] == []


def test_context_show_json_lists_live_presence_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ws = _make_workspace(tmp_path)
    presence.upsert(ws, _CTX, "sess-alice", runtime="claude", pid=111)
    presence.upsert(ws, _CTX, "sess-bob", runtime="codex", pid=222)

    monkeypatch.chdir(ws)
    result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)

    sids = {rec["session_id"] for rec in data["presence"]}
    assert sids == {"sess-alice", "sess-bob"}
    runtimes = {rec["session_id"]: rec["runtime"] for rec in data["presence"]}
    assert runtimes["sess-alice"] == "claude"
    assert runtimes["sess-bob"] == "codex"


def test_context_show_json_excludes_stale_presence_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json as _json
    from datetime import UTC, datetime, timedelta

    from dadaia_workspace.core import kernel_tunables

    ws = _make_workspace(tmp_path)
    stale_path = ws / ".dadaia" / "states" / "presence" / _CTX / "sess-stale.json"
    stale_path.parent.mkdir(parents=True, exist_ok=True)
    stale_ts = (
        datetime.now(tz=UTC) - timedelta(seconds=kernel_tunables.PRESENCE_TTL_SECONDS + 100)
    ).isoformat()
    stale_path.write_text(
        _json.dumps(
            {
                "session_id": "sess-stale",
                "runtime": "claude",
                "pid": 1,
                "started_at": stale_ts,
                "last_seen_at": stale_ts,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(ws)
    result = _runner.invoke(app, ["context", "show", _CTX, "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.stdout)
    assert data["presence"] == []
