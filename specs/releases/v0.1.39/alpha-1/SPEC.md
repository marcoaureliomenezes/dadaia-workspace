# SPEC: v0.1.39 alpha-1 - SDD governance v2 taxonomy and workflow scope repair

**Status:** Aprovado
**Release ID:** v0.1.39
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29

## Workflow Evidence

The requested release-definition workflow was attempted first:

```bash
.dadaia/.venv/bin/dadaia lifecycle release define \
  --context dadaia-workspace \
  --release-id v0.1.39 \
  --run-id v0139-define-sdd-governance \
  --backlog sdd-governance-v2-agents-lifecycle \
  --harness pi \
  --model gpt-5.3-codex-spark:medium \
  --json
```

It blocked at `spec_create` because the selected context exceeded the headless prompt
budget. A fake-worker retry also blocked before launch, proving the issue is prompt
selection, not PI runtime execution. This release therefore includes the workflow blocker
as a picked bug and uses this manually authored SPEC/PLAN/TASKS as the fallback definition.

## Picked Scope

| Item | Kind | Disposition in this release |
|------|------|-----------------------------|
| `specs/backlog/sdd-governance-v2-agents-lifecycle.md` | backlog | Partially consumed: specs archive taxonomy/gate-class slice ships; JSONL bug-events and audit-disposition law remain explicit residuals. |
| `specs/bugs/release-definition-spec-create-overselects-context-budget.md` | bug | Fixed in this release. |
| `specs/bugs/lifecycle-review-commands-miss-active-segment-artifacts.md` | bug | Fixed in this release. |

## Requirements

### R1 - Release-definition selected-scope selectors are bounded

`release_definition.spec_create` asks for `selected_backlog_items`, `selected_bugs`, and
`selected_audit_findings` and expects exactly the operator-picked items. Those selectors
MUST use `ReleaseDefinitionScopeInput` when present and MUST NOT inject the entire
backlog, bug, or audit corpus.

Acceptance:

- A release-definition run scoped to one backlog item records only that backlog file in
  the `selected_backlog_items` context refs.
- A release-definition run scoped to one bug records only that bug file in
  `selected_bugs`.
- The oversized-prompt failure mode for this scoped release is eliminated.

### R2 - Per-class specs archive directories are FROZEN

The SDD gate path classifier MUST classify the accepted per-class archive directories as
FROZEN:

- `specs/backlog/_archive/**`
- `specs/audits/_archive/**`
- `specs/bugs/_archive/**`

Archive writes through file-write tools are blocked; deliberate archive moves remain a
git operation outside the file-tool gate envelope.

Acceptance:

- Unit coverage proves these three path families classify as `FROZEN`.
- Existing `specs/_archive/**` behavior remains unchanged.

### R3 - Scaffold and doctor know the accepted taxonomy

New scaffolded spec trees and specs doctor repair/validation MUST include the three
per-class archive directories without changing the existing central release archive model.

Acceptance:

- Scaffold/doctor tests prove `backlog/_archive`, `audits/_archive`, and
  `bugs/_archive` are created or accepted.
- Consumed backlog release-ledger behavior under `specs/_archive/<release>/` is not
  replaced in this alpha.

### R4 - Residual governance pillars stay visible

This alpha does NOT implement JSONL bug-events or audit-disposition law. The backlog item
must be rewritten after implementation to retain only those residuals.

Acceptance:

- `sdd-governance-v2-agents-lifecycle` remains non-terminal with shipped taxonomy notes
  and explicit residual sections for JSONL bug-events and audit-disposition law.

### R5 - Single-step lifecycle review prompts identify active segment artifacts

Review and closure workers MUST be told the concrete active release artifact directory
when the requested release is segmented in `ACTIVE.md`.

Acceptance:

- A QA review prompt for active `release: v0.1.39`, `segment: alpha-1` references
  `specs/releases/v0.1.39/alpha-1/`.
- A QA workflow rerun no longer rejects because it searched only the flat release path.

## Out of Scope

- JSONL bug-event CLI/schema/migration.
- Audit-disposition law and audit archive lifecycle.
- Panel analytics for bug telemetry.
- Any OpenCode-related scope.

## Traceability

| Source | Requirements |
|--------|--------------|
| `sdd-governance-v2-agents-lifecycle` taxonomy pillar | R2, R3, R4 |
| `release-definition-spec-create-overselects-context-budget` | R1 |
| `lifecycle-review-commands-miss-active-segment-artifacts` | R5 |
