"""Doctor cleanup for retired concurrency state and caller-owned sessions.

Re-classification note (T-011-04 / FR-W1-04, ADR-8 amended): SESSION-record (bind) GC TTL
semantics now measure against the heartbeat-renewed ``last_seen_at`` (with TTL-from-creation
fallback for pre-heartbeat records), resolved by ``session_identity.liveness_timestamp``;
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
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _make_doctor(ws: Path, store: FakeContextStore | None = None) -> DoctorService:
    if store is None:
        store = FakeContextStore()
    return DoctorService(
        context_store=store,
        git_client=FakeGitClient(),
        workspace_root=ws,
    )


def _stale_iso(ttl: int = 300, extra_seconds: int = 60) -> str:
    """Return an ISO timestamp TTL+extra_seconds in the past (guaranteed stale)."""
    dt = datetime.now(tz=UTC) - timedelta(seconds=ttl + extra_seconds)
    return dt.isoformat()


def _fresh_iso() -> str:
    """Return a current ISO timestamp (guaranteed fresh for default TTL=1800)."""
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Retired context-global state plus expired session record
# ---------------------------------------------------------------------------


def test_gc_deletion_matrix(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"
    ctx_locks_dir.mkdir(parents=True)
    sessions_dir = ws / ".dadaia" / "sessions"

    # Any pre-doctrine content is inert and removed as a directory.
    lock_file = ctx_locks_dir / "myctx.lock.json"
    stale_rec = {
        "context": "myctx",
        "release": "v0.1.6",
        "session_id": "old-sess",
        "mode": "BOUND_IMPLEMENTATION",
        "acquired_at": _stale_iso(ttl=1800),
        "heartbeat": _stale_iso(ttl=1800),
        "ttl": 1800,
    }
    lock_file.write_text(json.dumps(stale_rec, indent=2), encoding="utf-8")

    # (b) TTL-expired .dadaia/sessions/<id>.json → GRAVEYARD-GC.
    sess_file = sessions_dir / "old-sess-001.json"
    expired_sess = {
        "session_id": "old-sess-001",
        "context": "myctx",
        "mode": "BOUND_IMPLEMENTATION",
        "release": "v0.1.6",
        "runtime": "test",
        "last_seen_at": _stale_iso(ttl=300),
        "ttl_seconds": 300,
    }
    sess_file.write_text(json.dumps(expired_sess, indent=2), encoding="utf-8")

    # Additional legacy shapes do not receive individual semantics.
    sentinel = ctx_locks_dir / "myctx.lock.sentinel"
    sentinel.write_text("", encoding="utf-8")

    # (d) invalid JSON lock file → LOCK-NEW.
    bad_lock = ctx_locks_dir / "badctx.lock.json"
    bad_lock.write_text("NOT JSON {{{", encoding="utf-8")

    # (e) lock file missing required fields → LOCK-NEW.
    incomplete_lock = ctx_locks_dir / "incompletectx.lock.json"
    incomplete_rec = {"context": "incompletectx"}  # missing everything else
    incomplete_lock.write_text(json.dumps(incomplete_rec, indent=2), encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not lock_file.exists()
    assert not ctx_locks_dir.exists()
    assert any("RETIRED-LOCK-STATE" in a for a in actions), actions
    assert not sess_file.exists()
    assert any("GRAVEYARD-GC" in a and "old-sess-001.json" in a for a in actions), actions
    assert not sentinel.exists()
    assert not bad_lock.exists()
    assert not incomplete_lock.exists()


# ---------------------------------------------------------------------------
# Clean-exit + TTL-from-creation fallback
# ---------------------------------------------------------------------------


def test_no_stale_records_and_ttl_from_creation_fallback(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    sessions_dir = ws / ".dadaia" / "sessions"

    # A fresh caller-owned session survives.
    sess_file = sessions_dir / "live-sess.json"
    fresh_sess = {
        "session_id": "live-sess",
        "context": "freshctx",
        "mode": "BOUND_IMPLEMENTATION",
        "release": "v0.1.6",
        "runtime": "test",
        "last_seen_at": _fresh_iso(),
        "ttl_seconds": 1800,
    }
    sess_file.write_text(json.dumps(fresh_sess, indent=2), encoding="utf-8")
    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert sess_file.exists()
    gc_actions = [a for a in actions if "GC" in a]
    assert gc_actions == [], f"Expected no GC actions for fresh records, got: {gc_actions}"

    # TTL-from-creation fallback: a record WITHOUT last_seen_at uses bound_at for GC;
    # the session-record pid is NEVER consulted for bind GC.
    from dadaia_workspace.features.spec_context import session_identity

    stale_id = "sess_pre01"
    session_identity.write_session(
        ws,
        stale_id,
        {
            "session_id": stale_id,
            "context": "myctx",
            "mode": "READ",
            "pid": 4242,
            "bound_at": _stale_iso(ttl=300),
            "ttl_seconds": 300,
        },
    )
    fresh_id = "sess_pre02"
    session_identity.write_session(
        ws,
        fresh_id,
        {
            "session_id": fresh_id,
            "context": "myctx",
            "mode": "READ",
            "pid": 4242,
            "bound_at": _fresh_iso(),
            "ttl_seconds": 300,
        },
    )

    doctor2 = _make_doctor(ws)
    actions2 = doctor2.fix()

    assert not (ws / ".dadaia" / "sessions" / f"{stale_id}.json").exists(), (
        f"Pre-last_seen_at record stale by creation must be collected. Actions: {actions2}"
    )
    assert (ws / ".dadaia" / "sessions" / f"{fresh_id}.json").exists(), (
        f"Pre-last_seen_at record fresh by creation must be spared. Actions: {actions2}"
    )


# ---------------------------------------------------------------------------
# T-011-04 (FR-W1-04 / ADR-8 amended): heartbeat-renewed last_seen_at bind GC — CRITICAL
# ---------------------------------------------------------------------------


def _post_gate_heartbeat(ws: Path, sess_id: str) -> None:
    """Invoke the REAL PostToolUse heartbeat (refreshes last_seen_at) for ``sess_id``.

    No env-var leak: the harness session id is fed through the stdin payload, exactly as
    the production hook resolves it (resolve_session_id). This is the renewal path the
    operator's live sessions actually take — not a planted timestamp.
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
    saved_ws = os.environ.get("WORKSPACE_ROOT")
    old_stdin = sys.stdin
    sys.stdin = io.StringIO(json.dumps({"session_id": sess_id}))
    os.environ["WORKSPACE_ROOT"] = str(ws)
    try:
        assert sdd_post_gate.main() == 0
    finally:
        sys.stdin = old_stdin
        if saved_ws is None:
            os.environ.pop("WORKSPACE_ROOT", None)
        else:
            os.environ["WORKSPACE_ROOT"] = saved_ws
        for k, v in saved_env.items():
            if v is not None:
                os.environ[k] = v


def _write_read_bind(
    ws: Path, sess_id: str, *, last_seen_at: str, bound_at: str | None = None
) -> None:
    """Persist a READ-mode bind record via the session-identity owner (production writer)."""
    from dadaia_workspace.features.spec_context import session_identity

    record: dict[str, object] = {
        "session_id": sess_id,
        "context": "myctx",
        "mode": "READ",
        "release": None,
        "runtime": "test",
        "pid": 4242,
        "last_seen_at": last_seen_at,
        "ttl_seconds": 300,
        "is_stale": False,
    }
    if bound_at is not None:
        record["bound_at"] = bound_at
    session_identity.write_session(ws, sess_id, record)


def test_renewed_bind_survives_gc_and_gate_still_resolves_read(tmp_path: Path) -> None:
    """FR-W1-04: real heartbeat renewal ⇒ bind survives GC ⇒ gate resolves READ for the sid.

    No planted pid: we write a stale READ bind, run the PRODUCTION PostToolUse heartbeat
    to refresh its last_seen_at, then sweep — the renewed record must NOT be collected,
    and the gate's mode resolution must still see READ for that session.
    """
    from dadaia_workspace.hooks.sdd_gate import _resolve_mode

    ws = _make_workspace(tmp_path)
    sess_id = "sess_live01"
    # Stale by last_seen_at — would be collected if not renewed.
    _write_read_bind(ws, sess_id, last_seen_at=_stale_iso(ttl=300))

    # REAL renewal: the PostToolUse heartbeat refreshes last_seen_at.
    _post_gate_heartbeat(ws, sess_id)

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    sess_file = ws / ".dadaia" / "sessions" / f"{sess_id}.json"
    assert sess_file.exists(), (
        f"Renewed bind must survive GC (last_seen_at refreshed by heartbeat). Actions: {actions}"
    )
    assert not any("GRAVEYARD-GC" in a and sess_id in a for a in actions), (
        f"Renewed bind must NOT be graveyard-collected: {actions}"
    )
    # The gate still resolves READ for this sid via the session record.
    assert _resolve_mode(ws, sess_id, "myctx") == "READ"


def test_stale_unrenewed_bind_is_collected(tmp_path: Path) -> None:
    """FR-W1-04: a bind whose last_seen_at is past TTL with NO renewal is collected."""
    ws = _make_workspace(tmp_path)
    sess_id = "sess_dead01"
    _write_read_bind(ws, sess_id, last_seen_at=_stale_iso(ttl=300))
    # No heartbeat — the session is dead.

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    sess_file = ws / ".dadaia" / "sessions" / f"{sess_id}.json"
    assert not sess_file.exists(), (
        f"Stale unrenewed bind must be graveyard-collected. Actions: {actions}"
    )
    assert any("GRAVEYARD-GC" in a and sess_id in a for a in actions), (
        f"Expected GRAVEYARD-GC for the dead bind, got: {actions}"
    )
