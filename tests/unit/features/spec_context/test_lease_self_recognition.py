"""Lease acquire self-recognition (v0.1.50 FR1 — audit F-1 rotated-sid self-block).

A holder whose recorded harness pid IS the acquiring session's own live pid — AND
whose replaced sid carries LINEAGE EVIDENCE (a CLI session record with the same
pid, written by `dadaia context bind`) — must RENEW (third identity rung), never
`LockHeldError` itself out of its own lease when the session id rotated.

Bare pid equality is NOT enough: fixtures and eval flows legitimately model
foreign holders with the current process pid and no session record; those keep
blocking (the frozen TOCTOU/no-steal contracts).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease

pytestmark = pytest.mark.unit

_PID = 4242


def _alive(_pid: int) -> bool:
    return True


def _seed_session_record(workspace: Path, session_id: str, *, pid: int) -> None:
    """Write the CLI session record that `dadaia context bind` would have written."""
    sessions = workspace / ".dadaia" / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)
    (sessions / f"{session_id}.json").write_text(
        json.dumps({"context": "ctx", "mode": "implementation", "pid": pid}),
        encoding="utf-8",
    )


def _acquire(workspace: Path, session_id: str, *, pid: int = _PID) -> tuple[str, dict[str, object]]:
    return lease.acquire(
        workspace,
        "ctx",
        session_id,
        "v9.9.9",
        "implementation",
        pid_probe=_alive,
        pid=pid,
    )


def test_rotated_sid_same_pid_with_lineage_renews(tmp_path: Path) -> None:
    """Same live harness pid + rotated sid + session-record lineage ⇒ RENEW (F-1)."""
    _seed_session_record(tmp_path, "sess_old", pid=_PID)
    status1, _ = _acquire(tmp_path, "sess_old")
    assert status1 == "ACQUIRED"

    status2, rec2 = _acquire(tmp_path, "sess_new")
    assert status2 == "RENEWED"
    assert rec2["session_id"] == "sess_new"
    assert rec2["pid"] == _PID


def test_self_recognition_reindexes_the_new_sid(tmp_path: Path) -> None:
    """The self-recognition RENEW leaves no dangling by-session entry."""
    _seed_session_record(tmp_path, "sess_old", pid=_PID)
    _acquire(tmp_path, "sess_old")
    _acquire(tmp_path, "sess_new")

    index_dir = tmp_path / ".dadaia" / "states" / "ctx_locks" / "by-session"
    assert (index_dir / "sess_new.json").exists()
    assert not (index_dir / "sess_old.json").exists()


def test_same_pid_without_session_record_still_blocked(tmp_path: Path) -> None:
    """No lineage evidence ⇒ no self-recognition — the frozen foreign contract."""
    _acquire(tmp_path, "sess_a")  # no session record seeded

    with pytest.raises(lease.LockHeldError):
        _acquire(tmp_path, "sess_b")


def test_same_pid_with_mismatched_record_pid_still_blocked(tmp_path: Path) -> None:
    """A session record with a DIFFERENT pid is not lineage evidence."""
    _seed_session_record(tmp_path, "sess_a", pid=9999)
    _acquire(tmp_path, "sess_a")

    with pytest.raises(lease.LockHeldError):
        _acquire(tmp_path, "sess_b")


def test_foreign_live_pid_still_blocked(tmp_path: Path) -> None:
    """No-steal guard: a DIFFERENT live pid is never recognized as self."""
    _seed_session_record(tmp_path, "sess_a", pid=1111)
    status1, _ = _acquire(tmp_path, "sess_a", pid=1111)
    assert status1 == "ACQUIRED"

    with pytest.raises(lease.LockHeldError):
        _acquire(tmp_path, "sess_b", pid=2222)
