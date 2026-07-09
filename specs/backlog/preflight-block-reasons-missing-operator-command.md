---
name: preflight-block-reasons-missing-operator-command
status: candidate
opened: 2026-07-09
owner: project-manager (curates)
source: "v0.1.69 code-review MEDIUM — pre-existing preflight _check_* block reasons carry operator_command:null; FR3 made them reachable in production for the first time"
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/service.py#LifecyclePreflightService" }
    change: "give each blocking preflight check a non-null, actionable operator_command. Six pre-existing block reasons in the _check_* methods (wrong bound context, wrong bound release, active release mismatch, active release phase mismatch, lease mode mismatch, live foreign lease holder) return operator_command=None. Before v0.1.69 FR3 these were unreachable (the unresolved_runtime_preflight stub always fired first); now that build_lifecycle_preflight_input feeds the real service.preflight, they surface to operators. AC3.3 of v0.1.69 wants every blocked preflight to carry a specific, non-null operator_command; the 'unbound' path already does. Fill the remaining six with the exact remediation command (e.g. `dadaia context bind <ctx> --mode <mode> --release <rel>` for binding/mode mismatches, `git ...`/`dadaia lifecycle ...` for the others). Add an executed-path test asserting each blocked reason carries a non-null operator_command."
---

# BACKLOG — Fill non-null `operator_command` on the six preflight block reasons

**Priority:** MEDIUM. v0.1.69 FR3 built the preflight-input probe assembly and wired
`service.preflight`, retiring the inert stub. AC3.1's core contract (never emit the
generic stub string) is met and tested. But six pre-existing block reasons in
`LifecyclePreflightService._check_*` still return `operator_command: null`; FR3 makes
them reachable in production for the first time. AC3.3's "non-null `operator_command`"
clause is proven only for the `unbound` path.

**Why not folded into v0.1.69:** this logic predates the release (confirmed via
`git show main:...features/lifecycle/service.py`); v0.1.69's picked bug
(`lifecycle-preflight-unusable-resolved-runtime-inputs`) is fixed — preflight is a real
diagnostic that returns specific reasons, never the stub. Filling each of the six with a
correct remediation command is a bounded polish task better done as a tracked follow-up
than bundled into a validated release. Routed here per `release-governance` (never
silently dropped), mirroring the v0.1.68 non-blocking-finding precedent.

**Acceptance sketch:** each of the six blocking `_check_*` reasons carries a non-null,
correct `operator_command`; an executed-path test drives each block path and asserts
`operator_command is not None` with the expected remediation verb.
