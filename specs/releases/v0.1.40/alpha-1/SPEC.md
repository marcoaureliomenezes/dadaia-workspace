# SPEC: v0.1.40 alpha-1 - SDD Governance v2 completion

**Status:** Aprovado
**Release ID:** v0.1.40
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-29
**Consumes:** sdd-governance-v2-agents-lifecycle

## Workflow Evidence

Release definition was attempted through dadaia-workflows first, as the default path:

```bash
dadaia lifecycle release define --context dadaia-workspace --release-id v0.1.40 \
  --run-id v0140-define-sdd-governance-v2 \
  --backlog sdd-governance-v2-agents-lifecycle \
  --bug backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict \
  --bug backlog-doctor-blocks-consumed-item-refactor-commit \
  --bug lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention \
  --harness pi --model gpt-5.3-codex-spark:medium --json
```

PI blocked at `spec_create` with `agent result missing artifact evidence`. The bug-report
workflow recorded `pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence`.

The fallback workflow harnesses were then tried:

- `--harness fake` blocked at `spec_create` because `specs/releases/v0.1.40/SPEC.md`
  did not exist.
- `--harness codex --model gpt-5.5:medium` blocked at `spec_create` for the same
  missing canonical `SPEC.md` artifact.

Those blockers were also registered through `dadaia lifecycle bug report`. This
SPEC/PLAN/TASKS set is therefore a manual fallback for definition only, justified by
workflow bugs in the release's picked scope. Implementation, review, and closure remain
workflow-first.

## Picked Scope

| Item | Kind | Disposition in this release |
|------|------|-----------------------------|
| `sdd-governance-v2-agents-lifecycle` | backlog | Fully consumed: JSONL bug-events and audit-disposition law ship here. |
| `backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict` | bug | Fixed by terminal-status parser alignment. |
| `backlog-doctor-blocks-consumed-item-refactor-commit` | bug | Fixed by consume-aware backlog doctor behavior during active release implementation. |
| `lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention` | bug | Fixed by making workflow-first lifecycle a canonical rule/memory surface. |
| `pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence` | bug | Fixed by release-definition create-step artifact reliability hardening. |
| `fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact` | bug | Fixed by deterministic fake create-artifact materialization. |
| `codex-release-definition-spec_create-does-not-create-canonical-spec.md-artifact` | bug | Fixed by create-step artifact contract/gate hardening shared by Layer-2 workers. |

## Requirements

### R1 - Release-definition create steps produce canonical artifacts

The release-definition workflow MUST be able to complete `spec_create`, `plan_create`,
and `tasks_create` with canonical artifacts at the active release artifact path.

Acceptance:

- `dadaia lifecycle release define --harness fake` writes `SPEC.md`, `PLAN.md`, and
  `TASKS.md` and completes through `definition_commit_gate`.
- The create-step gate rejects handoff-only success when the file is absent.
- The PI/Codex create-step prompt and adapter path preserve the exact artifact path and
  hash requirements; a live worker failure is surfaced as a workflow bug, not silently
  treated as a successful definition.

### R2 - Event-sourced JSONL bug telemetry ships

Add append-only bug telemetry alongside the existing Markdown bug records.

Acceptance:

- A JSON schema is shipped for bug events with required `bug_id`, `event`, `ts`, and
  `reported_by`; event types are `reported`, `resolved`, `superseded`, `deferred`,
  `rejected`, and `archived`.
- `dadaia bugs append`, `dadaia bugs status`, and `dadaia bugs stats` operate on
  `specs/bugs/<YYYYMMDDTHH>Z.jsonl`, rotating after 1000 rows.
- The CLI validates event coherence: non-`reported` events require a prior `reported`
  event for the same `bug_id`.
- A migration path converts current `specs/bugs/*.md` records into JSONL events and
  archives the Markdown sources under `specs/bugs/_archive/`.
- Existing `dadaia lifecycle bug report` remains compatible during the transition.

### R3 - Audit-disposition law ships

Audit findings MUST be explicitly dispositioned before audit archive.

Acceptance:

- The audit workflow/doctor recognizes every finding disposition:
  `fixed`, `superseded`, `deferred`, or `rejected`.
- A release after an audit must disposition every finding before closure can claim the
  audit is complete.
- Audits move to `specs/audits/_archive/` only when all findings are dispositioned and
  the release is approved.
- Open bugs and open audits are documented as higher-priority release-definition inputs
  than plain backlog.

### R4 - Workflow-first lifecycle is canonical

For supported lifecycle phases, dadaia-workflows are the rule and manual execution is
the exception.

Acceptance:

- `release-governance`, `workspace-protocol`, relevant skills, and memory state that
  release definition, implementation, review, closure, bug-report, audit, research, and
  backlog-definition should use `dadaia lifecycle ...` workflows by default.
- Manual fallback is documented as allowed only when the workflow is unavailable or
  itself broken, and the fallback must register the workflow bug first.
- The rule is projected through public assets and `dadaia public doctor` remains green.

### R5 - Backlog terminal status checks agree

Backlog doctor and specs doctor MUST share one terminal-status interpretation.

Acceptance:

- `backlog doctor` accepts ADR-11 terminal statuses with version suffixes such as
  `DELIVERED - v0.1.40` and `CONSUMED - v0.1.40`.
- `specs doctor` no longer warns for a consumed backlog item using the same canonical
  terminal-status form.
- The pre-commit backlog gate does not block implementation commits for a backlog item
  declared in the active release `**Consumes:**` line solely because its old anchors are
  being moved by the consuming release.

## Out Of Scope

- Panel bug analytics beyond CLI `stats`.
- Replacing the existing Markdown bug-report workflow in one step; compatibility must be
  preserved for this alpha.
- Renaming historical archived release folders that already produce legacy warnings.

## Traceability

| Source | Requirements |
|--------|--------------|
| `sdd-governance-v2-agents-lifecycle` | R2, R3 |
| `lifecycle-prompts-still-depend-on-agents-remembering-to-use-dadaia-workflows-by-convention` | R4 |
| `pi-release-definition-spec_create-still-blocks-with-missing-artifact-evidence` | R1 |
| `fake-release-definition-spec_create-does-not-create-canonical-spec.md-artifact` | R1 |
| `codex-release-definition-spec_create-does-not-create-canonical-spec.md-artifact` | R1 |
| `backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict` | R5 |
| `backlog-doctor-blocks-consumed-item-refactor-commit` | R5 |
