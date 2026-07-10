"""T-010-06 / WS-R2 FR-R2-05 / AC-R2-04: two-actor concurrency e2e — no-steal invariant.

This is the falsifying end-to-end test for the whole concurrency kernel (T-010-03 re-root,
T-010-04 heartbeat, T-010-05 pid-liveness). It generalizes ``test_two_process_denial.py``
from one denial scenario into the four AC-R2-04 invariants, and — crucially — proves them
with **real OS processes** whose PIDs are genuinely alive (or genuinely dead), so the
pid-liveness veto is exercised against the real platform-seamed probe, not a fake.

Every scenario:

* spawns actual ``python`` subprocesses that drive the **real** lease / gate surfaces;
* uses **file rendezvous** (``tests/e2e/lease_rendezvous.py``) — every wait has a bounded
  deadline, never an infinite poll, never a blind ``time.sleep`` of the whole duration;
* injects a **short TTL** (``SHORT_TTL_SECONDS``) so a holder can go BUSY *past* TTL while
  its PID stays alive, instead of sleeping the real 120 s;
* asserts the invariants on the **lock-file history** (``LockJournal``), not on subprocess
  return values.

The scenarios (AC-R2-04 (i)-(iv)):

(i)   HOLDER-BUSY NO-STEAL / ADDITIVE — holder A busy past TTL (pid alive); foreign B does
      an in-repo ``specs/bugs`` ADDITIVE write through the real ``sdd_gate`` subprocess ⇒
      ALLOW, and **no** captured lock version ever names B.
(ii)  HOLDER-BUSY NO-STEAL / MUTATING — same holder busy past TTL; foreign B attempts a
      MUTATING acquire wired with the real ``OsProcessProbe`` ⇒ BLOCKED while A's pid is
      alive; the lock history never names B.
(iii) DISJOINT CONTEXTS — two holders mutate two *different* context repos concurrently ⇒
      no cross-block (regression for gate-cross-context-lock-contamination).
(iv)  DEAD-HOLDER TAKEOVER — holder A acquires then its process **really exits**; foreign B
      MUTATING acquire ⇒ TAKEOVER succeeds (history shows A, then B).

Platform: the pid probe is the platform-seamed ``OsProcessProbe`` (``os.kill(pid, 0)`` on
POSIX, ``OpenProcess`` on Windows). These tests are green on POSIX and run on the
Windows/macOS CI legs unchanged — no Linux-only acceptance, no platform skips.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from dadaia_workspace.core import kernel_tunables
from dadaia_workspace.features.spec_context import lease
from tests.e2e.lease_rendezvous import (
    SHORT_TTL_SECONDS,
    LockJournal,
    read_lock_record,
    wait_for_file,
    wait_until,
)
from tests.fixtures.harness_env import claude_hook_env, run_hook_subprocess

pytestmark = pytest.mark.e2e

_SLUG = "dadaia-workspace"
_OTHER_SLUG = "other-context"

#: Generous bounded deadlines (seconds). Far larger than the work they gate, so a healthy
#: machine never flakes, yet a genuinely hung child fails the test instead of the suite.
_READY_DEADLINE = 30.0
_STALE_DEADLINE = SHORT_TTL_SECONDS + 30.0
_EXIT_DEADLINE = 30.0


# --------------------------------------------------------------------------------------
# Real-process runner programs (spawned with ``python -c``). Each drives the REAL lease
# wired with the REAL platform-seamed pid probe — exactly the way ``hooks/sdd_gate`` wires
# it — so the no-steal veto is exercised against a genuinely alive/dead PID.
# --------------------------------------------------------------------------------------

#: Holder A: acquire with a short TTL, signal ``ready``, then stay genuinely BUSY (pid
#: alive) until ``stop`` appears. The busy-wait is itself bounded so a leaked child can
#: never hang the CI host. The holder writes its own pid to ``pidfile`` for the test.
_HOLDER = textwrap.dedent(
    """
    import os, sys, time
    from pathlib import Path
    from dadaia_workspace.features.spec_context import lease

    ws, ctx, sid, ttl = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4])
    ready, stop, pidfile = Path(sys.argv[5]), Path(sys.argv[6]), Path(sys.argv[7])

    status, _rec = lease.acquire(ws, ctx, sid, "v0.1.10", "IMPLEMENTATION", ttl=ttl)
    pidfile.write_text(str(os.getpid()))
    ready.write_text(status)  # rendezvous: lease is held and pid recorded

    # Stay alive (pid probe must see us alive) until told to stop. Bounded so a leaked
    # child self-terminates instead of hanging the host. No heartbeat renewal happens
    # here, so the record ages past the short TTL while this process is demonstrably alive.
    deadline = time.monotonic() + 120.0
    while not stop.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    """
)

#: Foreign MUTATING actor: attempt to acquire the SAME context's lease, wired with the
#: real ``OsProcessProbe`` (the hook's exact probe). Prints YIELDED on LockHeldError,
#: ACQUIRED/TAKEOVER on success. Exit code mirrors the outcome for belt-and-suspenders.
_FOREIGN_MUTATING = textwrap.dedent(
    """
    import sys
    from pathlib import Path
    from dadaia_workspace.features.spec_context import lease
    from dadaia_workspace.core.exceptions import LockHeldError
    from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

    ws, ctx, sid = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    probe = OsProcessProbe()
    try:
        status, _rec = lease.acquire(
            ws, ctx, sid, "v0.1.10", "IMPLEMENTATION",
            pid_probe=lambda pid: probe.is_pid_alive(pid),
        )
    except LockHeldError as exc:
        print("YIELDED")
        print(str(exc))
        sys.exit(0)
    print(status)
    sys.exit(0)
    """
)


def _python(*args: str, timeout: float, code: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _spawn(*args: str, code: str) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", code, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _make_workspace(tmp_path: Path, *slugs: str) -> Path:
    """Throwaway workspace: a repo + approved IMPLEMENTATION ACTIVE.md per slug.

    Never touches the live workspace — everything is under ``tmp_path``.
    """
    (tmp_path / ".dadaia" / "states").mkdir(parents=True, exist_ok=True)
    for slug in slugs:
        rel = tmp_path / "repos" / slug / "specs" / "releases"
        rel.mkdir(parents=True, exist_ok=True)
        (rel / "ACTIVE.md").write_text(
            "release: v0.1.10\nphase: IMPLEMENTATION\n", encoding="utf-8"
        )
        (tmp_path / "repos" / slug / "specs" / "bugs").mkdir(parents=True, exist_ok=True)
        (rel / "v0.1.10").mkdir(parents=True, exist_ok=True)
    return tmp_path


def _start_holder(
    ws: Path, ctx: str, sid: str, paths: dict[str, Path], *, ttl: int = SHORT_TTL_SECONDS
) -> subprocess.Popen[str]:
    """Spawn holder A and block until it has signalled the lease is held."""
    proc = _spawn(
        str(ws),
        ctx,
        sid,
        str(ttl),
        str(paths["ready"]),
        str(paths["stop"]),
        str(paths["pid"]),
        code=_HOLDER,
    )
    wait_for_file(paths["ready"], deadline_s=_READY_DEADLINE, what=f"holder {sid} to acquire")
    assert paths["ready"].read_text().strip() in {"ACQUIRED", "RENEWED"}
    return proc


def _stop_holder(proc: subprocess.Popen[str], stop: Path) -> None:
    stop.write_text("stop")
    try:
        proc.wait(timeout=_EXIT_DEADLINE)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=_EXIT_DEADLINE)
        raise AssertionError("holder process did not exit after stop signal") from None


def _wait_ttl_stale(ws: Path, ctx: str) -> None:
    """Block (bounded) until the holder's heartbeat has aged past the short TTL.

    Purely clock-based: we read the record's heartbeat and compare elapsed wall-clock
    against its ``ttl``. No fixed sleep of the whole duration — we poll the *condition*.
    """
    from datetime import UTC, datetime

    def _stale() -> bool:
        rec = read_lock_record(ws, ctx)
        if rec is None:
            return False
        hb = rec.get("heartbeat")
        ttl = rec.get("ttl")
        if not isinstance(hb, str) or not isinstance(ttl, int):
            return False
        hb_dt = datetime.fromisoformat(hb.replace("Z", "+00:00"))
        if hb_dt.tzinfo is None:
            hb_dt = hb_dt.replace(tzinfo=UTC)
        return (datetime.now(tz=UTC) - hb_dt).total_seconds() >= ttl

    wait_until(_stale, deadline_s=_STALE_DEADLINE, what="holder heartbeat to age past TTL")


# --------------------------------------------------------------------------------------
# (i) HOLDER-BUSY NO-STEAL — foreign ADDITIVE in-repo write ALLOWED, never named in lock.
# --------------------------------------------------------------------------------------
def test_holder_busy_foreign_additive_allowed_and_never_named(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    holder, foreign = "session-A-holder", "session-B-foreign"
    journal = LockJournal(ws, _SLUG)
    paths = {
        "ready": tmp_path / "A.ready",
        "stop": tmp_path / "A.stop",
        "pid": tmp_path / "A.pid",
    }

    proc_a = _start_holder(ws, _SLUG, holder, paths)
    try:
        journal.capture()  # version 0: A holds, fresh
        _wait_ttl_stale(ws, _SLUG)  # A is now TTL-stale BUT its pid is alive
        journal.capture()  # version 1: still A (no heartbeat renewal, pid alive)

        # Foreign B writes an in-repo ADDITIVE bug file through the REAL gate subprocess.
        target = ws / "repos" / _SLUG / "specs" / "bugs" / "from-foreign.md"
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": str(target)},
            "session_id": foreign,
        }
        result = run_hook_subprocess("sdd_gate", payload, claude_hook_env(ws, session_id=foreign))
        journal.capture()  # version 2: must STILL be A — ADDITIVE never touches the lock

        assert result.returncode == 0
        assert result.block_envelope() is None, (
            "in-repo specs/bugs write is ADDITIVE → must ALLOW; a block means the re-root regressed"
        )
    finally:
        _stop_holder(proc_a, paths["stop"])

    # INVARIANT on lock-file HISTORY: every captured version names A; B never appears.
    assert journal.holders() == [holder, holder, holder], journal.holders()
    assert not journal.names_session(foreign), (
        "lease-theft regression: a foreign ADDITIVE write must never appear in the lock history"
    )


# --------------------------------------------------------------------------------------
# (ii) HOLDER-BUSY NO-STEAL — foreign MUTATING attempt BLOCKED while holder pid alive.
# --------------------------------------------------------------------------------------
def test_holder_busy_foreign_mutating_blocked_while_pid_alive(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    holder, foreign = "session-A-holder", "session-B-foreign"
    journal = LockJournal(ws, _SLUG)
    paths = {
        "ready": tmp_path / "A.ready",
        "stop": tmp_path / "A.stop",
        "pid": tmp_path / "A.pid",
    }

    proc_a = _start_holder(ws, _SLUG, holder, paths)
    try:
        journal.capture()  # version 0: A holds
        _wait_ttl_stale(ws, _SLUG)  # TTL-stale, but A's pid is alive ⇒ no-steal veto
        journal.capture()  # version 1: still A

        # Foreign B attempts a MUTATING acquire wired with the REAL pid probe.
        proc_b = _python(str(ws), _SLUG, foreign, timeout=_EXIT_DEADLINE, code=_FOREIGN_MUTATING)
        journal.capture()  # version 2: A must still hold — B vetoed by live-pid probe

        out = proc_b.stdout + proc_b.stderr
        assert proc_b.returncode == 0, out
        assert "YIELDED" in proc_b.stdout, out
        assert "ACQUIRED" not in proc_b.stdout and "TAKEOVER" not in proc_b.stdout, out
        # Forbidden-law: the yield message never instructs a manual unblock ceremony.
        lowered = out.lower()
        for forbidden in ("bind --mode write", "relaunch", "lock steal"):
            assert forbidden not in lowered, out
    finally:
        _stop_holder(proc_a, paths["stop"])

    assert journal.holders() == [holder, holder, holder], journal.holders()
    assert not journal.names_session(foreign), (
        "no-steal violated: a live-pid holder's lease was overwritten by a foreign MUTATING actor"
    )


# --------------------------------------------------------------------------------------
# (iii) DISJOINT CONTEXTS — two holders mutate different repos concurrently, no cross-block.
# --------------------------------------------------------------------------------------
def test_disjoint_contexts_no_cross_block(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG, _OTHER_SLUG)
    sid_a, sid_b = "session-ctxA", "session-ctxB"
    journal_a = LockJournal(ws, _SLUG)
    journal_b = LockJournal(ws, _OTHER_SLUG)
    paths_a = {
        "ready": tmp_path / "A.ready",
        "stop": tmp_path / "A.stop",
        "pid": tmp_path / "A.pid",
    }
    paths_b = {
        "ready": tmp_path / "B.ready",
        "stop": tmp_path / "B.stop",
        "pid": tmp_path / "B.pid",
    }

    # Use the full short-TTL-free default TTL so both stay fresh and live concurrently.
    proc_a = _start_holder(ws, _SLUG, sid_a, paths_a, ttl=kernel_tunables.LEASE_TTL_SECONDS)
    proc_b = _start_holder(ws, _OTHER_SLUG, sid_b, paths_b, ttl=kernel_tunables.LEASE_TTL_SECONDS)
    try:
        journal_a.capture()
        journal_b.capture()
    finally:
        _stop_holder(proc_a, paths_a["stop"])
        _stop_holder(proc_b, paths_b["stop"])

    # Each context acquired its OWN lease — neither blocked the other (no cross-context
    # lock contamination). Two distinct lock files, each named by its own holder.
    assert journal_a.holders() == [sid_a]
    assert journal_b.holders() == [sid_b]
    assert not journal_a.names_session(sid_b)
    assert not journal_b.names_session(sid_a)
    # Both holder processes acquired cleanly (a cross-block would have raised LockHeldError
    # inside the holder, killing the ready signal — already asserted by _start_holder).
    rec_a = read_lock_record(ws, _SLUG)
    rec_b = read_lock_record(ws, _OTHER_SLUG)
    assert rec_a is not None and rec_a["session_id"] == sid_a
    assert rec_b is not None and rec_b["session_id"] == sid_b


# --------------------------------------------------------------------------------------
# (iv) DEAD-HOLDER TAKEOVER — holder process really exits, foreign MUTATING acquire wins.
# --------------------------------------------------------------------------------------
def test_dead_holder_takeover(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    holder, foreign = "session-A-dead", "session-B-takeover"
    journal = LockJournal(ws, _SLUG)
    paths = {
        "ready": tmp_path / "A.ready",
        "stop": tmp_path / "A.stop",
        "pid": tmp_path / "A.pid",
    }

    proc_a = _start_holder(ws, _SLUG, holder, paths)
    journal.capture()  # version 0: A holds
    holder_pid = int(paths["pid"].read_text().strip())

    # A's process REALLY exits (dead pid). Then wait — bounded — until the OS has reaped it
    # and the record has aged past the short TTL, so the takeover path's probe sees a dead pid.
    _stop_holder(proc_a, paths["stop"])
    _wait_ttl_stale(ws, _SLUG)
    journal.capture()  # version 1: still A's stale record, but A is dead now

    # Sanity: the holder pid is genuinely gone (so the takeover is justified, not a fluke).
    from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

    wait_until(
        lambda: not OsProcessProbe().is_pid_alive(holder_pid),
        deadline_s=_EXIT_DEADLINE,
        what="holder pid to be reaped",
    )

    # Foreign B MUTATING acquire (real pid probe) ⇒ TAKEOVER succeeds against the dead holder.
    proc_b = _python(str(ws), _SLUG, foreign, timeout=_EXIT_DEADLINE, code=_FOREIGN_MUTATING)
    journal.capture()  # version 2: now B holds — the takeover landed

    out = proc_b.stdout + proc_b.stderr
    assert proc_b.returncode == 0, out
    assert "ACQUIRED" in proc_b.stdout or "TAKEOVER" in proc_b.stdout, out
    assert "YIELDED" not in proc_b.stdout, out

    # INVARIANT on history: A held, then (still A while dead), then B took over.
    assert journal.holders() == [holder, holder, foreign], journal.holders()
    final = read_lock_record(ws, _SLUG)
    assert final is not None and final["session_id"] == foreign
    # The takeover stamped B's real pid into the record (the new live holder).
    assert isinstance(final.get("pid"), int) and final["pid"] != holder_pid


# --------------------------------------------------------------------------------------
# (v) HOOK-ACQUIRED HOLDER NO-STEAL (NF-1, rc-2) — the production process model.
#
# Production never acquires in-process: the holder is the harness, and the lease is acquired
# by the EPHEMERAL ``pre_gate`` hook child the harness spawns. The hook child dies in
# milliseconds; the no-steal pid-veto can only work if the recorded pid is the LONG-LIVED
# harness (``getppid()``), not the dead hook child. This scenario reproduces exactly that:
#
#   * a long-lived DRIVER process (the stand-in harness) spawns the REAL ``pre_gate`` hook as
#     a child, which acquires the lease recording the driver's pid (``getppid()``);
#   * the driver then stays alive (no renewal) until told to stop, so the record ages past the
#     short TTL while the driver pid is demonstrably alive;
#   * a foreign MUTATING acquire (real pid probe) ⇒ BLOCKED while the driver lives;
#   * killing the driver ⇒ a later foreign MUTATING acquire ⇒ TAKEOVER.
#
# This is the falsification the rc-1 e2e lacked (it only had in-process direct-API holders).
# --------------------------------------------------------------------------------------

#: Long-lived DRIVER (stand-in harness): invoke the REAL pre_gate hook (the single merged
#: harness entrypoint since v0.1.53) as a child so the hook records the driver's pid via
#: getppid(), confirm the lease names the driver, then idle until stopped. Bounded so a
#: leaked child self-terminates. Writes its own pid for the test.
_HOOK_DRIVER = textwrap.dedent(
    """
    import json, os, subprocess, sys, time
    from pathlib import Path

    ws, ctx, sid = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    ready, stop, pidfile = Path(sys.argv[4]), Path(sys.argv[5]), Path(sys.argv[6])

    target = ws / "repos" / ctx / "specs" / "releases" / "rel-1" / "TASKS.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}, "session_id": sid}

    env = dict(os.environ)
    env["WORKSPACE_ROOT"] = str(ws)
    env["CLAUDE_CODE_SESSION_ID"] = sid
    for bad in ("DADAIA_SESSION_ID", "DADAIA_MODE", "CODEX_SESSION_ID"):
        env.pop(bad, None)

    # Spawn the REAL gate hook as a CHILD of this driver. The hook records getppid() == this
    # driver's pid, then exits. This is the production topology (harness spawns ephemeral hook).
    proc = subprocess.run(
        [sys.executable, "-m", "dadaia_workspace.hooks.pre_gate"],
        input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=30,
    )
    pidfile.write_text(str(os.getpid()))
    ready.write_text("OK" if not proc.stdout.strip() else "BLOCKED:" + proc.stdout)

    # Stay alive (pid probe must see THIS driver alive) until told to stop. No renewal happens,
    # so the record ages past the short TTL while this driver is demonstrably alive.
    deadline = time.monotonic() + 120.0
    while not stop.exists() and time.monotonic() < deadline:
        time.sleep(0.02)
    """
)


def _start_hook_driver(
    ws: Path, ctx: str, sid: str, paths: dict[str, Path]
) -> subprocess.Popen[str]:
    """Spawn the long-lived hook-driver and block until it has acquired via the real hook."""
    proc = _spawn(
        str(ws),
        ctx,
        sid,
        str(paths["ready"]),
        str(paths["stop"]),
        str(paths["pid"]),
        code=_HOOK_DRIVER,
    )
    wait_for_file(paths["ready"], deadline_s=_READY_DEADLINE, what=f"hook-driver {sid} to acquire")
    assert paths["ready"].read_text().strip() == "OK", paths["ready"].read_text()
    return proc


def _set_short_ttl_on_record(ws: Path, ctx: str, ttl: int) -> None:
    """Shrink the live record's TTL in place so it can age out fast (no 120 s real sleep).

    The hook always acquires with the default 120 s TTL (the gate has no short-TTL seam), so
    we rewrite ``ttl`` on the on-disk record post-acquire. This is a test-only accelerant on a
    record the real hook genuinely wrote — the holder pid, session id, and heartbeat are the
    hook's real values; only the staleness clock is compressed.
    """
    rec = read_lock_record(ws, ctx)
    assert rec is not None
    rec["ttl"] = ttl
    lease._record_path(ws, ctx).write_text(json.dumps(rec), encoding="utf-8")


def test_hook_acquired_holder_no_steal_while_driver_alive_then_takeover(tmp_path: Path) -> None:
    ws = _make_workspace(tmp_path, _SLUG)
    holder, foreign = "driver-A-holder", "session-B-foreign"
    journal = LockJournal(ws, _SLUG)
    paths = {
        "ready": tmp_path / "A.ready",
        "stop": tmp_path / "A.stop",
        "pid": tmp_path / "A.pid",
    }

    proc_a = _start_hook_driver(ws, _SLUG, holder, paths)
    driver_pid = int(paths["pid"].read_text().strip())
    try:
        rec0 = journal.capture()  # version 0: A holds, acquired via the real hook
        assert rec0 is not None
        # NF-1 core assertion: the lease records the LONG-LIVED driver pid (getppid in the
        # hook), NOT the ephemeral hook child's pid. Without the fix this is the dead hook pid.
        assert rec0["pid"] == driver_pid, rec0
        assert rec0["session_id"] == holder

        _set_short_ttl_on_record(ws, _SLUG, SHORT_TTL_SECONDS)
        _wait_ttl_stale(ws, _SLUG)  # TTL-stale, but the DRIVER pid is alive ⇒ no-steal veto
        journal.capture()  # version 1: still A

        # Foreign B attempts a MUTATING acquire wired with the REAL pid probe. The probe sees
        # the driver pid alive ⇒ B must be vetoed (this is what was inert before NF-1).
        proc_b = _python(str(ws), _SLUG, foreign, timeout=_EXIT_DEADLINE, code=_FOREIGN_MUTATING)
        journal.capture()  # version 2: A must STILL hold — B vetoed by the live driver pid
        out_b = proc_b.stdout + proc_b.stderr
        assert proc_b.returncode == 0, out_b
        assert "YIELDED" in proc_b.stdout, out_b
        assert "ACQUIRED" not in proc_b.stdout and "TAKEOVER" not in proc_b.stdout, out_b
    finally:
        _stop_holder(proc_a, paths["stop"])

    # Driver A is now dead. Confirm the OS reaped it, then a foreign MUTATING acquire TAKEOVERs.
    from dadaia_workspace.infrastructure.process_probe_adapter import OsProcessProbe

    wait_until(
        lambda: not OsProcessProbe().is_pid_alive(driver_pid),
        deadline_s=_EXIT_DEADLINE,
        what="driver pid to be reaped",
    )
    proc_c = _python(str(ws), _SLUG, foreign, timeout=_EXIT_DEADLINE, code=_FOREIGN_MUTATING)
    journal.capture()  # version 3: now B took over the dead driver's stale lease
    out_c = proc_c.stdout + proc_c.stderr
    assert proc_c.returncode == 0, out_c
    assert "ACQUIRED" in proc_c.stdout or "TAKEOVER" in proc_c.stdout, out_c

    # HISTORY: A (hook-acquired), A (stale-but-alive), A (B vetoed), B (takeover after death).
    assert journal.holders() == [holder, holder, holder, foreign], journal.holders()
    # No-steal held while the driver lived: B never appears until A is dead.
    assert journal.versions[2] is not None and journal.versions[2]["session_id"] == holder
