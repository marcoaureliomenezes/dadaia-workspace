"""T-014-07 — by-session heartbeat index, same-CAS atomic (FR-W4-02).

Asserts:

* ``acquire``/``steal``/``release`` maintain ``ctx_locks/by-session/<sid>.json``.
* The index write happens INSIDE the sentinel CAS — a crash injected via the existing
  ``_before_write`` seam leaves NEITHER the record NOR the index half-written (they
  cannot diverge) — atomicity is lease-integrity coverage, kept as a named test.
* PostToolUse renewal is index-driven, with a full-scan fallback only when the
  by-session DIR is absent (migration window).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dadaia_workspace.features.spec_context import lease


def _by_session_file(workspace: Path, sid: str) -> Path:
    return workspace / ".dadaia" / "states" / "ctx_locks" / "by-session" / f"{sid}.json"


def _read_index(workspace: Path, sid: str) -> list[str]:
    path = _by_session_file(workspace, sid)
    if not path.exists():
        return []
    return sorted(json.loads(path.read_text(encoding="utf-8"))["contexts"])


# ---------------------------------------------------------------------------
# Index maintained across the lease lifecycle + PostToolUse index-driven scan — 1 param
# ---------------------------------------------------------------------------


def test_index_maintained_across_lifecycle_and_post_gate_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.hooks import sdd_post_gate

    # acquire writes the by-session index; a second context for the same sid appends.
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    assert _read_index(tmp_path, "sess_a") == ["ctxa"]
    lease.acquire(tmp_path, "ctxb", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    assert _read_index(tmp_path, "sess_a") == ["ctxa", "ctxb"]
    assert lease.contexts_for_session(tmp_path, "sess_a") == ["ctxa", "ctxb"]

    # release removes the ctx from the index and unlinks the file when empty.
    lease.release(tmp_path, "ctxa", "sess_a")
    assert _read_index(tmp_path, "sess_a") == ["ctxb"]
    lease.release(tmp_path, "ctxb", "sess_a")
    assert not _by_session_file(tmp_path, "sess_a").exists()

    # steal transfers the index entry to the new holder.
    lease.acquire(tmp_path, "ctxc", "sess_c", "v1", "IMPLEMENTATION", pid=999999)
    dead = lambda pid: False  # noqa: E731
    rec = lease.read_record(tmp_path, "ctxc")
    assert rec is not None
    rec["heartbeat"] = "2000-01-01T00:00:00+00:00"
    lease._write_record(lease._record_path(tmp_path, "ctxc"), rec)
    ok, _ = lease.steal(tmp_path, "ctxc", "sess_d", pid_probe=dead, pid=4321)
    assert ok
    assert _read_index(tmp_path, "sess_c") == []
    assert _read_index(tmp_path, "sess_d") == ["ctxc"]

    # PostToolUse: index-driven lookup returns only the querying session's held contexts.
    lease.acquire(tmp_path, "ctxe", "sess_e", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxf", "sess_f", "v1", "IMPLEMENTATION", pid=4321)
    assert sdd_post_gate._iter_lease_contexts(tmp_path, "sess_e") == ["ctxe"]
    assert sdd_post_gate._iter_lease_contexts(tmp_path, "sess_f") == ["ctxf"]

    # Full-scan fallback fires only when the by-session dir is absent (migration window).
    fallback_ws = tmp_path.parent / (tmp_path.name + "-fallback")
    lock_dir = fallback_ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / "legacy.lock.json").write_text(
        json.dumps({"context": "legacy", "session_id": "sess_x"}), encoding="utf-8"
    )
    assert not (lock_dir / "by-session").exists()
    assert sdd_post_gate._iter_lease_contexts(fallback_ws, "sess_x") == ["legacy"]


# ---------------------------------------------------------------------------
# Same-CAS atomicity: record + index cannot diverge under crash injection — kept
# ---------------------------------------------------------------------------


def test_crash_before_write_leaves_neither_record_nor_index(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DADAIA_TESTING", "1")

    class _Boom(RuntimeError):
        pass

    def _crash() -> None:
        raise _Boom

    monkeypatch.setattr(lease, "_before_write", _crash)
    with pytest.raises(_Boom):
        lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)

    # Neither half was written — the record write and the index write are one unit,
    # both gated behind the same _before_write seam.
    assert lease.read_record(tmp_path, "ctxa") is None
    assert _read_index(tmp_path, "sess_a") == []


# ---------------------------------------------------------------------------
# .ptr-match RENEW must not dangle the old sid's index entry — kept (F-7)
# ---------------------------------------------------------------------------


def test_ptr_renew_removes_replaced_sid_entry(tmp_path: Path) -> None:
    """v0.1.50 FR2 (audit F-7): the .ptr-match RENEW must not dangle the old sid."""
    lease.acquire(tmp_path, "ctxa", "sess_inc", "v1", "IMPLEMENTATION", pid=4321)

    # Simulate a drifted lock record (relaunch without .ptr cleanup): the record
    # names a foreign sid with its own index entry, while .ptr still names sess_inc.
    rec = lease.read_record(tmp_path, "ctxa")
    assert rec is not None
    rec["session_id"] = "sess_drift"
    lease._write_record(lease._record_path(tmp_path, "ctxa"), rec)
    lease._index_add(tmp_path, "ctxa", "sess_drift")

    status, renewed = lease.acquire(tmp_path, "ctxa", "sess_inc", "v1", "IMPLEMENTATION", pid=4321)
    assert status == "RENEWED"
    assert renewed["session_id"] == "sess_inc"

    index_dir = tmp_path / ".dadaia" / "states" / "ctx_locks" / "by-session"
    assert (index_dir / "sess_inc.json").exists()
    assert not (index_dir / "sess_drift.json").exists()


# ---------------------------------------------------------------------------
# session_holds requires CAS-indexed evidence — kept
# ---------------------------------------------------------------------------


def test_session_holds_reads_acquisition_evidence(tmp_path: Path) -> None:
    """v0.1.50 FR2: session_holds is True only for a same-CAS-indexed holder."""
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)

    assert lease.session_holds(tmp_path, "ctxa", "sess_a") is True
    assert lease.session_holds(tmp_path, "ctxa", "sess_ghost") is False
    assert lease.session_holds(tmp_path, "ctxb", "sess_a") is False
