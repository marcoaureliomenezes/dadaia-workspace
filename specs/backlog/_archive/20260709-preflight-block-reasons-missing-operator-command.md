---
name: preflight-block-reasons-missing-operator-command
status: superseded
superseded_by: lifecycle-pipeline-correctness-and-diagnosability (consolidation 2026-07-10)
opened: 2026-07-09
owner: project-manager (curates)
source: "v0.1.69 code-review MEDIUM — pre-existing preflight _check_* block reasons carry operator_command:null; FR3 made them reachable in production for the first time"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/service.py#LifecyclePreflightService" }
    change: "give each blocking preflight check a non-null, actionable operator_command. Seven block sites return operator_command=None (grill-verified at HEAD, service.py): wrong bound context (:310), wrong bound release (:312), active release mismatch (:326), active release phase mismatch (:328), lease mode mismatch (:366), live foreign lease holder (:368), and required handoff gate failed (:416). Before v0.1.69 FR3 these were unreachable (the unresolved_runtime_preflight stub always fired first); now that build_lifecycle_preflight_input feeds the real service.preflight, they surface to operators. AC3.3 of v0.1.69 wants every blocked preflight to carry a specific, non-null operator_command; the 'unbound' path already does. Fill the remaining seven with the exact remediation command (e.g. `dadaia context bind <ctx> --mode <mode> --release <rel>` for binding/mode mismatches, `git ...`/`dadaia lifecycle ...` for the others). Add an executed-path test asserting each blocked reason carries a non-null operator_command."
---

# BACKLOG — Fill non-null `operator_command` on the seven preflight block reasons

**Priority:** MEDIUM. v0.1.69 FR3 built the preflight-input probe assembly and wired
`service.preflight`, retiring the inert stub. AC3.1's core contract (never emit the
generic stub string) is met and tested. But seven pre-existing block reasons (including `required handoff gate failed`, service.py:416) in
`LifecyclePreflightService._check_*` still return `operator_command: null`; FR3 makes
them reachable in production for the first time. AC3.3's "non-null `operator_command`"
clause is proven only for the `unbound` path.

**Why not folded into v0.1.69:** this logic predates the release (confirmed via
`git show main:...features/lifecycle/service.py`); v0.1.69's picked bug
(`lifecycle-preflight-unusable-resolved-runtime-inputs`) is fixed — preflight is a real
diagnostic that returns specific reasons, never the stub. Filling each of the seven with a
correct remediation command is a bounded polish task better done as a tracked follow-up
than bundled into a validated release. Routed here per `release-governance` (never
silently dropped), mirroring the v0.1.68 non-blocking-finding precedent.

**Acceptance sketch:** each of the seven blocking reasons (six `_check_*` sites + the `_check_handoffs` gate-failed site) carries a non-null,
correct `operator_command`; an executed-path test drives each block path and asserts
`operator_command is not None` with the expected remediation verb.
