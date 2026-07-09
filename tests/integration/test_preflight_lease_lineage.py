"""v0.1.72 FR2 — the preflight lease probe honors process lineage (bug
``rebind-does-not-adopt-same-process-lease``).

``build_lifecycle_preflight_input`` used a FORKED identity check (record sid !=
incumbent sid ⇒ foreign) that contradicted acquire's rung-1 ``.ptr`` canon: on the
reporter's remote the lock named an old harness identity whose pid was the live harness
process — OUR OWN lineage — and preflight reported ``live_foreign_holder=True`` forever.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace import container

_CTX = "lineage-ctx"
_RELEASE = "v0.2.0"


def _workspace(tmp_path: Path) -> Path:
    states = tmp_path / ".dadaia" / "states"
    states.mkdir(parents=True)
    (states / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (tmp_path / "repos").mkdir()
    return tmp_path


def _write_lock(ws: Path, *, session_id: str, pid: int) -> None:
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / f"{_CTX}.lock.json").write_text(
        json.dumps(
            {
                "context": _CTX,
                "release": _RELEASE,
                "session_id": session_id,
                "mode": "BOUND_IMPLEMENTATION",
                "pid": pid,
                "acquired_at": datetime.now(tz=UTC).isoformat(),
                "heartbeat": datetime.now(tz=UTC).isoformat(),  # FRESH — is_held True
                "ttl": 120,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _write_incumbent(ws: Path, session_id: str) -> None:
    runtime = ws / ".dadaia" / "sessions" / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    (runtime / f"{_CTX}.ptr").write_text(session_id, encoding="utf-8")


def test_own_lineage_holder_is_not_foreign(tmp_path: Path) -> None:
    """Lock pid == our OWN pid (trivially in our ancestry chain), old sid, fresh
    heartbeat — the reporter's topology. Must NOT be a live foreign holder."""
    ws = _workspace(tmp_path)
    _write_lock(ws, session_id="019f-old-harness-identity", pid=os.getpid())
    _write_incumbent(ws, "sess_current")

    data = container.build_lifecycle_preflight_input(ws, context=_CTX, release_id=_RELEASE)

    assert data.lease.live_foreign_holder is False, data.lease


def test_live_non_lineage_holder_stays_foreign(tmp_path: Path) -> None:
    """A record held by an ALIVE process OUTSIDE our lineage is a genuine live foreign
    holder — the multi-session protection keeps its teeth.

    The live non-ancestor process is a child python sleeper (cross-platform): a CHILD is
    never in this process's ANCESTRY chain, so lineage discrimination correctly reports
    it foreign while the pid probe sees it alive.
    """
    import sys

    ws = _workspace(tmp_path)
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        _write_lock(ws, session_id="another-sessions-lease", pid=proc.pid)
        _write_incumbent(ws, "sess_current")

        data = container.build_lifecycle_preflight_input(ws, context=_CTX, release_id=_RELEASE)

        assert data.lease.live_foreign_holder is True, data.lease
    finally:
        proc.kill()
        proc.wait()
