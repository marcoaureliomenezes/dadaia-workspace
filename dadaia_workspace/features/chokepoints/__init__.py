"""Chokepoint enforcement (W1, v0.1.14): harness-independent git-hook gates.

The SDD gate (``hooks/sdd_gate``) fires for *file-write tools* inside a harness that
supports PreToolUse hooks. Chokepoints provide a separate boundary for any invocation
where hooks are absent, disabled, bypassed, or changed by a future harness release.

The package holds three modules:

* :mod:`~dadaia_workspace.features.chokepoints.branch_policy` — the gitflow v2 branch
  contract, :class:`Decision` (shared outcome shape) and :class:`PushRef`.
* :mod:`~dadaia_workspace.features.chokepoints.push_gate` — branch policy + specs-canon
  scan + range-scoped denylist scan (:func:`push_gate_decision`).
* :mod:`~dadaia_workspace.features.chokepoints.denylist_scan` — the denylist scanner.

All decision/action functions are pure: every I/O and process seam is injected, so the
CLI wires the real container adapters and the tests drive synthetic facts. Zero
subprocess, zero ``os.kill`` — the push-gate's git object reads arrive via the injected
:class:`~dadaia_workspace.core.protocols.git_object_reader.GitObjectReader` port,
and its specs-canon predicates arrive via the injected
``canon_violations_fn`` callable, which this package never
imports at module scope.
"""

from __future__ import annotations

from dadaia_workspace.features.chokepoints.branch_policy import (
    Decision,
    PushRef,
    branch_name_is_permitted,
    parse_push_refs,
    parse_push_stdin,
)
from dadaia_workspace.features.chokepoints.push_gate import push_gate_decision

__all__ = [
    "Decision",
    "PushRef",
    "branch_name_is_permitted",
    "parse_push_refs",
    "parse_push_stdin",
    "push_gate_decision",
]
