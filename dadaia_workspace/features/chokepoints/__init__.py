"""Chokepoint enforcement (W1, v0.1.14): harness-independent git-hook gates.

The SDD gate (``hooks/sdd_gate``) fires for *file-write tools* inside a harness that
supports PreToolUse hooks. Chokepoints provide a separate boundary for any invocation
where hooks are absent, disabled, bypassed, or changed by a future harness release.

v0.5.1 K7 ("split chokepoints.service into its four modules; one verdict store") split
the former single ``service.py`` (~1,042 LOC gluing four concerns) into:

* :mod:`~dadaia_workspace.features.chokepoints.branch_policy` — the gitflow v2 branch
  contract, :class:`Decision` (shared outcome shape) and :class:`PushRef`.
* :mod:`~dadaia_workspace.features.chokepoints.pre_commit` — the NO-LOCKS presence
  advisory (:func:`pre_commit_decision`).
* :mod:`~dadaia_workspace.features.chokepoints.push_gate` — branch policy + specs-canon
  scan + range-scoped denylist scan (:func:`push_gate_decision`).
* :mod:`~dadaia_workspace.features.chokepoints.verdict` — the ONE verdict store
  (:func:`covering_verdict`), reading the COMMITTED ``specs/releases/**/verdicts/``
  evidence — never ``.dadaia/handoff/``, which is no longer a verdict source at all.

The former push-verdict GC lifecycle (``iter_security_approvals``,
``gc_consumed_push_verdicts``, ``dadaia ci gc-push-verdicts``) is DELETED outright: it
served the ``.dadaia/handoff/`` store, which no verdict reader consults any more.

All decision/action functions are pure: every I/O and process seam is injected, so the
CLI wires the real container adapters and the tests drive synthetic facts. Zero
subprocess, zero ``os.kill`` — the push-gate's git object reads arrive via the injected
:class:`~dadaia_workspace.core.protocols.git_object_reader.GitObjectReader` port, the
pre-commit presence read arrives via the injected ``others_alive`` callable, and the
push-gate's specs-canon predicates arrive via the injected
``canon_violations_fn``/``verdict_violations_fn`` callables — none of which this
package imports at module scope any more (v0.5.1 K7 drops the
``chokepoints -> spec_context.presence`` and ``chokepoints -> specs.canon``
import-linter suppressions entirely, alongside ``chokepoints ->
infrastructure.jsonl_log_rotation``, deleted with the GC lane).
"""

from __future__ import annotations

from dadaia_workspace.features.chokepoints.branch_policy import (
    Decision,
    PushRef,
    branch_name_is_permitted,
    context_slug_for_path,
    parse_push_refs,
    parse_push_stdin,
)
from dadaia_workspace.features.chokepoints.pre_commit import (
    bundled_ledger_advisory,
    pre_commit_decision,
)
from dadaia_workspace.features.chokepoints.push_gate import push_gate_decision
from dadaia_workspace.features.chokepoints.verdict import Verdict, covering_verdict

__all__ = [
    "Decision",
    "PushRef",
    "Verdict",
    "branch_name_is_permitted",
    "bundled_ledger_advisory",
    "context_slug_for_path",
    "covering_verdict",
    "parse_push_refs",
    "parse_push_stdin",
    "pre_commit_decision",
    "push_gate_decision",
]
