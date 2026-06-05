"""Unit tests for T-R1-03: sdd-post-gate.sh heartbeat renewal.

Bug C fix: sdd-post-gate.sh must renew BOTH:
  1. The session file's last_seen_at field
  2. The context lock (semaphore) heartbeat field at
     .dadaia/states/ctx_locks/<context>.semaphore.json

Tests verify both timestamps are updated when the post-gate fires.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

_PKG_SCRIPTS = Path(__file__).resolve().parents[3] / "dadaia_workspace" / "public" / "scripts"
POST_GATE = _PKG_SCRIPTS / "sdd-post-gate.sh"


def _install_scripts(workspace: Path) -> Path:
    target = workspace / ".dadaia" / "scripts"
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(POST_GATE, target / POST_GATE.name)
    (target / POST_GATE.name).chmod(0o755)
    return target


def _stale_ts(seconds_ago: int = 120) -> str:
    return (datetime.now(tz=UTC) - timedelta(seconds=seconds_ago)).isoformat()


def _make_session_file(
    workspace: Path,
    session_id: str,
    *,
    context: str = "my-proj",
    release: str = "v1",
    last_seen_at: str | None = None,
) -> Path:
    sessions_dir = workspace / ".dadaia" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    data = {
        "session_id": session_id,
        "context": context,
        "mode": "BOUND_IMPLEMENTATION",
        "release": release,
        "runtime": "claude-code",
        "pid": os.getpid(),
        "bound_at": now,
        "last_seen_at": last_seen_at or now,
        "ttl_seconds": 300,
    }
    session_file = sessions_dir / f"{session_id}.json"
    session_file.write_text(json.dumps(data, indent=2))
    return session_file


def _make_semaphore_file(
    workspace: Path,
    context: str,
    session_id: str,
    *,
    heartbeat: str | None = None,
) -> Path:
    """Write a context semaphore file."""
    sem_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    sem_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now(tz=UTC).isoformat()
    data = {
        "owner": session_id,
        "phase": "BOUND_IMPLEMENTATION",
        "release": "v1",
        "write_set": [],
        "acquired_at": now,
        "ttl": 300,
        "heartbeat": heartbeat or now,
    }
    sem_file = sem_dir / f"{context}.semaphore.json"
    sem_file.write_text(json.dumps(data, indent=2))
    return sem_file


def _run_post_gate(workspace: Path, *, session_id: str) -> subprocess.CompletedProcess:  # type: ignore[type-arg]
    script = workspace / ".dadaia" / "scripts" / "sdd-post-gate.sh"
    log_file = workspace / ".dadaia" / "sdd-post-gate-test.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "WORKSPACE_ROOT": str(workspace),
        "DADAIA_SESSION_ID": session_id,
        "SDD_GATE_LOG": str(log_file),
    }
    return subprocess.run(
        ["bash", str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )


@pytest.fixture()
def workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    return ws


# ---------------------------------------------------------------------------
# T-R1-03 AC-1: post-gate renews session file last_seen_at
# ---------------------------------------------------------------------------


def test_tr103_post_gate_renews_session_last_seen_at(workspace: Path) -> None:
    """AC-1: sdd-post-gate.sh renews the session file's last_seen_at field."""
    _install_scripts(workspace)
    sess_id = "sess_hb01"
    old_ts = _stale_ts(60)
    sess_file = _make_session_file(workspace, sess_id, last_seen_at=old_ts)

    before = datetime.now(tz=UTC)
    result = _run_post_gate(workspace, session_id=sess_id)
    after = datetime.now(tz=UTC)

    assert result.returncode == 0

    updated = json.loads(sess_file.read_text())
    new_last_seen = datetime.fromisoformat(updated["last_seen_at"])
    assert new_last_seen >= before
    assert new_last_seen <= after + timedelta(seconds=1)
    assert updated["last_seen_at"] != old_ts


# ---------------------------------------------------------------------------
# T-R1-03 AC-2: post-gate renews context semaphore heartbeat (Bug C fix)
# ---------------------------------------------------------------------------


def test_tr103_post_gate_renews_semaphore_heartbeat(workspace: Path) -> None:
    """AC-2 (Bug C): sdd-post-gate.sh renews the context semaphore heartbeat.

    This is the core Bug C fix: the post-gate must renew BOTH the session file
    AND the per-context semaphore heartbeat field.
    """
    _install_scripts(workspace)
    sess_id = "sess_hb02"
    context = "my-proj"
    old_ts = _stale_ts(60)

    sess_file = _make_session_file(workspace, sess_id, context=context, last_seen_at=old_ts)
    sem_file = _make_semaphore_file(workspace, context, sess_id, heartbeat=old_ts)

    before = datetime.now(tz=UTC)
    result = _run_post_gate(workspace, session_id=sess_id)
    after = datetime.now(tz=UTC)

    assert result.returncode == 0

    # Verify session file was renewed
    sess_updated = json.loads(sess_file.read_text())
    assert sess_updated["last_seen_at"] != old_ts, "Session file last_seen_at should be updated"

    # Verify semaphore heartbeat was renewed (Bug C fix)
    sem_updated = json.loads(sem_file.read_text())
    new_hb = datetime.fromisoformat(sem_updated["heartbeat"])
    assert new_hb >= before, f"Semaphore heartbeat ({new_hb}) should be >= before_run ({before})"
    assert new_hb <= after + timedelta(seconds=1)
    assert sem_updated["heartbeat"] != old_ts, "Semaphore heartbeat should be updated (Bug C fix)"


def test_tr103_post_gate_both_timestamps_updated(workspace: Path) -> None:
    """AC-2 (integrated): both session last_seen_at and semaphore heartbeat are updated."""
    _install_scripts(workspace)
    sess_id = "sess_hb03"
    context = "my-proj"
    old_ts = _stale_ts(90)

    sess_file = _make_session_file(workspace, sess_id, context=context, last_seen_at=old_ts)
    sem_file = _make_semaphore_file(workspace, context, sess_id, heartbeat=old_ts)

    result = _run_post_gate(workspace, session_id=sess_id)
    assert result.returncode == 0

    sess_data = json.loads(sess_file.read_text())
    sem_data = json.loads(sem_file.read_text())

    assert sess_data["last_seen_at"] != old_ts, "Session last_seen_at not updated"
    assert sem_data["heartbeat"] != old_ts, "Semaphore heartbeat not updated (Bug C)"


# ---------------------------------------------------------------------------
# T-R1-03 AC-3: post-gate is no-op when semaphore not owned by session
# ---------------------------------------------------------------------------


def test_tr103_post_gate_skips_semaphore_when_not_owner(workspace: Path) -> None:
    """AC-3: post-gate does not update semaphore when session is not the owner."""
    _install_scripts(workspace)
    sess_id = "sess_hb04"
    other_sess = "sess_other01"
    context = "my-proj"
    old_ts = _stale_ts(60)

    _make_session_file(workspace, sess_id, context=context, last_seen_at=old_ts)
    sem_file = _make_semaphore_file(workspace, context, other_sess, heartbeat=old_ts)

    result = _run_post_gate(workspace, session_id=sess_id)
    assert result.returncode == 0

    sem_data = json.loads(sem_file.read_text())
    # Semaphore should NOT be updated (owned by other_sess, not sess_id)
    assert sem_data["heartbeat"] == old_ts, (
        "Semaphore heartbeat should NOT be updated when session is not owner"
    )


# ---------------------------------------------------------------------------
# T-R1-03 AC-4: post-gate noop when semaphore absent (no error)
# ---------------------------------------------------------------------------


def test_tr103_post_gate_noop_when_semaphore_absent(workspace: Path) -> None:
    """AC-4: post-gate handles missing semaphore gracefully (no error)."""
    _install_scripts(workspace)
    sess_id = "sess_hb05"
    old_ts = _stale_ts(60)

    sess_file = _make_session_file(workspace, sess_id, last_seen_at=old_ts)
    # No semaphore file created

    result = _run_post_gate(workspace, session_id=sess_id)
    assert result.returncode == 0

    # Session file should still be renewed
    sess_data = json.loads(sess_file.read_text())
    assert sess_data["last_seen_at"] != old_ts
