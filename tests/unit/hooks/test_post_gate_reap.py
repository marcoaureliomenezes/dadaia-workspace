"""FR26 (v0.4.3 T-043-41) — the reconciler reaps what it already walks.

Intent: CONTRACT — A26.1, A26.2, A26.3, AG.1

``sdd_post_gate._reap_stale_records`` extends the SAME advisory PostToolUse reconciler
that already touches this session/presence domain (``presence.renew`` /
``_refresh_session_record``) to also DELETE what has gone stale well beyond any
legitimate live session's heartbeat window: session/presence records stale beyond
N×TTL (``kernel_tunables.RECONCILER_REAP_TTL_MULTIPLIER``), their tmp markers
(``reconciler-last-*``, ``ctx-inject-fired-*``), now-empty presence context dirs, and
zombie ``.dadaia/states/lifecycle/*.json`` run records (``status`` "running"/"completed"
— "blocked" runs are a paused, still-relevant operator decision, never a zombie).

These fixtures drive ``_reap_stale_records`` (and, for the throttle-sharing and
fail-open/exit-code proofs, ``_reconcile_working_tree``/``main()``) directly against a
synthetic ``.dadaia`` tree — no real git, no real harness — mirroring
``tests/unit/features/chokepoints/test_push_verdict_gc.py``'s fixture style (the T-043-39
precedent this task explicitly follows), including its AG.1 lane-guard fixtures.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from dadaia_workspace.core.kernel_tunables import (
    PRESENCE_TTL_SECONDS,
    RECONCILER_REAP_TTL_MULTIPLIER,
    SESSION_GC_TTL_SECONDS,
)
from dadaia_workspace.features.spec_context import session_identity
from dadaia_workspace.hooks import _common, sdd_post_gate

_SELF = "self-session"
_OTHER_STALE = "other-stale-session"
_OTHER_LIVE = "other-live-session"
_CTX = "demo-ctx"

_STALE_SESSION_AGE = SESSION_GC_TTL_SECONDS * RECONCILER_REAP_TTL_MULTIPLIER + 60
_STALE_PRESENCE_AGE = PRESENCE_TTL_SECONDS * RECONCILER_REAP_TTL_MULTIPLIER + 60


def _iso(age_seconds: int, *, now: datetime) -> str:
    return (now - timedelta(seconds=age_seconds)).isoformat()


def _write_session(
    workspace: Path,
    sid: str,
    *,
    now: datetime,
    age_seconds: int | None,
    ttl_seconds: int = SESSION_GC_TTL_SECONDS,
) -> Path:
    record: dict[str, object] = {
        "session_id": sid,
        "context": _CTX,
        "mode": "IMPLEMENTATION",
        "pid": 1,
        "ttl_seconds": ttl_seconds,
    }
    if age_seconds is not None:
        record["last_seen_at"] = _iso(age_seconds, now=now)
    session_identity.write_session(workspace, sid, record)
    return session_identity.session_record_path(workspace, sid)


def _write_marker(workspace: Path, name: str, *, age_seconds: int) -> Path:
    path = workspace / ".dadaia" / "tmp" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("marker", encoding="utf-8")
    mtime = time.time() - age_seconds
    os.utime(path, (mtime, mtime))
    return path


def _write_presence(
    workspace: Path,
    ctx: str,
    sid: str,
    *,
    now: datetime,
    age_seconds: int | None,
    owner: str | None = None,
) -> Path:
    path = workspace / ".dadaia" / "states" / "presence" / ctx / f"{sid}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "session_id": owner if owner is not None else sid,
        "runtime": "unknown",
        "pid": 1,
        "started_at": _iso(age_seconds or 0, now=now),
    }
    if age_seconds is not None:
        record["last_seen_at"] = _iso(age_seconds, now=now)
    path.write_text(json.dumps(record), encoding="utf-8")
    return path


def _write_lifecycle_run(workspace: Path, run_id: str, *, status: str) -> Path:
    path = workspace / ".dadaia" / "states" / "lifecycle" / f"{run_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"run": {"run_id": run_id, "status": status}, "schema_version": "lifecycle-run-v1"}
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# A26.1 — session records stale beyond N×TTL are deleted with their markers; a live
# session's records (self, or a fresh-heartbeat foreign session) are never touched.
# ---------------------------------------------------------------------------


def test_stale_session_reaped_with_its_paired_markers(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    session_path = _write_session(tmp_path, _OTHER_STALE, now=now, age_seconds=_STALE_SESSION_AGE)
    reconciler_marker = _write_marker(tmp_path, f"reconciler-last-{_OTHER_STALE}", age_seconds=10)
    ctx_inject_marker = _write_marker(tmp_path, f"ctx-inject-fired-{_OTHER_STALE}", age_seconds=10)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert not session_path.exists()
    assert not reconciler_marker.exists()
    assert not ctx_inject_marker.exists()
    assert outcome.sessions == (_OTHER_STALE,)
    assert set(outcome.markers) == {
        f"reconciler-last-{_OTHER_STALE}",
        f"ctx-inject-fired-{_OTHER_STALE}",
    }


def test_fresh_heartbeat_foreign_session_never_touched(tmp_path: Path) -> None:
    """A26.1's own words: 'a live session's records are never touched' — proven with a
    FRESH-heartbeat record belonging to a DIFFERENT session than the one invoking reap."""
    now = datetime.now(tz=UTC)
    session_path = _write_session(tmp_path, _OTHER_LIVE, now=now, age_seconds=5)
    marker = _write_marker(tmp_path, f"reconciler-last-{_OTHER_LIVE}", age_seconds=5)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert session_path.exists()
    assert marker.exists()
    assert outcome.sessions == ()
    assert outcome.markers == ()


def test_self_session_and_markers_never_touched_even_when_ancient(tmp_path: Path) -> None:
    """The invoking session's OWN record/markers are never a reap candidate — proven by
    seeding them with an age that would otherwise qualify as stale many times over,
    independent of whatever ``main()`` would normally have refreshed moments earlier
    (defensive: ``_reap_stale_records`` is also called directly by these fixtures, exactly
    as ``_reconcile_working_tree`` is in the pre-existing reconciler suite)."""
    now = datetime.now(tz=UTC)
    session_path = _write_session(tmp_path, _SELF, now=now, age_seconds=_STALE_SESSION_AGE * 10)
    marker = _write_marker(
        tmp_path, f"reconciler-last-{_SELF}", age_seconds=_STALE_SESSION_AGE * 10
    )

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert session_path.exists()
    assert marker.exists()
    assert outcome.sessions == ()
    assert outcome.markers == ()


def test_orphaned_marker_reaped_by_own_age_when_no_owning_session_record(
    tmp_path: Path,
) -> None:
    """Real-workspace evidence (2026-08-17): several ``reconciler-last-*``/
    ``ctx-inject-fired-*`` markers reference session ids with NO ``.dadaia/sessions/<id>.json``
    at all — orphaned by a prior doctor GC pass or a session that never wrote a record.
    These fall back to the marker's OWN mtime staleness (no session record to consult)."""
    stale_marker = _write_marker(
        tmp_path, "reconciler-last-ghost-session", age_seconds=_STALE_SESSION_AGE
    )
    fresh_marker = _write_marker(tmp_path, "ctx-inject-fired-fresh-ghost", age_seconds=10)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert not stale_marker.exists()
    assert fresh_marker.exists()
    assert outcome.markers == ("reconciler-last-ghost-session",)


def test_malformed_session_record_never_aborts_the_sweep(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    broken = tmp_path / ".dadaia" / "sessions" / "broken.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("{ not json", encoding="utf-8")
    session_path = _write_session(tmp_path, _OTHER_STALE, now=now, age_seconds=_STALE_SESSION_AGE)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert broken.exists()  # unreadable ⇒ skipped, never aborts the rest of the sweep.
    assert not session_path.exists()
    assert outcome.sessions == (_OTHER_STALE,)


# ---------------------------------------------------------------------------
# A26.1 — presence records stale beyond N×TTL are reaped; a now-empty context dir is
# removed; a pre-existing empty context dir is removed too.
# ---------------------------------------------------------------------------


def test_stale_presence_reaped_and_empty_context_dir_removed(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    ctx_dir = tmp_path / ".dadaia" / "states" / "presence" / _CTX
    path = _write_presence(
        tmp_path, _CTX, "stale-presence-owner", now=now, age_seconds=_STALE_PRESENCE_AGE
    )

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert not path.exists()
    assert not ctx_dir.exists()
    assert outcome.presence == (f"{_CTX}/stale-presence-owner.json",)
    assert outcome.empty_context_dirs == (_CTX,)


def test_fresh_presence_survives_context_dir_survives(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    ctx_dir = tmp_path / ".dadaia" / "states" / "presence" / _CTX
    path = _write_presence(tmp_path, _CTX, "live-presence-owner", now=now, age_seconds=5)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert path.exists()
    assert ctx_dir.exists()
    assert outcome.presence == ()
    assert outcome.empty_context_dirs == ()


def test_self_owned_presence_never_touched_even_when_ancient(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    path = _write_presence(
        tmp_path, _CTX, _SELF, now=now, age_seconds=_STALE_PRESENCE_AGE * 10, owner=_SELF
    )

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert path.exists()
    assert outcome.presence == ()


def test_pre_existing_empty_context_dir_removed(tmp_path: Path) -> None:
    empty_dir = tmp_path / ".dadaia" / "states" / "presence" / "already-empty-ctx"
    empty_dir.mkdir(parents=True)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert not empty_dir.exists()
    assert outcome.empty_context_dirs == ("already-empty-ctx",)


def test_malformed_presence_record_never_aborts_the_sweep(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    broken = tmp_path / ".dadaia" / "states" / "presence" / _CTX / "broken.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("{ not json", encoding="utf-8")
    stale_path = _write_presence(
        tmp_path, _CTX, "stale-presence-owner", now=now, age_seconds=_STALE_PRESENCE_AGE
    )

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    # A malformed record has no readable heartbeat ⇒ treated as stale (fail toward
    # cleanup — mirrors ``presence.others_alive``'s existing corrupt-record handling) and
    # is reaped too; the point under test is that it never raises out of the sweep and
    # never prevents the legitimate stale sibling from being reaped in the same pass.
    assert not broken.exists()
    assert not stale_path.exists()
    assert set(outcome.presence) == {f"{_CTX}/broken.json", f"{_CTX}/stale-presence-owner.json"}


# ---------------------------------------------------------------------------
# A26.2 — zombie lifecycle/state run records ("running"/"completed") are reaped; a
# "blocked" run (a paused, still-relevant operator decision) is never touched.
# ---------------------------------------------------------------------------


def test_zombie_lifecycle_runs_reaped_blocked_survives(tmp_path: Path) -> None:
    running = _write_lifecycle_run(tmp_path, "zombie-running", status="running")
    completed = _write_lifecycle_run(tmp_path, "zombie-completed", status="completed")
    blocked = _write_lifecycle_run(tmp_path, "paused-blocked", status="blocked")

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert not running.exists()
    assert not completed.exists()
    assert blocked.exists()
    assert set(outcome.lifecycle_runs) == {"zombie-running.json", "zombie-completed.json"}


def test_malformed_lifecycle_record_never_aborts_the_sweep(tmp_path: Path) -> None:
    broken = tmp_path / ".dadaia" / "states" / "lifecycle" / "broken.json"
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_text("{ not json", encoding="utf-8")
    running = _write_lifecycle_run(tmp_path, "zombie-running", status="running")

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert broken.exists()
    assert not running.exists()
    assert outcome.lifecycle_runs == ("zombie-running.json",)


# ---------------------------------------------------------------------------
# AG.1 — every reap target is resolved before deletion, refused if it resolves outside
# ``.dadaia/``, and a symlinked directory is never followed. Mirrors
# ``tests/unit/features/chokepoints/test_push_verdict_gc.py``'s two lane-guard fixtures.
# ---------------------------------------------------------------------------


def test_lane_guard_never_follows_a_symlinked_directory(tmp_path: Path) -> None:
    """AG.1's "never follow a symlinked directory" clause is a SEPARATE guard from
    "refuse a target resolving outside .dadaia/" (the next test) — this fixture isolates
    it: the decoy's real target lives INSIDE ``.dadaia/`` itself, so ``_resolved_within``
    alone would happily accept it. Only ``os.walk(..., followlinks=False)`` keeps it safe
    — verified with the T-043-39 trick: temporarily flipping to ``followlinks=True``
    (during development of this fixture) makes it fail (the decoy gets discovered,
    reaped, and deleted through the symlink), proving the guard is load-bearing, not
    coincidental."""
    now = datetime.now(tz=UTC)
    real_target = tmp_path / ".dadaia" / "states" / "presence-linked-target"
    real_target.mkdir(parents=True)
    decoy = real_target / "decoy.json"
    decoy.write_text(
        json.dumps({"session_id": "decoy", "last_seen_at": _iso(_STALE_PRESENCE_AGE, now=now)}),
        encoding="utf-8",
    )

    presence_root = tmp_path / ".dadaia" / "states" / "presence"
    presence_root.mkdir(parents=True)
    (presence_root / "linked-ctx").symlink_to(real_target, target_is_directory=True)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    # The symlinked context dir is never descended into, so the decoy is never even
    # discovered — not reaped, not counted — and the symlink itself is never removed as
    # an "empty" context dir.
    assert decoy.exists()
    assert (presence_root / "linked-ctx").exists()
    assert outcome.presence == ()
    assert outcome.empty_context_dirs == ()


def test_lane_guard_refuses_a_target_resolving_outside_dadaia(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    outside = tmp_path / "outside-dadaia"
    outside.mkdir()
    real = outside / "real.json"
    real.write_text(
        json.dumps({"session_id": "escapee", "last_seen_at": _iso(_STALE_PRESENCE_AGE, now=now)}),
        encoding="utf-8",
    )

    ctx_dir = tmp_path / ".dadaia" / "states" / "presence" / _CTX
    ctx_dir.mkdir(parents=True)
    escape = ctx_dir / "escape.json"
    escape.symlink_to(real)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    assert real.exists()
    assert escape.exists()
    assert outcome.presence == ()


# ---------------------------------------------------------------------------
# A26.3 — reaping is best-effort/fail-open, matching the reconciler it extends: an
# unlink failure never aborts the sweep, and an internal reap error never changes the
# hook's exit code or blocks the advisory reconciler pass that follows it.
# ---------------------------------------------------------------------------


def test_unlink_failure_is_best_effort_and_does_not_abort_sweep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(tz=UTC)
    ctx_dir = tmp_path / ".dadaia" / "states" / "lifecycle"
    protected = _write_lifecycle_run(tmp_path, "protected", status="completed")
    other = _write_lifecycle_run(tmp_path, "other", status="running")
    # Also seed an unrelated, independently-reapable stale session to prove one lane's
    # failure never prevents a DIFFERENT lane from completing its own sweep.
    session_path = _write_session(tmp_path, _OTHER_STALE, now=now, age_seconds=_STALE_SESSION_AGE)

    # Portable removal-failure simulation (not ``os.chmod`` on the containing
    # directory): the POSIX read-only-directory permission model is a platform no-op
    # for file deletion on Windows (the read-only attribute NTFS exposes there does not
    # block content deletion the way a POSIX write-permission bit does), so the
    # chmod-based simulation never actually denies the unlink and the best-effort
    # branch goes unexercised. Monkeypatching ``Path.unlink`` to raise for these exact
    # targets — same idiom as the v0.4.2 unreadable-file precedent (monkeypatched
    # ``Path.read_text``) — exercises the identical ``except OSError`` branch
    # identically on every platform; matched by value equality (the production code
    # builds its own ``Path`` instances via ``iterdir()``), so the unrelated session
    # lane's own unlink is untouched.
    denied = {protected, other}
    real_unlink = Path.unlink

    def _unlink_denied(self: Path, *args: object, **kwargs: object) -> None:
        if self in denied:
            raise PermissionError(13, "Permission denied", str(self))
        real_unlink(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "unlink", _unlink_denied)

    outcome = sdd_post_gate._reap_stale_records(tmp_path, _SELF)

    # Neither lifecycle record could be unlinked (denied) — best-effort,
    # no raise — but the unrelated session lane still completed its own sweep.
    assert (ctx_dir / "protected.json").exists()
    assert (ctx_dir / "other.json").exists()
    assert outcome.lifecycle_runs == ()
    assert not session_path.exists()
    assert outcome.sessions == (_OTHER_STALE,)


def test_reap_never_raises_and_never_changes_exit_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A26.3: an internal reap error must never break the PostToolUse hook's contract —
    ``main()`` still exits 0, and the advisory reconciler pass still runs to completion."""
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / "repos" / _CTX).mkdir(parents=True, exist_ok=True)
    session_identity.write_session(
        tmp_path,
        _SELF,
        {"session_id": _SELF, "context": _CTX, "mode": "IMPLEMENTATION", "pid": 1},
    )

    def _boom(workspace: Path, sess_id: str, **_: object) -> None:
        raise RuntimeError("reap blew up mid-pass")

    monkeypatch.setattr(sdd_post_gate, "_reap_stale_records", _boom)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: [])
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(_common, "read_stdin_json", lambda: {"session_id": _SELF})
    monkeypatch.setattr(_common, "resolve_session_id", lambda payload: _SELF)

    assert sdd_post_gate.main() == 0


# ---------------------------------------------------------------------------
# The reap runs on the SAME throttle cadence as the advisory working-tree walk it now
# shares a call site with — "the reconciler reaps what it already walks", not a second,
# independent, unthrottled sweep on every single tool call.
# ---------------------------------------------------------------------------


def test_reap_shares_the_reconciler_throttle_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    (tmp_path / "repos" / _CTX).mkdir(parents=True, exist_ok=True)
    session_identity.write_session(
        tmp_path,
        _SELF,
        {"session_id": _SELF, "context": _CTX, "mode": "IMPLEMENTATION", "pid": 1},
    )
    now = datetime.now(tz=UTC)
    _write_session(tmp_path, _OTHER_STALE, now=now, age_seconds=_STALE_SESSION_AGE)

    calls = {"n": 0}
    real_reap = sdd_post_gate._reap_stale_records

    def _spy(workspace: Path, sess_id: str, **kwargs: object) -> sdd_post_gate.ReapOutcome:
        calls["n"] += 1
        return real_reap(workspace, sess_id, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(sdd_post_gate, "_reap_stale_records", _spy)
    monkeypatch.setattr(sdd_post_gate, "_porcelain_paths", lambda repo: [])

    sdd_post_gate._reconcile_working_tree(tmp_path, _SELF)  # first: runs, throttle stamped
    sdd_post_gate._reconcile_working_tree(tmp_path, _SELF)  # second: throttled, no reap call

    assert calls["n"] == 1, "a throttled invocation must not re-run the reap either"


# ---------------------------------------------------------------------------
# FR27/A27.1 (T-043-42): reconciler-events.jsonl rotates for the reap-event writer
# too — same shared file, same shared rotation helper as the flag writer.
# ---------------------------------------------------------------------------


def test_reap_event_rotates_the_shared_events_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import dadaia_workspace.infrastructure.jsonl_log_rotation as rotation

    log = tmp_path / ".dadaia" / "logs" / "reconciler-events.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text('{"seed": true}\n', encoding="utf-8")
    monkeypatch.setattr(rotation, "LOG_ROTATION_MAX_BYTES", 8)

    outcome = sdd_post_gate.ReapOutcome(sessions=("stale-1",))
    sdd_post_gate._append_reap_event(tmp_path, _SELF, outcome)  # noqa: SLF001

    rotated = log.with_name(log.name + ".1")
    assert rotated.exists()
    assert json.loads(rotated.read_text(encoding="utf-8").strip()) == {"seed": True}
    new_lines = [ln for ln in log.read_text(encoding="utf-8").splitlines() if ln]
    assert len(new_lines) == 1
    rec = json.loads(new_lines[0])
    assert rec["event"] == "RECONCILER_REAP"
    assert rec["sessions_reaped"] == 1
