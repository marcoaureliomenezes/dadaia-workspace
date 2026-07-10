"""T-014-08 — release-predicate helpers (FR-W4-03, both flows).

Covers the lease-level predicate logic that ``dadaia context release`` drives:

* eval flow (env sid) — release every lock record naming the sid.
* default flow (CLI sid ≠ harness sid) — release the bound context's lease ONLY when
  the holder pid is dead OR in the caller's ancestry; a LIVE FOREIGN holder is never
  released by context name alone.
* after a successful release the heartbeat does NOT renew and the lease is reclaimable.
* unbound holder with no session record → renewal continues (DP-3 invariant preserved).

CRITICAL pid-lineage release semantics (v0.1.72 FR2): never-releases-live-foreign-holder
and indeterminate-ancestry-does-not-release are the fail-safe rows and stay named.
"""

from __future__ import annotations

from pathlib import Path

from dadaia_workspace.features.spec_context import lease

_DEAD = lambda _pid: False  # noqa: E731 — every pid dead
_ALIVE = lambda _pid: True  # noqa: E731 — every pid alive


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


# ---------------------------------------------------------------------------
# Eval-flow release + dead-pid/ancestry release + unbound-keeps-renewing — 1 param
# ---------------------------------------------------------------------------


def test_release_and_renewal_flow_matrix(tmp_path: Path) -> None:
    # Eval flow (env sid): release_for_session releases every lease named by the sid,
    # and after release the heartbeat does NOT renew (DP-3: no phantom re-creation).
    lease.acquire(tmp_path, "ctxa", "sess_env", "v1", "IMPLEMENTATION", pid=4321)
    lease.acquire(tmp_path, "ctxb", "sess_env", "v1", "IMPLEMENTATION", pid=4321)
    released = lease.release_for_session(tmp_path, "sess_env")
    assert sorted(released) == ["ctxa", "ctxb"]
    assert lease.read_record(tmp_path, "ctxa") is None
    assert lease.read_record(tmp_path, "ctxb") is None
    assert lease.renew_heartbeat(tmp_path, "ctxa", "sess_env") is False
    assert lease.read_record(tmp_path, "ctxa") is None

    # Default flow: releases when the holder pid is dead.
    lease.acquire(tmp_path, "ctxc", "harness_sid", "v1", "IMPLEMENTATION", pid=99999)
    holder = lease.release_context_if_caller_owned(
        tmp_path, "ctxc", caller_pid=4321, pid_probe=_DEAD
    )
    assert holder == "harness_sid"
    assert lease.read_record(tmp_path, "ctxc") is None

    # Default flow: releases when the holder pid is alive AND in the caller's ancestry.
    lease.acquire(tmp_path, "ctxd", "harness_sid", "v1", "IMPLEMENTATION", pid=5000)
    ancestry = lambda h, c: (h, c) == (5000, 6000)  # noqa: E731
    holder2 = lease.release_context_if_caller_owned(
        tmp_path, "ctxd", caller_pid=6000, pid_probe=_ALIVE, ancestry=ancestry
    )
    assert holder2 == "harness_sid"
    assert lease.read_record(tmp_path, "ctxd") is None

    # DP-3 invariant: an unbound holder with no session record still renews (no
    # absence-based renewal guard exists).
    lease.acquire(tmp_path, "ctxe", "harness_sid2", "v1", "IMPLEMENTATION", pid=4321)
    assert lease.renew_heartbeat(tmp_path, "ctxe", "harness_sid2") is True
