"""T-014-08 — release-predicate helpers (FR-W4-03, both flows).

Covers the lease-level predicate logic that ``dadaia context release`` drives:

* eval flow (env sid) — release every lock record naming the sid.
* default flow (CLI sid ≠ harness sid) — release the bound context's lease ONLY when
  the holder pid is dead OR in the caller's ancestry; a LIVE FOREIGN holder is never
  released by context name alone.
* after a successful release the heartbeat does NOT renew and the lease is reclaimable.
* unbound holder with no session record → renewal continues (DP-3 invariant preserved).
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.spec_context import lease

_DEAD = lambda _pid: False  # noqa: E731 — every pid dead
_ALIVE = lambda _pid: True  # noqa: E731 — every pid alive


# --------------------------------------------------------------------------- #
# Eval flow
# --------------------------------------------------------------------------- #


def test_eval_flow_releases_every_lease_named_by_sid(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "sess_env", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxb", "sess_env", "v1", "IMPLEMENTATION", pid=4321)
    released = lease.release_for_session(tmp_path, "sess_env")
    assert sorted(released) == ["ctxa", "ctxb"]
    assert lease.read_record(tmp_path, "ctxa") is None
    assert lease.read_record(tmp_path, "ctxb") is None


def test_eval_flow_after_release_heartbeat_does_not_renew(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "sess_env", "v1", "IMPLEMENTATION", pid=4321)
    lease.release_for_session(tmp_path, "sess_env")
    # The record is gone; renew_heartbeat must NOT re-create it (DP-3).
    assert lease.renew_heartbeat(tmp_path, "ctxa", "sess_env") is False
    assert lease.read_record(tmp_path, "ctxa") is None


# --------------------------------------------------------------------------- #
# Default flow — holder-identity predicate
# --------------------------------------------------------------------------- #


def test_default_flow_releases_when_holder_pid_dead(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "harness_sid", "v1", "IMPLEMENTATION", pid=99999)
    holder = lease.release_context_if_caller_owned(
        tmp_path, "ctxa", caller_pid=4321, pid_probe=_DEAD
    )
    assert holder == "harness_sid"
    assert lease.read_record(tmp_path, "ctxa") is None


def test_default_flow_releases_when_holder_in_caller_ancestry(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "harness_sid", "v1", "IMPLEMENTATION", pid=5000)
    # Holder pid 5000 is alive AND an ancestor of caller 6000.
    ancestry = lambda h, c: (h, c) == (5000, 6000)  # noqa: E731
    holder = lease.release_context_if_caller_owned(
        tmp_path, "ctxa", caller_pid=6000, pid_probe=_ALIVE, ancestry=ancestry
    )
    assert holder == "harness_sid"
    assert lease.read_record(tmp_path, "ctxa") is None


def test_default_flow_never_releases_live_foreign_holder(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "foreign_sid", "v1", "IMPLEMENTATION", pid=7000)
    # Holder alive, NOT in caller ancestry → must NOT be released.
    ancestry = lambda _h, _c: False  # noqa: E731
    holder = lease.release_context_if_caller_owned(
        tmp_path, "ctxa", caller_pid=8000, pid_probe=_ALIVE, ancestry=ancestry
    )
    assert holder is None
    assert lease.read_record(tmp_path, "ctxa") is not None  # untouched


def test_default_flow_indeterminate_ancestry_does_not_release(tmp_path: Path) -> None:
    lease.acquire(tmp_path, "ctxa", "foreign_sid", "v1", "IMPLEMENTATION", pid=7000)
    # ancestry callable returns False for UNKNOWN (the CLI maps UNKNOWN→False) → conservative.
    holder = lease.release_context_if_caller_owned(
        tmp_path, "ctxa", caller_pid=8000, pid_probe=_ALIVE, ancestry=lambda _h, _c: False
    )
    assert holder is None
    assert lease.read_record(tmp_path, "ctxa") is not None


# --------------------------------------------------------------------------- #
# DP-3 invariant preserved: unbound holder with no session record keeps renewing
# --------------------------------------------------------------------------- #


def test_unbound_holder_with_no_session_record_keeps_renewing(tmp_path: Path) -> None:
    # No session record anywhere; the lock simply names harness_sid. renew must succeed
    # (the v0.1.10 FR-R2-01 invariant — there is NO absence-based renewal guard).
    lease.acquire(tmp_path, "ctxa", "harness_sid", "v1", "IMPLEMENTATION", pid=4321)
    assert lease.renew_heartbeat(tmp_path, "ctxa", "harness_sid") is True
