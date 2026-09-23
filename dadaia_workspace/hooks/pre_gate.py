"""Merged PreToolUse entrypoint (FR-W4-01, T-014-03).

A single hook the harness invokes as ``python -m dadaia_workspace.hooks.pre_gate``. It
reads the stdin JSON envelope **once**, then evaluates the registered PreToolUse policies
in a fixed order, first-block-wins:

    1. root-whitelist  (``root_whitelist.evaluate_payload``)
    2. venv-guard slot (wired in TG-4 — :func:`_venv_guard_reason`, a no-op until then)
    3. SDD gate        (``sdd_gate.evaluate_payload``)

Allow requires every policy to allow; the first policy that returns a block reason
short-circuits and that reason is emitted via the ``{"decision":"block",...}`` envelope.
``pre_gate`` is the single hook entrypoint; the standalone ``sdd_gate.main`` /
``root_whitelist.main`` CLI entrypoints (one-release deprecation from v0.1.14) were
removed in v0.1.53. Their pure ``evaluate_payload`` policy surfaces are reused here so
there is no third drifting copy of the gate logic.

Parity invariants preserved verbatim from the standalone gates:
- NotebookEdit is gated by the SDD gate but NOT by the root-whitelist policy (the policy
  modules own that distinction; ``pre_gate`` adds no tool filtering of its own).
- PROTECTED (``.dadaia/sessions/``) stays the sole fail-CLOSED path (inside the SDD policy).
- Fail-open posture: any policy that cannot attribute a write allows it; the entrypoint
  never deadlocks. A policy raising is caught and treated as ALLOW.
"""

from __future__ import annotations

import sys
from collections.abc import Callable

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
            block = policy(payload)
        except Exception:  # noqa: BLE001 — fail-open: a policy crash must never block
            block = None
        if block is not None:
            return block
    return None


def main() -> int:
    """Run the merged PreToolUse gate. Returns 0 always (block via the stdout envelope)."""
    reason = evaluate_payload(_common.read_stdin_json())
    if reason is not None:
        _common.emit_block(reason)
    else:
        _common.emit_allow()
    return 0


if __name__ == "__main__":
    sys.exit(main())
