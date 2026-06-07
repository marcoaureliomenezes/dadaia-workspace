"""T-016-12: e2e two-process lease — exactly-one-mutating, without ever freezing.

Two real subprocesses target the same context in a tmp_path workspace.

* Process A acquires the lease (the legitimate mutating session).
* Process B is a *genuinely different* concurrent session (no ``.ptr`` match). Under
  the restored exactly-one-mutating invariant (D1 / constitution §8), B MUST NOT
  mutate — ``acquire`` yields with an informative ``LockHeldError``.

This is NOT the freeze the operator forbade: the freeze came from a session being
blocked by *its own* relaunched/abandoned lease (session-id instability). The stable
``.ptr`` identity makes a relaunch RENEW (see ``test_short_heartbeat_triad``), so the
single operator never blocks themselves. A live foreign lease here is a real second
session, and yielding is correct. Crucially, the yield message contains NO manual
unblock ceremony — no ``bind --mode write``, ``relaunch``, or ``lock steal`` — because
reclaim-iff-stale frees a finished/dead holder automatically after the heartbeat window.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

_ACQUIRE_A = """
import sys
from pathlib import Path
from dadaia_workspace.features.spec_context import lease
ws, ctx, ready = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
lease.acquire(ws, ctx, "sessA", "v1", "IMPLEMENTATION")
ready.write_text("ready")  # rendezvous: signal B that the lease is held
"""

# B is a genuinely different session (its own session_id, no .ptr for it). It must be
# denied the MUTATING lease via LockHeldError, and must NOT take the lease over.
_ATTEMPT_B = """
import sys
from pathlib import Path
from dadaia_workspace.features.spec_context import lease
from dadaia_workspace.core.exceptions import LockHeldError
ws, ctx = Path(sys.argv[1]), sys.argv[2]
try:
    status, rec = lease.acquire(ws, ctx, "sessB", "v1", "IMPLEMENTATION")
except LockHeldError as exc:
    print("YIELDED")
    print(str(exc))
    sys.exit(0)
# Reaching here means B mutated concurrently — the invariant is broken.
print("ACQUIRED-WRONGLY", status)
sys.exit(2)
"""


def test_two_process_genuine_concurrent_session_yields(tmp_path: Path) -> None:
    ctx = "e2eproc"
    ready = tmp_path / "ready.flag"

    proc_a = subprocess.run(
        [sys.executable, "-c", _ACQUIRE_A, str(tmp_path), ctx, str(ready)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc_a.returncode == 0, proc_a.stderr

    # File-based rendezvous: wait until A has signalled (deterministic, no CPU spin).
    for _ in range(100):
        if ready.exists():
            break
        time.sleep(0.01)
    assert ready.exists(), "process A never signalled lease acquisition"

    proc_b = subprocess.run(
        [sys.executable, "-c", _ATTEMPT_B, str(tmp_path), ctx],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = proc_b.stdout + proc_b.stderr

    # B yields (exactly-one-mutating restored); it does NOT take the lease over.
    assert proc_b.returncode == 0, f"B should yield cleanly; out={output!r}"
    assert "YIELDED" in proc_b.stdout, output
    assert "ACQUIRED-WRONGLY" not in proc_b.stdout, output

    # Forbidden-law: the yield message instructs NO manual unblock ceremony.
    lowered = output.lower()
    for forbidden in ("bind --mode write", "relaunch", "lock steal"):
        assert forbidden not in lowered, f"yield message must not mention {forbidden!r}; out={output!r}"
    # It is informative: additive writes still allowed + auto-reclaim explained.
    assert "additive" in lowered
    assert "auto-reclaim" in lowered or "automatically" in lowered

    # The lease record is STILL owned by A — B never mutated it.
    rec_after = json.loads((tmp_path / ".dadaia/states/ctx_locks" / f"{ctx}.lock.json").read_text())
    assert rec_after["session_id"] == "sessA"
