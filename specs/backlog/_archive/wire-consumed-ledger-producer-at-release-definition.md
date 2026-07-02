---
name: wire-consumed-ledger-producer-at-release-definition
id: FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01
reported: 2026-06-26
owner: project-manager (curates) -> product-engineer (release definition)
priority: HIGH
status: delivered
delivered_in: v0.1.27
builds_on: backlog-definition-workflow-dedup-conflict-control (R2 residual — the producer half of §6 removal-on-release)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/backlog/removal_lifecycle.py#consume_at_release_definition" }
    change: "invoke this from the real release-definition surface so the consumed_backlog ledger is actually written in production (not only in the integration loop test)"
  - subject: { kind: code, ref: "dadaia_workspace/features/lifecycle/workflows/release_definition.py#ReleaseDefinitionWorkflow" }
    change: "establish how a release declares the backlog items it consumes + their shipped subject-anchor set (e.g. a consumed_backlog field in the release SPEC frontmatter or a terminal release-definition step), then bind+verify those anchors to feed consume_at_release_definition"
  - subject: { kind: code, ref: "dadaia_workspace/features/backlog/removal_lifecycle.py#BacklogRemovalLifecycle" }
    change: "expose the producer (.consume) on the release-definition surface symmetrically with the closure .remove() call already wired into `dadaia lifecycle close`"
---

# Wire the consumed_backlog producer at release-definition (R2 residual)

## Problem
v0.1.26 R2 shipped the full removal-on-release MECHANISM — the R1-shaped ledger
writer (`consume_at_release_definition`), the residual-aware closure hook
(`apply_removal` / `remove_at_closure`), the `BacklogRemovalLifecycle` container
facade, and the closure-side invocation (`dadaia lifecycle close` calls
`lifecycle.remove(...)`). The BL-STALE loop is proven both directions at the
function/integration level (`tests/integration/test_backlog_removal_loop.py`).

**Gap (QA MEDIUM, v0.1.26 alpha-1, 2026-06-26):** the *producer* half is not wired
into the real release-definition surface. Nothing writes `consumed_backlog.json` in
production, so `remove_at_closure` always reads an empty ledger and no-ops — the
loop cannot fire end-to-end on a real release. R2 met all 11 of its own acceptance
criteria (the producer wiring was not among them), but the §6 removal-on-release
feature is operationally inert until this lands.

## Why it was deferred (not invented under-spec)
Deriving the **verified shipped subject-anchor set** at release-definition time is
genuinely underspecified: it requires a convention for how a release *declares*
which backlog items it consumed and which of their bound anchors actually shipped.
Inventing that derivation ad-hoc would have been theater. It needs a deliberate
design decision (release-SPEC `consumed_backlog` field vs a terminal
release-definition step vs operator declaration), then bind+verify through the R1
registry before calling the existing `consume_at_release_definition`.

## Acceptance
1. A real release-definition run writes `specs/_archive/<release-id>/consumed_backlog.json`
   keyed on the verified shipped anchor set — tested end-to-end (not just at the
   function level).
2. After a real define→close cycle, an item fully consumed by the release is removed
   from the live SET (archive copy precedes unlink) and `backlog doctor` reports zero
   BL-STALE — tested end-to-end.
3. The release-declaration convention is documented (memory/architecture or the
   release-definition skill) so an operator/agent knows how to mark consumption.

## Sequence
After v0.1.26 closes; before relying on removal-on-release operationally. Does not
block `workflow-model-governance`.
