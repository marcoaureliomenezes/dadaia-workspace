"""Doctor cleanup for retired concurrency state and caller-owned sessions.

Re-classification note (T-011-04 / FR-W1-04, ADR-8 amended): SESSION-record (bind) GC TTL
semantics measure against the heartbeat-renewed ``last_seen_at`` (``session_store.is_live``);
the bind-CLI pid is never consulted (dead by construction).

CRITICAL GC: renewed-bind survival prevents live-session collection — kept verbatim,
exercising the REAL PostToolUse renewal path (no planted-pid fixtures).
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
import os  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from dadaia_workspace.infrastructure.git_subprocess import GitSubprocessClient
from dadaia_workspace.infrastructure.json_context_store import JsonContextStore
from tests.fixtures.stores import context_store


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "spec_contexts.json").write_text("{}", encoding="utf-8")
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path, store: JsonContextStore | None = None) -> DoctorService:
    if store is None:
        store = context_store(ws / ".dadaia" / "states")
    return DoctorService(
        context_store=store,
        git_client=GitSubprocessClient(),
        workspace_root=ws,
    )


def _ago(seconds: float) -> str:
    return (datetime.now(tz=UTC) - timedelta(seconds=seconds)).isoformat()


def _stale() -> str:  # past a day: a dead session, never a paused one
    return _ago(86400 + 60)


def _bind(ws: Path, sid: str, last_seen_at: str) -> Path:
    """A READ bind record written by the production session-store writer."""
    from dadaia_workspace.core import session_store

    record = {"session_id": sid, "context": "myctx", "mode": "READ", "release": None, "runtime": "test",
              "pid": 4242, "last_seen_at": last_seen_at}  # fmt: skip
    session_store.write_session(ws, sid, record)
    return ws / ".dadaia" / "sessions" / f"{sid}.json"


def test_gc_deletion_matrix(tmp_path: Path) -> None:
    """Retired context-global state (every ctx_locks shape: stale, sentinel, invalid JSON, incomplete)
    goes as one directory (WS-states-slop); an expired session record goes by GRAVEYARD-GC."""
    ws = _make_workspace(tmp_path)
    locks = ws / ".dadaia" / "states" / "ctx_locks"
    locks.mkdir(parents=True)
    (locks / "myctx.lock.json").write_text(
        json.dumps({"context": "myctx", "heartbeat": _stale()}), encoding="utf-8"
    )
    (locks / "myctx.lock.sentinel").write_text("", encoding="utf-8")
    (locks / "badctx.lock.json").write_text("NOT JSON {{{", encoding="utf-8")
    (locks / "incompletectx.lock.json").write_text('{"context": "x"}', encoding="utf-8")
    expired = _bind(ws, "old-sess-001", _stale())

    actions = _make_doctor(ws).fix()

    assert not locks.exists() and not expired.exists()
    assert any("WS-states-slop" in a for a in actions), actions
    assert any("GRAVEYARD-GC" in a and "old-sess-001.json" in a for a in actions), actions


def _post_gate_heartbeat(ws: Path, sess_id: str) -> None:
    """Invoke the REAL PostToolUse heartbeat (refreshes last_seen_at) for ``sess_id``.

    The harness session id is the hook env's, exactly as the production hook resolves it
    (resolve_session_id, env only). This is the renewal path the operator's live sessions
    actually take — not a planted timestamp.
    """
    import io
    import sys

    from dadaia_workspace.hooks import sdd_post_gate

    override_vars = (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
        "CODEX_THREAD_ID",
    )
    saved_env = {k: os.environ.pop(k, None) for k in override_vars}
    os.environ["CLAUDE_CODE_SESSION_ID"] = sess_id
    saved_cwd = Path.cwd()
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"session_id": sess_id}))
    os.chdir(ws)
    try:
        assert sdd_post_gate.main() == 0
    finally:
        sys.stdin = old_stdin
        os.chdir(saved_cwd)
        os.environ.pop("CLAUDE_CODE_SESSION_ID")
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


@pytest.mark.parametrize(
    ("idle", "renew", "survives"),
    [
        pytest.param(360, False, True, id="bind-lost-silently-after-five-idle-minutes-idle-bind-survives"),
        pytest.param(None, True, True, id="FR-W1-04-heartbeat-renewed-bind-survives-and-resolves"),
        pytest.param(None, False, False, id="FR-W1-04-unrenewed-stale-bind-collected"),
    ],
)  # fmt: skip
def test_no_stale_records(tmp_path: Path, idle: int | None, renew: bool, survives: bool) -> None:
    """Intent: CONTRACT — T-011-04, bind-lost-silently-after-five-idle-minutes: another session's
    SessionStart lane collects a bind only past a dead session's TTL (a day), measured against
    ``last_seen_at`` renewed through the REAL PostToolUse path; idle minutes never unbind."""
    from dadaia_workspace.core.session_store import live_session

    ws = _make_workspace(tmp_path)
    sid = "sess_01"
    record = _bind(ws, sid, _stale() if idle is None else _ago(idle))
    if renew:
        # post-gate-runs-the-reaper-on-the-tool-hot-path: the heartbeat never reaps.
        expired = ws / ".dadaia" / "tmp" / "expired.txt"
        expired.parent.mkdir(parents=True, exist_ok=True)
        expired.touch()
        os.utime(expired, (0, 0))
        _post_gate_heartbeat(ws, sid)
        assert expired.exists(), "a tool call must never run the reaper"

    actions = _make_doctor(ws).expire()

    assert record.exists() is survives
    assert any("GRAVEYARD-GC" in a and sid in a for a in actions) is not survives
    assert (live_session(ws, sid) is not None) is survives
