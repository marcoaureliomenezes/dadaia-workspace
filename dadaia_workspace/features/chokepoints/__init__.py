"""Chokepoint enforcement (W1, v0.1.14): harness-independent git-hook gates.

The SDD gate (``hooks/sdd_gate``) only fires for *file-write tools* inside a harness that
supports PreToolUse hooks — ``codex exec`` headless and any non-hooked runtime slip through
(bug ``codex-exec-hooks-do-not-fire-headless``). The chokepoints close that gap at the two
git boundaries every workflow must cross:

* **pre-commit lease gate** (:func:`pre_commit_decision`, FR-W1-01 / DP-4) — a commit into a
  Spec Context repo from a session that does NOT hold the context's MUTATING lease is
  blocked; the holder's own commits flow; commits while no lease exists flow
  (zero-false-block).
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
