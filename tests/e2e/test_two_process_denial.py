"""T-016-07: e2e two-process lease denial (AC-07).

Two real subprocesses target the same context in a tmp_path workspace. Process A
acquires the lease; process B (a different session) is denied and receives the
``dadaia lock steal`` unblock message, exiting non-zero. A's record is unchanged.
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

_ATTEMPT_B = """
import sys
from pathlib import Path
from dadaia_workspace.core.exceptions import LockHeldError
from dadaia_workspace.features.spec_context import lease
ws, ctx = Path(sys.argv[1]), sys.argv[2]
try:
    lease.acquire(ws, ctx, "sessB", "v1", "IMPLEMENTATION")
except LockHeldError as exc:
    print(str(exc))
    sys.exit(1)
print("UNEXPECTED-ACQUIRED")
sys.exit(0)
"""


def test_two_process_denial(tmp_path: Path) -> None:
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

    rec_before = json.loads(
        (tmp_path / ".dadaia/states/ctx_locks" / f"{ctx}.lock.json").read_text()
    )

    proc_b = subprocess.run(
        [sys.executable, "-c", _ATTEMPT_B, str(tmp_path), ctx],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = proc_b.stdout + proc_b.stderr
    assert proc_b.returncode != 0, f"B should be denied; got rc=0, out={output!r}"
    assert "dadaia lock steal" in output, output

    # A's lease record is unchanged by B's denied attempt.
    rec_after = json.loads((tmp_path / ".dadaia/states/ctx_locks" / f"{ctx}.lock.json").read_text())
    assert rec_after["session_id"] == rec_before["session_id"] == "sessA"
