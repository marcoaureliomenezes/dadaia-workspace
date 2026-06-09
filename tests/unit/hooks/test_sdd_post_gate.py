"""Unit + parity tests for dadaia_workspace.hooks.sdd_post_gate.

Mandatory parity:
  (a) atomic renewal via os.replace;
  (b) [A-Za-z0-9_-] session-id strip (CWE-22);
  (c) fail-open: any non-LockHeldError condition -> ALLOW/no-op (PROTECTED is the sole
      fail-closed path, and it lives in the PreToolUse gate, never here).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from dadaia_workspace.hooks import sdd_post_gate


def _ws_with_session(tmp_path: Path, sess_id: str) -> Path:
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True)
    (tmp_path / ".dadaia" / "states").mkdir(parents=True)
    (sessions / f"{sess_id}.json").write_text(
        json.dumps(
            {
                "context": "ctx",
                "release": "rel-1",
                "runtime": "claude",
                "pid": 42,
                "last_seen_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_no_session_id_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("DADAIA_SESSION_ID", raising=False)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    assert sdd_post_gate.main() == 0


def test_missing_session_file_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / ".dadaia" / "sessions").mkdir(parents=True)
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "ghost")
    assert sdd_post_gate.main() == 0


def test_heartbeat_renews_and_appends(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    ws = _ws_with_session(tmp_path, "live-1")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_SESSION_ID", "live-1")
    assert sdd_post_gate.main() == 0

    data = json.loads((ws / ".dadaia" / "sessions" / "live-1.json").read_text(encoding="utf-8"))
    assert data["last_seen_at"] != "2026-01-01T00:00:00+00:00"

    events = (ws / ".dadaia" / "logs" / "lock-events.jsonl").read_text(encoding="utf-8")
    record = json.loads(events.strip().splitlines()[-1])
    assert record["event"] == "HEARTBEAT"
    assert record["session_id"] == "live-1"
    assert record["context"] == "ctx"


def test_atomic_renewal_uses_os_replace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # PARITY (a): session-file renewal must go through os.replace (atomic on Windows too).
    ws = _ws_with_session(tmp_path, "repl-1")
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_SESSION_ID", "repl-1")

    calls: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src: object, dst: object) -> None:
        calls.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", spy)
    assert sdd_post_gate.main() == 0
    assert len(calls) == 1
    # No leftover temp files.
    assert list((ws / ".dadaia" / "sessions").glob("*.tmp")) == []


def test_session_id_strip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # PARITY (b): a traversal-laden DADAIA_SESSION_ID is stripped to [A-Za-z0-9_-], so the
    # resolved session file stays inside .dadaia/sessions/. We create the file under the
    # sanitized name and confirm it is the one renewed.
    sanitized = "etcpasswd"
    ws = _ws_with_session(tmp_path, sanitized)
    monkeypatch.setenv("WORKSPACE_ROOT", str(ws))
    monkeypatch.setenv("DADAIA_SESSION_ID", "../../etc/passwd")
    assert sdd_post_gate.main() == 0
    record = json.loads(
        (ws / ".dadaia" / "logs" / "lock-events.jsonl").read_text(encoding="utf-8").strip()
    )
    assert record["session_id"] == sanitized


def test_corrupt_session_file_fails_open(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # PARITY (c): a corrupt session JSON -> no-op (fail-open), never a crash/block.
    sessions = tmp_path / ".dadaia" / "sessions"
    sessions.mkdir(parents=True)
    (sessions / "bad.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("DADAIA_SESSION_ID", "bad")
    assert sdd_post_gate.main() == 0
