---
name: audit-fanout
description: project-manager dispatches a deterministic audit sequence — project-auditor bootstraps memory, runs the doctors, applies the drift-detection skill, and emits a findings handoff; PM then decides backlog vs immediate release. Cites the drift-detection skill rather than restating it. Honesty note in body.
version: 0.1.0
schema_version: "1"
trigger: operator-requests-audit-or-closure
owner: project-manager
activity_class: ADDITIVE
lifecycle_phase: Audits
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (project to audit).
  scope:
    type: string
    required: false
    default: "full"
    description: Audit scope — "full" (entire project) or "partial" (a specific feature area).
stages:
  - id: audit_run
    agent: project-auditor
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-auditor-audit.handoff.json"
      must_include: ["doctor", "drift-detection", "findings"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.scope"
        as: scope
  - id: triage
    agent: project-manager
    needs: [audit_run]
    expected_output:
      path: ".dadaia/handoff/{context}/{run_ts}-project-manager-audit-triage.handoff.json"
      must_include: ["backlog", "release decision"]
    inputs:
      - kind: stage_output
        from: stages.audit_run.output
        as: audit_findings
exit_criteria:
  - all_stages: completed
---

# audit-fanout

The deterministic audit dispatch sequence. `project-manager` triggers it; `project-auditor`
executes the read-only audit and emits a findings handoff; PM reads the handoff and decides
the disposition. The step order is fixed and the output format (handoff JSON) is
contractual, which is why a reference file beats ad-hoc dispatch.

Cites constitution §1 matrix: **activity class ADDITIVE, lifecycle phase Research** (§7
phase 4, audit). The audit writes only to `.dadaia/reports/**` and `.dadaia/handoff/**` and
takes no lease (§8 ADDITIVE).

> **Honesty note.** This is a dispatch-reference document. Claude Code and Codex workflow
> Markdown does not auto-execute at runtime (constitution §4). This file is read by an
> agent only when `project-manager` explicitly loads it as context. It is not a Claude Code
> or Codex runtime primitive. In Codex, fan-out requires an explicit subagent delegation
> request or a future real executor; this file alone never spawns agents.

## When to use

When the operator requests a workspace audit, or at a release CLOSURE checkpoint where a
drift check against memory is required before the release is finalized.

## Steps (deterministic audit sequence)

1. **Bootstrap memory.** `project-auditor` reads `specs/memory/architecture.md`,
   `specs/memory/product/index.md`, and the target feature atoms for the in-scope area.
2. **Run the doctors.** Run `dadaia public doctor` and `dadaia specs doctor`. Any non-zero
   exit is an immediate finding recorded in the handoff.
3. **Drift detection.** Apply the **`drift-detection`** skill for the in-scope features.
   This workflow CITES that skill by name and does NOT restate its procedure — the skill is
   the single source of the drift-detection rubric (anti-duplication, constitution §12.3).
4. **Emit findings.** `project-auditor` emits the findings handoff JSON to
   `.dadaia/handoff/<context>/`, with severity-tagged drift items and recommended actions.
5. **PM triage.** `project-manager` reads the findings handoff and decides whether to open
   backlog items (routed per §10) or to open an immediate release. This decision is a PM
   judgment call made after step 4 — it is not embedded in this workflow.

## Judgment delegation

The workflow embeds no judgment about the disposition of findings. After step 4, PM decides
backlog vs release. The audit itself is read-only; the only writes are report and handoff
files.

## Output

The project-auditor findings handoff under `.dadaia/handoff/<context>/` is the primary
deliverable, followed by the PM triage handoff recording the disposition decision.
