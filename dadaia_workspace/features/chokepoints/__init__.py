"""Chokepoint enforcement (W1, v0.1.14): harness-independent git-hook gates.

The SDD gate (``hooks/sdd_gate``) fires for *file-write tools* inside a harness that
supports PreToolUse hooks. Chokepoints provide a separate boundary for any invocation
where hooks are absent, disabled, bypassed, or changed by a future harness release:

* **pre-commit presence check** (:func:`pre_commit_decision`) — warns when another live
  session is present and always allows the commit on concurrency grounds.
* **push-gate verdict check** (:func:`push_gate_decision`, FR-W1-02 / DP-5) — a push is
  blocked unless a ``security-reviewer`` APPROVE handoff covers every pushed commit sha.

Both are pure decision functions: every I/O and process seam is injected, so the CLI wires
the real container adapters and the tests drive synthetic facts. Zero subprocess, zero
``os.kill`` — the ancestry probe is the injected read-only ``ProcessAncestry`` port.
"""

from __future__ import annotations

from dadaia_workspace.features.chokepoints.service import (
    Decision,
    PushRef,
    context_slug_for_path,
    iter_security_approvals,
    pre_commit_decision,
    push_gate_decision,
)

__all__ = [
    "Decision",
    "PushRef",
    "context_slug_for_path",
    "iter_security_approvals",
    "pre_commit_decision",
    "push_gate_decision",
]
