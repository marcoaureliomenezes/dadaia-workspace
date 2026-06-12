"""T-010-05 (WS-R2 FR-R2-03/04): pid-liveness probe before TAKEOVER + holder-safe renew.

Decision table under test (TTL says reclaimable on its own; the injected pid_probe is the
no-steal veto):

    TTL-stale  + pid alive  (probe)         -> BLOCK  (no takeover; foreign session yields)
    TTL-stale  + pid dead/absent (probe)    -> TAKEOVER (ACQUIRED)
    TTL-stale  + probe=None (no seam)       -> TAKEOVER (TTL-only fallback)
    TTL-fresh  + foreign                     -> BLOCK  (yield-iff-live-foreign, unchanged)
    confirmed holder, even past TTL          -> RENEWED (no self-loss; FR-R2-04)

All timing uses an injected FakeClock; the pid_probe is a fake callable, so these are
deterministic and platform-seamed (no real os.kill). The renew-vs-foreign-acquire race
(FR-R2-04) is covered by a hypothesis property test that drives the interleaving via the
``_before_write`` seam (no real threads/Barrier) and asserts on lock-file *history*.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.core.lock_liveness import is_stale
from dadaia_workspace.features.spec_context import lease

BASE = datetime(2026, 6, 6, 12, 0, 0, tzinfo=UTC)
CTX = "pidctx"
TTL = lease.LEASE_TTL_SECONDS


def fixed(dt: datetime) -> Callable[[], datetime]:
    return lambda: dt


def _seed(
    workspace: Path,
    session_id: str,
    heartbeat: datetime,
    *,
    pid: int | None = 4242,
    ttl: int = TTL,
) -> None:
    """Write a lease record directly (bypassing acquire) to set up a precise state."""
    rec: dict[str, object] = {
        "context": CTX,
        "release": "v0.1.10",
        "session_id": session_id,
        "mode": "IMPLEMENTATION",
        "acquired_at": heartbeat.isoformat(),
        "heartbeat": heartbeat.isoformat(),
        "ttl": ttl,
    }
    if pid is not None:
        rec["pid"] = pid
    lease._record_path(workspace, CTX).write_text(json.dumps(rec), encoding="utf-8")


def _field(workspace: Path, key: str) -> object:
    """Read one field from the committed lease record (asserts the record exists)."""
    rec = lease.read_record(workspace, CTX)
    assert rec is not None, "expected a committed lease record"
    return rec[key]


def _alive(_pid: int) -> bool:
    return True


def _dead(_pid: int) -> bool:
    return False


# ---------------------------------------------------------------------------
# is_stale: the pid-probe veto lives here (core.lock_liveness)
# ---------------------------------------------------------------------------


def test_is_stale_ttl_expired_pid_alive_is_not_stale() -> None:
    """TTL-expired + alive pid + probe wired ⇒ NOT stale (no takeover)."""
    hb = (BASE - timedelta(seconds=TTL + 10)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL, "pid": 4242}
    assert is_stale(rec, clock=fixed(BASE), pid_probe=_alive) is False


def test_is_stale_ttl_expired_pid_dead_is_stale() -> None:
    """TTL-expired + dead pid ⇒ stale (reclaimable ⇒ takeover)."""
    hb = (BASE - timedelta(seconds=TTL + 10)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL, "pid": 4242}
    assert is_stale(rec, clock=fixed(BASE), pid_probe=_dead) is True


def test_is_stale_ttl_expired_no_probe_is_stale_fallback() -> None:
    """TTL-expired + probe=None ⇒ TTL-only fallback ⇒ stale (Windows-safe path)."""
    hb = (BASE - timedelta(seconds=TTL + 10)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL, "pid": 4242}
    assert is_stale(rec, clock=fixed(BASE), pid_probe=None) is True


def test_is_stale_ttl_expired_legacy_record_no_pid_is_stale() -> None:
    """TTL-expired + legacy record without a pid field ⇒ no veto ⇒ stale."""
    hb = (BASE - timedelta(seconds=TTL + 10)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL}  # no pid (legacy)
    assert is_stale(rec, clock=fixed(BASE), pid_probe=_alive) is True


def test_is_stale_ttl_fresh_probe_never_consulted() -> None:
    """A TTL-fresh record is live regardless of the probe (probe can never create staleness)."""
    hb = (BASE - timedelta(seconds=1)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL, "pid": 4242}

    def _boom(_pid: int) -> bool:
        raise AssertionError("probe must not be consulted on a TTL-fresh record")

    assert is_stale(rec, clock=fixed(BASE), pid_probe=_boom) is False


def test_is_stale_probe_raises_falls_back_to_ttl() -> None:
    """A probe that raises must not deadlock — fall back to the TTL verdict (stale)."""
    hb = (BASE - timedelta(seconds=TTL + 10)).isoformat()
    rec = {"heartbeat": hb, "ttl": TTL, "pid": 4242}

    def _raises(_pid: int) -> bool:
        raise OSError("simulated probe failure")

    assert is_stale(rec, clock=fixed(BASE), pid_probe=_raises) is True


# ---------------------------------------------------------------------------
# acquire: the TAKEOVER decision honors the probe veto
# ---------------------------------------------------------------------------


def test_acquire_ttl_stale_alive_holder_blocks_no_takeover(tmp_path: Path) -> None:
    """TTL-stale foreign holder still alive ⇒ acquire BLOCKs (the live-session-theft fix)."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 5), pid=9001)
    with pytest.raises(LockHeldError) as exc:
        lease.acquire(
            tmp_path,
            CTX,
            "intruder",
            "v0.1.10",
            "IMPLEMENTATION",
            clock=fixed(BASE),
            pid_probe=_alive,
        )
    assert "actively mutating" in str(exc.value)
    # Record untouched — holder keeps its lease.
    assert _field(tmp_path, "session_id") == "holder"


def test_acquire_ttl_stale_dead_holder_takes_over(tmp_path: Path) -> None:
    """TTL-stale foreign holder whose pid is dead ⇒ TAKEOVER (ACQUIRED)."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 5), pid=9001)
    status, rec = lease.acquire(
        tmp_path,
        CTX,
        "intruder",
        "v0.1.10",
        "IMPLEMENTATION",
        clock=fixed(BASE),
        pid_probe=_dead,
    )
    assert status == "ACQUIRED"
    assert rec["session_id"] == "intruder"
    assert _field(tmp_path, "session_id") == "intruder"


def test_acquire_ttl_stale_no_probe_takes_over(tmp_path: Path) -> None:
    """probe=None ⇒ TTL-only fallback ⇒ stale holder is taken over (no regression)."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 5), pid=9001)
    status, _ = lease.acquire(
        tmp_path,
        CTX,
        "intruder",
        "v0.1.10",
        "IMPLEMENTATION",
        clock=fixed(BASE),
        pid_probe=None,
    )
    assert status == "ACQUIRED"


def test_acquire_ttl_fresh_foreign_yields(tmp_path: Path) -> None:
    """TTL-fresh foreign holder ⇒ yield as today (probe never even consulted)."""
    _seed(tmp_path, "holder", BASE, pid=9001)
    with pytest.raises(LockHeldError):
        lease.acquire(
            tmp_path,
            CTX,
            "intruder",
            "v0.1.10",
            "IMPLEMENTATION",
            clock=fixed(BASE),
            pid_probe=_dead,  # dead, yet still BLOCKs because TTL-fresh
        )
    assert _field(tmp_path, "session_id") == "holder"


def test_acquire_writes_pid_into_record(tmp_path: Path) -> None:
    """A fresh acquire stamps the holder pid (default os.getpid, injectable)."""
    status, rec = lease.acquire(
        tmp_path, CTX, "s1", "v0.1.10", "IMPLEMENTATION", clock=fixed(BASE), pid=12345
    )
    assert status == "ACQUIRED"
    assert rec["pid"] == 12345
    assert _field(tmp_path, "pid") == 12345


# ---------------------------------------------------------------------------
# holder-safe renew past TTL (FR-R2-04)
# ---------------------------------------------------------------------------


def test_acquire_confirmed_holder_renews_past_ttl(tmp_path: Path) -> None:
    """A confirmed holder (same session_id) renews even if its own heartbeat aged past TTL."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 100), pid=7)
    status, rec = lease.acquire(
        tmp_path,
        CTX,
        "holder",
        "v0.1.10",
        "IMPLEMENTATION",
        clock=fixed(BASE),
        pid_probe=_alive,
        pid=7,
    )
    assert status == "RENEWED", "a holder must never lose its own lease to its own staleness"
    assert rec["session_id"] == "holder"
    assert rec["heartbeat"] == BASE.isoformat()


def test_renew_heartbeat_past_ttl_for_holder(tmp_path: Path) -> None:
    """renew_heartbeat refreshes a holder's heartbeat even past TTL (no self-loss)."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 100), pid=7)
    assert lease.renew_heartbeat(tmp_path, CTX, "holder", clock=fixed(BASE)) is True
    assert _field(tmp_path, "heartbeat") == BASE.isoformat()


def test_renew_heartbeat_non_holder_is_noop(tmp_path: Path) -> None:
    """A non-holder renewal is a guarded no-op and never overwrites the foreign record."""
    _seed(tmp_path, "holder", BASE, pid=7)
    assert lease.renew_heartbeat(tmp_path, CTX, "stranger", clock=fixed(BASE)) is False
    assert _field(tmp_path, "session_id") == "holder"


# ---------------------------------------------------------------------------
# steal honors the pid veto
# ---------------------------------------------------------------------------


def test_steal_refuses_ttl_stale_but_alive_holder(tmp_path: Path) -> None:
    """steal must refuse a TTL-stale-but-pid-alive holder (no stealing a running session)."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 5), pid=9001)
    ok, rec = lease.steal(tmp_path, CTX, "thief", clock=fixed(BASE), pid_probe=_alive)
    assert ok is False
    assert rec is not None and rec["session_id"] == "holder"


def test_steal_succeeds_on_dead_holder(tmp_path: Path) -> None:
    """steal succeeds on a TTL-stale holder whose pid is dead."""
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 5), pid=9001)
    ok, rec = lease.steal(tmp_path, CTX, "thief", clock=fixed(BASE), pid_probe=_dead, pid=55)
    assert ok is True
    assert rec is not None and rec["session_id"] == "thief" and rec["pid"] == 55


# ---------------------------------------------------------------------------
# FR-R2-04 stress/property: renew is atomic w.r.t. foreign acquire.
#
# This is the historical race at ``lease.py`` renew_heartbeat: it read the record,
# verified ownership, then wrote — WITHOUT the O_EXCL sentinel CAS. A foreign acquire
# taking over a stale record could interleave between that read and write, after which
# the renew's write would stamp the foreign record back to the holder — yielding a
# lock-file history where two different sessions both believe they hold the lease.
#
# We drive the interleaving deterministically via the ``_before_write`` seam (the same
# seam the TOCTOU test uses): while the holder's renew is *inside* its critical section
# (sentinel held), a foreign ``acquire`` is attempted. With the CAS fix, that foreign
# acquire cannot enter the critical section (its O_EXCL open fails) and ultimately yields
# or no-ops — it NEVER commits a record. Hypothesis explores how many foreign attempts
# interleave and the holder/foreign pids; every interleaving must keep the history
# coherent. The injected ``_before_write`` is torn down by monkeypatch even on failure.
# ---------------------------------------------------------------------------


@settings(max_examples=40, deadline=None)
@given(
    n_foreign_attempts=st.integers(min_value=1, max_value=3),
    holder_past_ttl=st.booleans(),
)
def test_renew_atomic_vs_foreign_acquire_history(
    n_foreign_attempts: int, holder_past_ttl: bool
) -> None:
    """Property: a foreign acquire interleaved during a holder renew never enters history.

    Asserts on lock-file HISTORY (every committed record's session_id), proving:
      (1) history never shows two different holders flip-flopping (no foreign write
          commits while the holder is mid-renew);
      (2) a foreign renewal never appears (the foreign session is always blocked while
          the holder pid is alive);
      (3) the holder is the sole committed owner at the end.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        workspace = Path(raw)
        history: list[str] = []
        real_write = lease._write_record

        def _recording_write(path: Path, data: dict[str, object]) -> None:
            real_write(path, data)
            history.append(str(data.get("session_id")))

        # Seed the holder; optionally already past TTL (so a naive foreign acquire would
        # be eligible to take over — but the holder pid is reported alive, so it must not).
        age = TTL + 5 if holder_past_ttl else 1
        _seed(workspace, "holder", BASE - timedelta(seconds=age), pid=7)
        # _seed wrote directly, not via the recorded hook — reset history to start clean.

        original_write = lease._write_record
        lease._write_record = _recording_write
        original_before = lease._before_write
        original_backoff = lease._INITIAL_BACKOFF
        # Sentinel contention from the interleaved foreign acquire would otherwise burn
        # real backoff sleeps; zero the backoff so retries spin near-instantly (the CAS
        # logic is unchanged — only the sleep duration shrinks).
        lease._INITIAL_BACKOFF = 0.0

        try:
            foreign_committed: list[str] = []

            def _interleave_foreign() -> None:
                # Holder is inside its renew critical section (sentinel held). A foreign
                # acquire must FAIL to enter and never commit a record.
                for _ in range(n_foreign_attempts):
                    try:
                        status, _ = lease.acquire(
                            workspace,
                            CTX,
                            "intruder",
                            "v0.1.10",
                            "IMPLEMENTATION",
                            clock=fixed(BASE),
                            pid_probe=_alive,
                            pid=8,
                        )
                        if status == "ACQUIRED":
                            foreign_committed.append("intruder")
                    except LockHeldError:
                        pass  # expected: sentinel contention or live-holder yield.

            lease._before_write = _interleave_foreign
            # Holder renews itself; the seam fires the foreign attempts mid-critical-section.
            lease.acquire(
                workspace,
                CTX,
                "holder",
                "v0.1.10",
                "IMPLEMENTATION",
                clock=fixed(BASE),
                pid_probe=_alive,
                pid=7,
            )
        finally:
            lease._before_write = original_before
            lease._write_record = original_write
            lease._INITIAL_BACKOFF = original_backoff

        # INVARIANT 1: no foreign write ever committed.
        assert not foreign_committed, "foreign acquire committed a record mid-renew"
        # INVARIANT 2: history never names the foreign session.
        assert "intruder" not in history, f"lock-file history shows a foreign write: {history}"
        # INVARIANT 3: every committed write is the holder; final owner is the holder.
        assert set(history) <= {"holder"}, f"history flip-flopped holders: {history}"
        final = lease.read_record(workspace, CTX)
        assert final is not None and final["session_id"] == "holder"


def test_renew_heartbeat_serialized_against_foreign_acquire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """renew_heartbeat now runs under the sentinel CAS (the named lease.py:379-394 race).

    Proof: while renew holds the sentinel, a foreign acquire targeting the SAME context
    cannot enter the critical section (its O_EXCL open fails). This is the fix — the old
    read→write renew had no CAS, so a foreign takeover could interleave and the renew's
    write would then resurrect a stale holder belief.
    """
    _seed(tmp_path, "holder", BASE - timedelta(seconds=TTL + 50), pid=7)
    sentinel = lease._sentinel_path(tmp_path, CTX)
    observed: dict[str, bool] = {}

    real_write = lease._write_record

    def _probe_then_write(path: Path, data: dict[str, object]) -> None:
        # We are inside renew's critical section here — the sentinel must be held,
        # so a concurrent O_EXCL acquire on the same sentinel must fail.
        with pytest.raises(FileExistsError), open(sentinel, "x", encoding="utf-8"):
            pass
        observed["sentinel_held"] = True
        real_write(path, data)

    monkeypatch.setattr(lease, "_write_record", _probe_then_write)
    assert lease.renew_heartbeat(tmp_path, CTX, "holder", clock=fixed(BASE)) is True
    assert observed.get("sentinel_held") is True, "renew_heartbeat must hold the sentinel CAS"
    assert not sentinel.exists()  # released after the critical section
    assert _field(tmp_path, "session_id") == "holder"
