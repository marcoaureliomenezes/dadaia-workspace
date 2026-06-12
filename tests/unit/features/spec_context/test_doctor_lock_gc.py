"""DoctorService LOCK-GC: stale-lease GC/reclaim with the pid-liveness veto (T-011-02).

Bug ``doctor-stale-lease-misdiagnosed-as-forgery`` half (1): there was no GC/reclaim
path for expired leases outside a MUTATING-write acquisition, and pre-pid records were
permanently un-reclaimable.

AC-W1-02 (the GC half): doctor reports ``LOCK-GC`` for a TTL-expired record whose holder
is dead OR whose record predates the ``pid`` field; ``--fix`` reclaims (deletes the
record); a live-pid record is NEVER reclaimed regardless of TTL.

Three states under test:
    (1) TTL-expired + dead pid        -> LOCK-GC reported; --fix deletes
    (2) TTL-expired + NO pid field    -> LOCK-GC reported; --fix deletes (pre-pid record)
    (3) TTL-expired + ALIVE pid       -> NOT reported; --fix leaves it untouched

The pid-liveness probe is injected at construction (composition-root seam) so the
verdict is deterministic — no real ``os.kill``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fcntl")

import json  # noqa: E402
from datetime import UTC, datetime, timedelta  # noqa: E402
from pathlib import Path  # noqa: E402

from dadaia_workspace.features.spec_context import lease  # noqa: E402
from dadaia_workspace.features.spec_context.doctor import DoctorService  # noqa: E402
from tests.fakes import FakeContextStore, FakeGitClient  # noqa: E402

TTL = lease.LEASE_TTL_SECONDS
CTX = "gcctx"


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".dadaia" / "states" / "ctx_locks").mkdir(parents=True)
    (ws / ".dadaia" / "sessions").mkdir(parents=True)
    (ws / "repos").mkdir()
    return ws


def _doctor(ws: Path, *, alive: bool | None) -> DoctorService:
    probe = None if alive is None else (lambda _pid: alive)
    return DoctorService(
        context_store=FakeContextStore(),
        git_client=FakeGitClient(),
        workspace_root=ws,
        pid_probe=probe,
    )


def _seed_stale(ws: Path, *, pid: int | None) -> Path:
    """Write a TTL-expired lease record to ctx_locks/. Returns its path."""
    hb = (datetime.now(tz=UTC) - timedelta(seconds=TTL + 600)).isoformat()
    rec: dict[str, object] = {
        "context": CTX,
        "release": "v0.1.11",
        "session_id": "holder",
        "mode": "IMPLEMENTATION",
        "acquired_at": hb,
        "heartbeat": hb,
        "ttl": TTL,
    }
    if pid is not None:
        rec["pid"] = pid
    path = ws / ".dadaia" / "states" / "ctx_locks" / f"{CTX}.lock.json"
    path.write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return path


def _lock_gc_codes(doctor: DoctorService) -> list[str]:
    return [i.description for i in doctor.check() if i.code == "LOCK-GC"]


# ---------------------------------------------------------------------------
# State (1): TTL-expired + dead pid -> reclaimable
# ---------------------------------------------------------------------------


def test_ttl_expired_dead_pid_reported_and_reclaimed(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    path = _seed_stale(ws, pid=4242)
    doctor = _doctor(ws, alive=False)

    reported = _lock_gc_codes(doctor)
    assert reported, "expected LOCK-GC for TTL-expired dead-holder record"
    assert "reclaim" in reported[0].lower() or "stale" in reported[0].lower()

    actions = doctor.fix()
    assert not path.exists(), "TTL-expired dead-holder record should be reclaimed by --fix"
    assert any("LOCK-GC" in a for a in actions)


# ---------------------------------------------------------------------------
# State (2): TTL-expired + NO pid field (pre-pid record) -> reclaimable
# ---------------------------------------------------------------------------


def test_ttl_expired_pidless_record_reported_and_reclaimed(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    path = _seed_stale(ws, pid=None)
    # Probe reports alive, but a pre-pid record has nothing to veto on -> still reclaimable.
    doctor = _doctor(ws, alive=True)

    reported = _lock_gc_codes(doctor)
    assert reported, "expected LOCK-GC for TTL-expired pre-pid record"

    doctor.fix()
    assert not path.exists(), "pre-pid TTL-expired record should be reclaimed by --fix"


# ---------------------------------------------------------------------------
# State (3): TTL-expired + ALIVE pid -> NEVER reclaimed
# ---------------------------------------------------------------------------


def test_ttl_expired_alive_pid_never_reclaimed(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path)
    path = _seed_stale(ws, pid=4242)
    doctor = _doctor(ws, alive=True)

    assert _lock_gc_codes(doctor) == [], "live-pid holder must NOT be reported as reclaimable"

    doctor.fix()
    assert path.exists(), "live-pid record must NEVER be reclaimed regardless of TTL"
    stored = json.loads(path.read_text())
    assert stored["session_id"] == "holder"


# ---------------------------------------------------------------------------
# Reclaim helper unit semantics (lease.reclaim)
# ---------------------------------------------------------------------------


def _fixed(dt: datetime):  # type: ignore[no-untyped-def]
    return lambda: dt


def test_reclaim_helper_decision_table() -> None:
    base = datetime(2026, 6, 10, 12, 0, 0, tzinfo=UTC)
    stale_hb = (base - timedelta(seconds=TTL + 10)).isoformat()
    fresh_hb = (base - timedelta(seconds=10)).isoformat()

    dead = lambda _pid: False  # noqa: E731
    alive = lambda _pid: True  # noqa: E731

    # TTL-expired + dead pid -> reclaimable
    assert lease.reclaim(
        {"heartbeat": stale_hb, "ttl": TTL, "pid": 99}, clock=_fixed(base), pid_probe=dead
    )
    # TTL-expired + no pid field -> reclaimable
    assert lease.reclaim({"heartbeat": stale_hb, "ttl": TTL}, clock=_fixed(base), pid_probe=alive)
    # TTL-expired + alive pid -> NOT reclaimable
    assert not lease.reclaim(
        {"heartbeat": stale_hb, "ttl": TTL, "pid": 99}, clock=_fixed(base), pid_probe=alive
    )
    # TTL-fresh -> NOT reclaimable
    assert not lease.reclaim(
        {"heartbeat": fresh_hb, "ttl": TTL, "pid": 99}, clock=_fixed(base), pid_probe=dead
    )
    # absent record -> reclaimable (corrupt/absent is reclaimable, fail-open)
    assert lease.reclaim(None, clock=_fixed(base), pid_probe=dead)
