"""v0.1.72 FR2 — same-process lease lineage adoption (bug
``rebind-does-not-adopt-same-process-lease``).

The reporter's exact remote topology: the lock record's ``session_id`` is an OLD
identity (dead prior session / hook-heartbeat harness id), its ``pid`` is the
long-lived harness process — an ANCESTOR of every CLI that harness spawns — and the
heartbeat is fresh (the harness's own PostToolUse renews it). The old forked preflight
identity check called that a "live foreign holder" and permanently blocked the rebind.

A process lineage can never be foreign to itself: ``holder_in_lineage`` discriminates
by ancestry-pid membership, ``adopt_if_own_lineage`` performs the eager rung-1
normalization at bind time, and the preflight probe uses the same discrimination.

CRITICAL adoption: lineage-membership (not sid equality) is the v0.1.72 FR2 law, kept
as two named tests (the adoption itself, and the never-touch-foreign fail-safe).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.features.spec_context import lease

_CTX = "adopt-ctx"


def _write_lock(ws: Path, *, session_id: str, pid: int) -> Path:
    lock_dir = ws / ".dadaia" / "states" / "ctx_locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "context": _CTX,
        "release": "v0.2.0",
        "session_id": session_id,
        "mode": "BOUND_IMPLEMENTATION",
        "pid": pid,
        "acquired_at": datetime.now(tz=UTC).isoformat(),
        "heartbeat": datetime.now(tz=UTC).isoformat(),
        "ttl": 120,
    }
    path = lock_dir / f"{_CTX}.lock.json"
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return path


def test_adopt_rewrites_same_lineage_record_to_new_session(tmp_path: Path) -> None:
    """The remote case: old sid + our-lineage pid ⇒ adopt; record now names the new sid
    and the incumbent pointer follows."""
    _write_lock(tmp_path, session_id="019f-old-harness-id", pid=42424)

    adopted = lease.adopt_if_own_lineage(
        tmp_path, _CTX, "sess_new", ancestry_pids=frozenset({42424})
    )

    assert adopted is True
    rec = lease.read_record(tmp_path, _CTX)
    assert rec is not None
    assert rec["session_id"] == "sess_new"
    assert rec["pid"] == 42424  # the harness pid stays — it IS the holder process
    ptr = tmp_path / ".dadaia" / "sessions" / "runtime" / f"{_CTX}.ptr"
    assert ptr.read_text(encoding="utf-8").strip() == "sess_new"


def test_adopt_never_touches_foreign_record(tmp_path: Path) -> None:
    """A record whose pid is OUTSIDE our lineage is a real foreign holder — untouched."""
    _write_lock(tmp_path, session_id="foreign-sid", pid=55555)

    adopted = lease.adopt_if_own_lineage(
        tmp_path, _CTX, "sess_new", ancestry_pids=frozenset({42424})
    )

    assert adopted is False
    rec = lease.read_record(tmp_path, _CTX)
    assert rec is not None
    assert rec["session_id"] == "foreign-sid"


def test_lineage_predicate_and_noop_matrix(tmp_path: Path) -> None:
    """holder_in_lineage membership predicate (ancestor pid / foreign pid / empty
    lineage / no record) plus adopt_if_own_lineage no-op cases (already-ours record,
    no record at all)."""
    _write_lock(tmp_path, session_id="old-harness-id", pid=42424)
    rec = lease.read_record(tmp_path, _CTX)
    assert lease.holder_in_lineage(rec, frozenset({99, 42424, 1})) is True
    assert lease.holder_in_lineage(rec, frozenset({99, 100})) is False
    assert lease.holder_in_lineage(rec, frozenset()) is False
    assert lease.holder_in_lineage(None, frozenset({42424})) is False

    # noop: record already names the caller's own session.
    ws2 = tmp_path.parent / (tmp_path.name + "-already-ours")
    _write_lock(ws2, session_id="sess_new", pid=42424)
    assert (
        lease.adopt_if_own_lineage(ws2, _CTX, "sess_new", ancestry_pids=frozenset({42424})) is False
    )

    # noop: no record exists at all.
    ws3 = tmp_path.parent / (tmp_path.name + "-no-record")
    (ws3 / ".dadaia" / "states").mkdir(parents=True)
    assert (
        lease.adopt_if_own_lineage(ws3, _CTX, "sess_new", ancestry_pids=frozenset({42424})) is False
    )
