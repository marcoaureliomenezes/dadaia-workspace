"""v0.2.9 follow-up — bind-epoch marker carries the session id (sid:<id>).

Bug family context-heartbeat-requires-env-after-persisted-bind /
context-bind-session-id-mismatch: after a default bind, the heartbeat and
``context show --json`` could not resolve the session without an exported
DADAIA_SESSION_ID (or resolved a divergent identity). The marker now records
``sid:<session_id>`` after the pid chain — old pid parsers skip it — and both
commands fall back to it via the W1-8 marker-only ancestry attribution.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import session_identity

pytestmark = pytest.mark.unit

_PID = 990011


def _ws(tmp_path: Path, slug: str = "ctx") -> Path:
    (tmp_path / ".dadaia" / "states" / "bind_epoch").mkdir(parents=True)
    (tmp_path / ".dadaia" / "states" / "spec_contexts.json").write_text(
        json.dumps(
            {
                "schema_version": "2",
                "contexts": [
                    {
                        "name": slug,
                        "repo_slug": slug,
                        "repo_url": "https://example.test/x.git",
                        "state": "alive",
                        "created_at": "2026-07-19T00:00:00Z",
                        "alive_since": "2026-07-19T00:00:00Z",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_marker_records_sid_after_the_pid_chain_and_stays_pid_parseable(
    tmp_path: Path,
) -> None:
    _ws(tmp_path)
    session_identity.write_bind_epoch(tmp_path, "ctx", pids=[_PID, _PID + 1], session_id="sess-abc")
    marker = tmp_path / ".dadaia" / "states" / "bind_epoch" / "ctx"
    lines = marker.read_text(encoding="utf-8").splitlines()
    assert lines == [str(_PID), str(_PID + 1), "sid:sess-abc"]
    # Back-compat: the pid reader ignores the non-integer sid line.
    assert session_identity.read_bind_epoch_pids(tmp_path, "ctx") == [_PID, _PID + 1]
    assert session_identity.read_bind_epoch_sid(tmp_path, "ctx") == "sess-abc"


def test_legacy_marker_without_sid_reads_none(tmp_path: Path) -> None:
    _ws(tmp_path)
    session_identity.write_bind_epoch(tmp_path, "ctx", pids=[_PID])
    assert session_identity.read_bind_epoch_sid(tmp_path, "ctx") is None
    # The empty-pids legacy path on a FRESH marker writes an empty file.
    session_identity.write_bind_epoch(tmp_path, "fresh", pids=[])
    assert (tmp_path / ".dadaia" / "states" / "bind_epoch" / "fresh").read_text() == ""
    assert session_identity.read_bind_epoch_sid(tmp_path, "fresh") is None


def test_heartbeat_falls_back_to_the_marker_sid(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The consumer repro: after a default bind, `context heartbeat` works with NO env."""
    _ws(tmp_path)
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "sess-abc.json").write_text(
        json.dumps({"session_id": "sess-abc", "context": "ctx", "mode": "read"}),
        encoding="utf-8",
    )
    session_identity.write_bind_epoch(
        tmp_path, "ctx", pids=[os.getpid(), os.getppid()], session_id="sess-abc"
    )
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    for var in ("CODEX_SESSION_ID", "CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)

    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    result = CliRunner().invoke(app, ["context", "heartbeat"])
    assert result.exit_code == 0, result.output
    assert "sess-abc" in result.output


def test_show_json_reports_the_marker_sid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The mismatch case: show --json reports the session the bind minted (sess_…),
    not a divergent/absent identity."""
    _ws(tmp_path)
    (tmp_path / "repos" / "ctx" / "specs").mkdir(parents=True)
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / "sess-abc.json").write_text(
        json.dumps(
            {
                "session_id": "sess-abc",
                "context": "ctx",
                "mode": "read",
                "last_seen_at": "2999-01-01T00:00:00+00:00",
                "ttl_seconds": 300,
            }
        ),
        encoding="utf-8",
    )
    session_identity.write_bind_epoch(
        tmp_path, "ctx", pids=[os.getpid(), os.getppid()], session_id="sess-abc"
    )
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
    monkeypatch.delenv("DADAIA_CONTEXT", raising=False)
    for var in ("CODEX_SESSION_ID", "CODEX_THREAD_ID", "CLAUDE_CODE_SESSION_ID"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)

    from typer.testing import CliRunner

    from dadaia_workspace.cli.main import app

    result = CliRunner().invoke(app, ["context", "show", "ctx", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["session"]["session_id"] == "sess-abc"
