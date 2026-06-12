"""T-014-07 — by-session heartbeat index, same-CAS atomic (FR-W4-02).

Asserts:

* ``acquire``/``steal``/``release`` maintain ``ctx_locks/by-session/<sid>.json``.
* The index write happens INSIDE the sentinel CAS — a crash injected via the existing
  ``_before_write`` seam leaves NEITHER the record NOR the index half-written (they
  cannot diverge).
* PostToolUse does NOT scan the lock dir when the session holds nothing
  (FS-op-counting fake).
* Full-scan fallback fires only when the by-session DIR is absent (migration window).
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


# --------------------------------------------------------------------------- #
# Index is maintained across the lease lifecycle
# --------------------------------------------------------------------------- #


def test_acquire_writes_by_session_index(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    assert _read_index(tmp_path, "sess_a") == ["ctxa"]


def test_acquire_two_contexts_indexed(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxb", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    assert _read_index(tmp_path, "sess_a") == ["ctxa", "ctxb"]
    assert lease.contexts_for_session(tmp_path, "sess_a") == ["ctxa", "ctxb"]


def test_release_removes_ctx_from_index_and_unlinks_when_empty(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxb", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    lease.release(tmp_path, "ctxa", "sess_a")
    assert _read_index(tmp_path, "sess_a") == ["ctxb"]
    lease.release(tmp_path, "ctxb", "sess_a")
    assert not _by_session_file(tmp_path, "sess_a").exists()


def test_steal_transfers_index_to_new_holder(tmp_path: Path) -> None:
    # sess_a holds ctxa; its pid is dead so sess_b can steal.
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=999999)
    dead = lambda pid: False  # noqa: E731 — terse fake probe: every pid is dead.

    # Age the record past TTL so it is reclaimable.
    rec = lease.read_record(tmp_path, "ctxa")
    assert rec is not None
    rec["heartbeat"] = "2000-01-01T00:00:00+00:00"
    lease._write_record(lease._record_path(tmp_path, "ctxa"), rec)

    ok, _ = lease.steal(tmp_path, "ctxa", "sess_b", pid_probe=dead, pid=4321)
    assert ok
    assert _read_index(tmp_path, "sess_a") == []  # old holder's entry cleaned
    assert _read_index(tmp_path, "sess_b") == ["ctxa"]


# --------------------------------------------------------------------------- #
# Same-CAS atomicity: record + index cannot diverge under crash injection
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# PostToolUse renewal: no lock-dir scan when the session holds nothing
# --------------------------------------------------------------------------- #


def test_post_gate_does_not_scan_lock_dir_when_holding_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dadaia_workspace.hooks import sdd_post_gate

    # One foreign lease exists (so the lock dir is non-empty) but sess_b holds nothing.
    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)

    lock_dir = tmp_path / ".dadaia" / "states" / "ctx_locks"
    scanned: list[Path] = []
    real_iterdir = Path.iterdir

    def _spy_iterdir(self: Path):  # type: ignore[no-untyped-def]
        if self == lock_dir:
            scanned.append(self)
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", _spy_iterdir)

    result = sdd_post_gate._iter_lease_contexts(tmp_path, "sess_b")
    assert result == []
    assert scanned == []  # the lock dir was NEVER scanned for a no-hold session.


def test_post_gate_index_driven_returns_only_held_contexts(tmp_path: Path) -> None:
    from dadaia_workspace.hooks import sdd_post_gate

    lease.acquire(tmp_path, "ctxa", "sess_a", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxb", "sess_b", "v1", "IMPLEMENTATION", pid=4321)
    assert sdd_post_gate._iter_lease_contexts(tmp_path, "sess_a") == ["ctxa"]
    assert sdd_post_gate._iter_lease_contexts(tmp_path, "sess_b") == ["ctxb"]


def test_post_gate_full_scan_fallback_when_index_dir_absent(tmp_path: Path) -> None:
    from dadaia_workspace.hooks import sdd_post_gate

    # Simulate a pre-index (migration) workspace: a lock record with NO by-session dir.
    lock_dir = tmp_path / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True)
    (lock_dir / "legacy.lock.json").write_text(
        json.dumps({"context": "legacy", "session_id": "sess_x"}), encoding="utf-8"
    )
    assert not (lock_dir / "by-session").exists()
    # Fallback returns the legacy record's context via the full scan.
    assert sdd_post_gate._iter_lease_contexts(tmp_path, "sess_x") == ["legacy"]
