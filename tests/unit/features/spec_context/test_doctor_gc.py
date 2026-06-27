"""Unit tests for DoctorService GC operations (T-016-06).

Acceptance criteria (SPEC §8 AC-08):
    - Stale ctx_locks/<ctx>.lock.json absent after doctor --fix.
    - TTL-expired .dadaia/sessions/<id>.json absent after doctor --fix.
    - Orphan ctx_locks/<ctx>.lock.sentinel (mtime > 30s) absent after doctor --fix.
    - No stale records: doctor --fix exits 0, nothing deleted.

Re-classification note (T-011-04 / FR-W1-04, ADR-8 amended): SESSION-record (bind) GC TTL
semantics now measure against the heartbeat-renewed ``last_seen_at`` (with TTL-from-creation
fallback for pre-heartbeat records), resolved by ``session_identity.liveness_timestamp``;
the bind-CLI pid is never consulted (dead by construction). The pre-existing graveyard-GC
fixtures here already used ``last_seen_at`` as the heartbeat key; the T-011-04 additions
below exercise the REAL renewal path (PostToolUse heartbeat) — no planted-pid fixtures.
"""

from __future__ import annotations

# Guard: skip this entire module on platforms where fcntl is not available (e.g. Windows).
import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
import os  # noqa: E402
import time  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
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
# T-016-06 AC-08a: stale ctx_locks/<ctx>.lock.json deleted by --fix
# ---------------------------------------------------------------------------


def test_stale_lock_json_deleted_after_fix(tmp_path: Path) -> None:
    """Stale ctx_locks/myctx.lock.json written to tmp workspace; doctor --fix deletes it."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

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
    assert lock_file.exists(), "Precondition: lock file must exist before fix"

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not lock_file.exists(), (
        f"Stale lock file should be deleted after doctor fix, but still exists. Actions: {actions}"
    )
    # Re-classification (T-011-02): a stale-but-valid record is reclaimed under LOCK-GC
    # (probe-aware) rather than LOCK-NEW; LOCK-NEW now covers only structural corruption.
    assert any("LOCK-GC" in a and "myctx.lock.json" in a for a in actions), (
        f"Expected LOCK-GC action for myctx.lock.json, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08b: TTL-expired session file deleted by --fix
# ---------------------------------------------------------------------------


def test_expired_session_file_deleted_after_fix(tmp_path: Path) -> None:
    """TTL-expired .dadaia/sessions/<id>.json deleted by doctor --fix (graveyard GC)."""
    ws = _make_workspace(tmp_path)
    sessions_dir = ws / ".dadaia" / "sessions"

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
    assert sess_file.exists(), "Precondition: session file must exist before fix"

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not sess_file.exists(), (
        f"Expired session file should be deleted after doctor fix, but still exists. "
        f"Actions: {actions}"
    )
    assert any("GRAVEYARD-GC" in a and "old-sess-001.json" in a for a in actions), (
        f"Expected GRAVEYARD-GC action for old-sess-001.json, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08c: orphan sentinel (mtime > 30s) deleted by --fix
# ---------------------------------------------------------------------------


def test_orphan_sentinel_deleted_after_fix(tmp_path: Path) -> None:
    """Orphan ctx_locks/<ctx>.lock.sentinel with mtime > 30s deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    sentinel = ctx_locks_dir / "myctx.lock.sentinel"
    sentinel.write_text("", encoding="utf-8")
    assert sentinel.exists()

    # Backdate mtime to 60 seconds ago to make it "orphaned"
    old_mtime = time.time() - 60.0
    os.utime(str(sentinel), (old_mtime, old_mtime))

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not sentinel.exists(), (
        f"Orphan sentinel should be deleted after doctor fix, but still exists. Actions: {actions}"
    )
    assert any("SENTINEL-GC" in a and "myctx.lock.sentinel" in a for a in actions), (
        f"Expected SENTINEL-GC action for myctx.lock.sentinel, got: {actions}"
    )


# ---------------------------------------------------------------------------
# T-016-06 AC-08d: no stale records → --fix exits 0, nothing deleted
# ---------------------------------------------------------------------------


def test_no_stale_records_fix_exits_clean(tmp_path: Path) -> None:
    """No stale records: doctor fix exits 0, no files deleted."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"
    sessions_dir = ws / ".dadaia" / "sessions"

    # Write a FRESH lock record (well within TTL)
    lock_file = ctx_locks_dir / "freshctx.lock.json"
    fresh_rec = {
        "context": "freshctx",
        "release": "v0.1.6",
        "session_id": "live-sess",
        "mode": "BOUND_IMPLEMENTATION",
        "acquired_at": _fresh_iso(),
        "heartbeat": _fresh_iso(),
        "ttl": 1800,
    }
    lock_file.write_text(json.dumps(fresh_rec, indent=2), encoding="utf-8")

    # Write a FRESH session file
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

    # Write a FRESH sentinel (mtime = now, age < 30s)
    sentinel = ctx_locks_dir / "freshctx.lock.sentinel"
    sentinel.write_text("", encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    # Nothing should be deleted
    assert lock_file.exists(), "Fresh lock file should NOT be deleted"
    assert sess_file.exists(), "Fresh session file should NOT be deleted"
    assert sentinel.exists(), "Fresh sentinel should NOT be deleted (age < 30s)"

    gc_actions = [a for a in actions if "GC" in a or "LOCK-NEW" in a]
    assert gc_actions == [], f"Expected no GC actions for fresh records, got: {gc_actions}"


# ---------------------------------------------------------------------------
# T-016-06: invalid/missing-fields lock file deleted by --fix
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# T-011-04 (FR-W1-04 / ADR-8 amended): heartbeat-renewed last_seen_at bind GC.
# Exercises the REAL renewal path — NO planted-pid fixtures. A PostToolUse hook
# invocation refreshes the bind record's last_seen_at; the GC sweep then spares it,
# and the gate still resolves READ for that sid.
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

    # Env vars that would override the stdin session_id (resolve_session_id order). They
    # must be cleared so the renewal honestly targets the bind sid fed via the payload —
    # exactly as a real harness delivers it through stdin, not via a leaked operator env.
    override_vars = (
        "DADAIA_SESSION_ID",
        "CLAUDE_CODE_SESSION_ID",
        "CODEX_SESSION_ID",
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
    assert _resolve_mode(ws, sess_id, "myctx", None) == "READ"


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


def test_bind_without_last_seen_at_decays_ttl_from_creation(tmp_path: Path) -> None:
    """FR-W1-04: a record WITHOUT last_seen_at uses TTL-from-creation (bound_at) for GC.

    A pre-last_seen_at record whose bound_at is past TTL is collected; one whose bound_at
    is fresh is spared. The session-record pid is NEVER consulted for bind GC.
    """
    ws = _make_workspace(tmp_path)
    from dadaia_workspace.features.spec_context import session_identity

    # Stale-by-creation: bound_at past TTL, no last_seen_at at all.
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
    # Fresh-by-creation: bound_at recent, no last_seen_at.
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

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not (ws / ".dadaia" / "sessions" / f"{stale_id}.json").exists(), (
        f"Pre-last_seen_at record stale by creation must be collected. Actions: {actions}"
    )
    assert (ws / ".dadaia" / "sessions" / f"{fresh_id}.json").exists(), (
        f"Pre-last_seen_at record fresh by creation must be spared. Actions: {actions}"
    )


def test_invalid_lock_file_deleted_after_fix(tmp_path: Path) -> None:
    """Invalid JSON lock file is deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    bad_lock = ctx_locks_dir / "badctx.lock.json"
    bad_lock.write_text("NOT JSON {{{", encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not bad_lock.exists(), "Invalid JSON lock file should be deleted by fix"
    assert any("LOCK-NEW" in a and "badctx.lock.json" in a for a in actions), (
        f"Expected LOCK-NEW action for badctx.lock.json, got: {actions}"
    )


def test_missing_fields_lock_file_deleted_after_fix(tmp_path: Path) -> None:
    """Lock file missing required fields is deleted by doctor --fix."""
    ws = _make_workspace(tmp_path)
    ctx_locks_dir = ws / ".dadaia" / "states" / "ctx_locks"

    incomplete_lock = ctx_locks_dir / "incompletectx.lock.json"
    incomplete_rec = {
        "context": "incompletectx",
        # Missing: release, session_id, mode, acquired_at, heartbeat, ttl
    }
    incomplete_lock.write_text(json.dumps(incomplete_rec, indent=2), encoding="utf-8")

    doctor = _make_doctor(ws)
    actions = doctor.fix()

    assert not incomplete_lock.exists(), "Incomplete lock file should be deleted by fix"
    assert any("LOCK-NEW" in a and "incompletectx.lock.json" in a for a in actions), (
        f"Expected LOCK-NEW action for incompletectx.lock.json, got: {actions}"
    )
