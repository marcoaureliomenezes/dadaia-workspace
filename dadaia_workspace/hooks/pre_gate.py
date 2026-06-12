"""Merged PreToolUse entrypoint (FR-W4-01, T-014-03).

A single hook the harness invokes as ``python -m dadaia_workspace.hooks.pre_gate``. It
reads the stdin JSON envelope **once**, then evaluates the registered PreToolUse policies
in a fixed order, first-block-wins:

    1. root-whitelist  (``root_whitelist.evaluate_payload``)
    2. venv-guard slot (wired in TG-4 — :func:`_venv_guard_reason`, a no-op until then)
    3. SDD gate        (``sdd_gate.evaluate_payload``)

Allow requires every policy to allow; the first policy that returns a block reason
short-circuits and that reason is emitted via the ``{"decision":"block",...}`` envelope.
The legacy ``sdd_gate.main`` / ``root_whitelist.main`` entrypoints are retained one release
for back-compat wiring; their pure ``evaluate_payload`` policy surfaces are reused here so
there is no third drifting copy of the gate logic.

Parity invariants preserved verbatim from the standalone gates:
- NotebookEdit is gated by the SDD gate but NOT by the root-whitelist policy (the policy
  modules own that distinction; ``pre_gate`` adds no tool filtering of its own).
- PROTECTED (``.dadaia/sessions/``) stays the sole fail-CLOSED path (inside the SDD policy).
- Fail-open posture: any policy that cannot attribute a write allows it; the entrypoint
  never deadlocks. A policy raising is caught and treated as ALLOW.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

from dadaia_workspace.hooks import _common, root_whitelist, sdd_gate, venv_guard


def _venv_guard_reason(payload: dict[str, object]) -> str | None:
    """Venv-guard policy slot (FR-W3-01, T-014-12).

    Delegates to :func:`dadaia_workspace.hooks.venv_guard.evaluate_payload` — a narrow
    Bash-only check that blocks ``dadaia`` / ``pip`` / ``python -m dadaia_workspace``
    invocations not rooted in ``.dadaia/.venv/bin/`` (ADR-G4). The evaluation order
    (root-whitelist → venv-guard → SDD gate) was fixed when the slot was introduced; this
    only fills the body.
    """
    return venv_guard.evaluate_payload(payload)


#: Ordered PreToolUse policies. First block wins; allow requires all.
_POLICIES: tuple[Callable[[dict[str, object]], str | None], ...] = (
    root_whitelist.evaluate_payload,
    _venv_guard_reason,
    sdd_gate.evaluate_payload,
)


def evaluate_payload(payload: dict[str, object]) -> str | None:
    """Run every PreToolUse policy in order; return the first block reason, else ``None``.

    Each policy is fail-open: a policy that raises is caught and treated as ALLOW so a
    single faulty policy can never deadlock the harness.
    """
    for policy in _POLICIES:
        try:
            reason = policy(payload)
        except Exception:  # noqa: BLE001 — fail-open: a policy crash must never block
            reason = None
        if reason is not None:
            return reason
    return None


def _append_latency(workspace: Path | None, event: str, duration_ms: float) -> None:
    """Append one hook-latency record to ``.dadaia/logs/hook-latency.jsonl`` (best-effort).

    FR-W4-06 (T-014-04). Fail-OPEN: an unresolvable workspace, an unwritable/absent logs
    dir, or any OS error is swallowed — telemetry must NEVER change the gate verdict or the
    exit code. ``duration_ms`` is clamped to ``>= 0`` (a monotonic clock never goes backward,
    but the clamp makes the contract explicit for consumers).
    """
    if workspace is None:
        return
    record = {
        "ts": datetime.now(tz=UTC).isoformat(),
        "hook": "pre_gate",
        "event": event,
        "duration_ms": round(max(0.0, duration_ms), 3),
    }
    path = workspace / ".dadaia" / "logs" / "hook-latency.jsonl"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except OSError:
        return


def main() -> int:
    """Run the merged PreToolUse gate. Returns 0 always (block via the stdout envelope).

    The whole invocation is timed (FR-W4-06): after the verdict is emitted, one best-effort
    latency record is appended to ``.dadaia/logs/hook-latency.jsonl``. The telemetry is
    fail-open and never alters the gate decision or the exit code.
    """
    start = time.monotonic()
    payload = _common.read_stdin_json()
    reason = evaluate_payload(payload)
    if reason is not None:
        _common.emit_block(reason)
    duration_ms = (time.monotonic() - start) * 1000.0
    try:
        workspace: Path | None = _resolve_workspace()
    except Exception:  # noqa: BLE001 — telemetry workspace resolution must never block
        workspace = None
    event = os.environ.get("DADAIA_HOOK_EVENT", "PreToolUse")
    _append_latency(workspace, event, duration_ms)
    return 0


def _resolve_workspace() -> Path:
    """Resolve the workspace root for telemetry: ``WORKSPACE_ROOT`` env, else walk up."""
    env = os.environ.get("WORKSPACE_ROOT")
    if env:
        return Path(env)
    from dadaia_workspace.core.workspace_resolver import resolve_workspace_root

    return resolve_workspace_root()


if __name__ == "__main__":
    sys.exit(main())
