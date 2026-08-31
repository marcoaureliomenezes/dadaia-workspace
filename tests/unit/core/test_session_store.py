"""Caller-scoped session-record storage tests (``core.session_store``).

Intent: CONTRACT — release K1 ("One Invocation"). Replaces
``tests/unit/features/spec_context/test_session_identity.py`` at the new interface:
the module moved from ``features.spec_context.session_identity`` into
``core.session_store`` (core cannot import features; :mod:`core.invocation` needs to
read a session record directly). Behavior is unchanged — this file is the deepened
module's test surface, ported byte-for-byte onto the new import path.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables, session_store
from dadaia_workspace.core import session_store as si

CTX = "myctx"
SID = "my-session-id"


def _ws(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    (ws / ".dadaia" / "states").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    return ws


# --------------------------------------------------------------------------- paths + traversal


@pytest.mark.parametrize(
    "bad_name",
    ["../escape", "a/b", "a.b"],
)
def test_path_validation_rejects_traversal(tmp_path: Path, bad_name: str) -> None:
    """FR-R3-03: every artifact lives under PROTECTED .dadaia/sessions/, and any name
    carrying a path separator or traversal segment is rejected (CWE-22)."""
    ws = _ws(tmp_path)
    path = si.session_record_path(ws, SID)
    assert path.relative_to(ws).as_posix().startswith(".dadaia/sessions/")
    with pytest.raises(ValueError, match="CWE-22"):
        si.session_record_path(ws, bad_name)


# --------------------------------------------------------------------------- record: roundtrip/atomic/fail-soft


def test_record_roundtrip_atomicity_and_fail_soft(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # session record: absent -> None, write -> read roundtrip.
    assert si.read_session(ws, SID) is None
    record = {"id": SID, "mode": "READ", "pid": 4242, "context": CTX}
    si.write_session(ws, SID, record)
    assert si.read_session(ws, SID) == record
    sessions = ws / ".dadaia" / "sessions"
    assert [p.name for p in sessions.iterdir() if p.name.endswith(".tmp")] == []

    # fail-soft: corrupt JSON, non-dict content, and an invalid id all yield None.
    si.session_record_path(ws, "corrupt", create=True).write_text("{not json", encoding="utf-8")
    assert si.read_session(ws, "corrupt") is None
    si.session_record_path(ws, "nondict", create=True).write_text("[1, 2, 3]", encoding="utf-8")
    assert si.read_session(ws, "nondict") is None
    assert si.read_session(ws, "../bad") is None

    # Pre-existing session JSON remains fail-soft.
    (ws / ".dadaia" / "sessions" / "old-layout.json").write_text(
        json.dumps({"legacy": True}), encoding="utf-8"
    )
    assert si.read_session(ws, "old-layout") == {"legacy": True}


# --------------------------------------------------------------------------- last_seen_at / liveness_timestamp (T-011-04)


def test_last_seen_at_and_liveness_timestamp_matrix(tmp_path: Path) -> None:
    ws = _ws(tmp_path)

    # touch_last_seen_at stamps and persists.
    si.write_session(
        ws, SID, {"id": SID, "mode": "READ", "last_seen_at": "2020-01-01T00:00:00+00:00"}
    )
    updated = si.touch_last_seen_at(ws, SID, now="2030-06-10T12:00:00+00:00")
    assert updated is not None
    assert updated["last_seen_at"] == "2030-06-10T12:00:00+00:00"
    reread = si.read_session(ws, SID)
    assert reread is not None and reread["last_seen_at"] == "2030-06-10T12:00:00+00:00"

    # missing record -> None (fail-soft, no-op).
    assert si.touch_last_seen_at(ws, "ghost", now="2030-06-10T12:00:00+00:00") is None

    # liveness_timestamp: prefers last_seen_at, falls back to bound_at/created_at, else "".
    assert (
        si.liveness_timestamp(
            {"last_seen_at": "2030-06-10T12:00:00+00:00", "bound_at": "2020-01-01T00:00:00+00:00"}
        )
        == "2030-06-10T12:00:00+00:00"
    )
    assert (
        si.liveness_timestamp({"bound_at": "2020-01-01T00:00:00+00:00"})
        == "2020-01-01T00:00:00+00:00"
    )
    assert (
        si.liveness_timestamp({"created_at": "2019-01-01T00:00:00+00:00"})
        == "2019-01-01T00:00:00+00:00"
    )
    assert si.liveness_timestamp({"mode": "READ"}) == ""


# ---------------------------------------------------------------------------
# F002 (20260830-design-bug-surface-audit): the session-binding record gets an OWNING
# module. session_store authors the schema (new_binding_record), owns the liveness
# predicate (is_live/live_session) and the reaper (reap_stale) — the CLI, invocation
# and the spec-context doctor stop hand-assembling gc_check dicts.
# ---------------------------------------------------------------------------


def test_new_binding_record_authors_the_schema() -> None:
    record = session_store.new_binding_record(
        session_id="sess-1",
        context="alpha",
        mode="BOUND_IMPLEMENTATION",
        release="0.5.3",
        runtime="claude-code",
        pid=1234,
        now="2026-08-31T12:00:00+00:00",
    )
    assert record == {
        "session_id": "sess-1",
        "context": "alpha",
        "mode": "BOUND_IMPLEMENTATION",
        "release": "0.5.3",
        "runtime": "claude-code",
        "pid": 1234,
        "bound_at": "2026-08-31T12:00:00+00:00",
        "last_seen_at": "2026-08-31T12:00:00+00:00",
        "ttl_seconds": kernel_tunables.SESSION_GC_TTL_SECONDS,
    }
    # The dead `is_stale: False` field (written by the old inline author, read by
    # nothing) does not survive the fold.
    assert "is_stale" not in record


def test_is_live_and_live_session(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    fresh = session_store.new_binding_record(
        session_id="sess-2",
        context="alpha",
        mode="READ",
        release=None,
        runtime="unknown",
        pid=1,
        now=now.isoformat(),
    )
    assert session_store.is_live(fresh)
    session_store.write_session(tmp_path, "sess-2", fresh)
    assert session_store.live_session(tmp_path, "sess-2") == fresh

    stale = dict(fresh)
    stale["last_seen_at"] = "2000-01-01T00:00:00+00:00"
    stale["bound_at"] = "2000-01-01T00:00:00+00:00"
    assert not session_store.is_live(stale)
    session_store.write_session(tmp_path, "sess-3", stale)
    assert session_store.live_session(tmp_path, "sess-3") is None
    assert session_store.live_session(tmp_path, "sess-absent") is None


def test_reap_stale_deletes_only_expired_records(tmp_path: Path) -> None:
    now = datetime.now(tz=UTC)
    live = session_store.new_binding_record(
        session_id="live-1",
        context="a",
        mode="READ",
        release=None,
        runtime="unknown",
        pid=1,
        now=now.isoformat(),
    )
    dead = dict(live)
    dead["last_seen_at"] = "2000-01-01T00:00:00+00:00"
    dead["bound_at"] = "2000-01-01T00:00:00+00:00"
    session_store.write_session(tmp_path, "live-1", live)
    session_store.write_session(tmp_path, "dead-1", dead)
    (session_store.sessions_dir(tmp_path) / "not-a-record.txt").write_text("", encoding="utf-8")

    reaped = session_store.reap_stale(tmp_path)

    assert reaped == ["dead-1"]
    assert session_store.read_session(tmp_path, "live-1") is not None
    assert session_store.read_session(tmp_path, "dead-1") is None


def test_gc_check_assembly_has_one_home() -> None:
    """The hand-built ``gc_check`` dict must not exist outside session_store: the
    liveness-predicate INPUT is owned by the record's owner (F002)."""
    import dadaia_workspace

    pkg_root = Path(dadaia_workspace.__file__).parent
    offenders = [
        str(p.relative_to(pkg_root))
        for p in sorted(pkg_root.rglob("*.py"))
        if "gc_check" in p.read_text(encoding="utf-8")
    ]
    assert offenders == [], offenders
