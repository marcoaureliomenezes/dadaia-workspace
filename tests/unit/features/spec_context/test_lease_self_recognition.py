"""Lease acquire self-recognition (v0.1.50 FR1 — audit F-1 rotated-sid self-block).

A holder whose recorded harness pid IS the acquiring session's own live pid — AND
whose replaced sid carries LINEAGE EVIDENCE (a CLI session record with the same
pid, written by `dadaia context bind`) — must RENEW (third identity rung), never
`LockHeldError` itself out of its own lease when the session id rotated.

Bare pid equality is NOT enough: fixtures and eval flows legitimately model
foreign holders with the current process pid and no session record; those keep
blocking (the frozen TOCTOU/no-steal contracts).

CRITICAL no-steal: foreign-live-pid remains a named blocked row.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from dadaia_workspace.core.exceptions import LockHeldError
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


def test_rotated_sid_same_pid_with_lineage_renews_and_reindexes(tmp_path: Path) -> None:
    """Same live harness pid + rotated sid + session-record lineage ⇒ RENEW (F-1),
    leaving no dangling by-session index entry for the replaced sid."""
    _seed_session_record(tmp_path, "sess_old", pid=_PID)
    status1, _ = _acquire(tmp_path, "sess_old")
    assert status1 == "ACQUIRED"

    status2, rec2 = _acquire(tmp_path, "sess_new")
    assert status2 == "RENEWED"
    assert rec2["session_id"] == "sess_new"
    assert rec2["pid"] == _PID

    index_dir = tmp_path / ".dadaia" / "states" / "ctx_locks" / "by-session"
    assert (index_dir / "sess_new.json").exists()
    assert not (index_dir / "sess_old.json").exists()


def _setup_no_session_record(ws: Path) -> None:
    _acquire(ws, "sess_a")  # no session record seeded


def _setup_mismatched_record_pid(ws: Path) -> None:
    _seed_session_record(ws, "sess_a", pid=9999)
    _acquire(ws, "sess_a")


def _setup_foreign_live_pid(ws: Path) -> None:
    _seed_session_record(ws, "sess_a", pid=1111)
    _acquire(ws, "sess_a", pid=1111)


@pytest.mark.parametrize(
    ("setup", "acquire_pid"),
    [
        pytest.param(
            _setup_no_session_record,
            2222,
            id="same-pid-no-session-record-still-blocked",
        ),
        pytest.param(
            _setup_mismatched_record_pid,
            2222,
            id="same-pid-mismatched-record-pid-still-blocked",
        ),
        pytest.param(
            _setup_foreign_live_pid,
            2222,
            id="foreign-live-pid-still-blocked",
        ),
    ],
)
def test_blocked_variants(tmp_path: Path, setup: Callable[[Path], None], acquire_pid: int) -> None:
    """No lineage evidence, mismatched record pid, or a genuinely different live pid —
    none of these are self-recognized; the frozen foreign-holder contract holds."""
    setup(tmp_path)
    with pytest.raises(LockHeldError):
        _acquire(tmp_path, "sess_b", pid=acquire_pid)
