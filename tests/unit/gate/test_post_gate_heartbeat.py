"""Unit tests for sdd-post-gate.sh heartbeat renewal.

The PostToolUse gate renews the session file's ``last_seen_at`` field. The
per-context semaphore was retired in v0.1.6 (the single TTL lease at
``.dadaia/states/ctx_locks/<ctx>.lock.json`` is renewed by the PreToolUse gate's
``lease.acquire`` RENEWED branch), so the post-gate has no semaphore to renew.
These tests assert only the live behavior: session renewal, and graceful no-op
when there is nothing else to touch.
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
# AC-1: post-gate renews session file last_seen_at
# ---------------------------------------------------------------------------


def test_post_gate_renews_session_last_seen_at(workspace: Path) -> None:
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
# AC-2: the per-context semaphore is retired — the post-gate touches no
# semaphore store, and renews the session regardless of any lock state.
# ---------------------------------------------------------------------------


def test_post_gate_renews_session_with_no_semaphore_store(workspace: Path) -> None:
    """The semaphore store no longer exists; the post-gate still renews the
    session file and never errors looking for a semaphore."""
    _install_scripts(workspace)
    sess_id = "sess_hb05"
    old_ts = _stale_ts(60)
    sess_file = _make_session_file(workspace, sess_id, last_seen_at=old_ts)

    result = _run_post_gate(workspace, session_id=sess_id)
    assert result.returncode == 0

    sess_data = json.loads(sess_file.read_text())
    assert sess_data["last_seen_at"] != old_ts

    # No semaphore store is created or expected anywhere.
    sem_dir = workspace / ".dadaia" / "states" / "ctx_locks"
    assert not list(sem_dir.glob("*.semaphore.json")) if sem_dir.exists() else True
