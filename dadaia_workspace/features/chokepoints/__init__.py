"""Chokepoint enforcement (W1, v0.1.14): harness-independent git-hook gates.

The SDD gate (``hooks/sdd_gate``) fires for *file-write tools* inside a harness that
supports PreToolUse hooks. Chokepoints provide a separate boundary for any invocation
where hooks are absent, disabled, bypassed, or changed by a future harness release:

* **pre-commit presence check** (:func:`pre_commit_decision`) — warns when another live
  session is present and always allows the commit on concurrency grounds.
* **push-gate branch + denylist check** (:func:`push_gate_decision`, v0.4.4 FR3 — the
  gitflow v2 inversion / v0.9.0 FR1-FR6) — a push is blocked unless it is a
  ``feature/{M.m.p}`` branch pushed to its own name (``develop``/``main`` advance by PR
  only), AND the range-scoped denylist scan (v0.9.0) finds no new object carrying a
  denylisted term across every non-deletion ref (tags included). The former
  security-reviewer-verdict check is DELETED from this path (v0.4.4 A3.4) — it
  relocates to a PR gate (FR4).
* **push-verdict GC** (:func:`gc_consumed_push_verdicts`, FR24 / v0.4.3 T-043-39 /
  v0.4.4 D5) — the POST-merge half of the verdict lifecycle: once a caller has
  independently confirmed a PR merge actually landed (never inside
  ``push_gate_decision`` itself — see that function's neighboring module docstring),
  the APPROVED verdict(s) it consumed are deleted, with an append-only audit-ledger
  line recorded first (A24.4) and the AG.1 symlink/boundary lane guard applied to
  every deletion.

All three are pure decision/action functions: every I/O and process seam is injected, so
the CLI wires the real container adapters and the tests drive synthetic facts. Zero
subprocess, zero ``os.kill`` — the ancestry probe is the injected read-only
``ProcessAncestry`` port, and the push-gate's git object reads arrive via the injected
:class:`~dadaia_workspace.core.protocols.git_object_reader.GitObjectReader` port.
"""

from __future__ import annotations

from dadaia_workspace.features.chokepoints.service import (
    Decision,
    GcOutcome,
    PushRef,
    context_slug_for_path,
    gc_consumed_push_verdicts,
    iter_security_approvals,
    pre_commit_decision,
    push_gate_decision,
)

__all__ = [
    "Decision",
    "GcOutcome",
    "PushRef",
    "context_slug_for_path",
    "gc_consumed_push_verdicts",
    "iter_security_approvals",
    "pre_commit_decision",
    "push_gate_decision",
]
