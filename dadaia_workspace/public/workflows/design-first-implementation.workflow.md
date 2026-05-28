---
name: design-first-implementation
description: Design-gated frontend implementation. design-specialist produces Figma + design report → quality gate → frontend-engineer implements → qa-engineer validates functional + design compliance.
version: 1.0.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name.
  surface:
    type: string
    required: true
    description: "UI surface under review (e.g. 'portfolio', 'dadaia-workspace-panel', or a path)."
  task_id:
    type: string
    required: true
    description: "Approved task identifier from TASKS.md."
stages:
  - id: design_production
    name: design-production
    agent: design-specialist
    description: "Produce Figma artifact + design report for the surface. Output must include figma_url and all 8 required sections."
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/design-specialist/{run_ts}-design.handoff.json"
      must_include: ["figma_url", "Design spec", "ASCII sketches", "Handoff to frontend-engineer"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.surface"
        as: surface
    gate:
      kind: operator-approval
      prompt: "Design report produced. Review the design spec and Figma artifact before allowing frontend implementation to begin."

  - id: design_quality_gate
    name: design-quality-gate
    agent: design-specialist
    needs: [design_production]
    description: "Run design-report-quality-gate skill to verify all 8 sections pass, including figma_url. Blocks if any section is FAIL."
    consumes:
      - ".dadaia/reports/{context}/design-specialist/{run_ts}-design.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/design-specialist/{run_ts}-quality-gate.handoff.json"
      must_include: ["PASS"]
    inputs:
      - kind: stage_output
        from: stages.design_production.output
        as: design_report

  - id: implementation
    name: implementation
    agent: frontend-engineer
    needs: [design_quality_gate]
    description: "Implement the approved design spec. design_report is a required stage input — gate blocks if missing."
    consumes:
      - ".dadaia/reports/{context}/design-specialist/{run_ts}-design.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-{task_id}-green.handoff.json"
      must_include: ["All tests pass"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id
      - kind: stage_output
        from: stages.design_production.output
        as: design_report

  - id: qa_validation
    name: qa-validation
    agent: qa-engineer
    needs: [implementation]
    description: "Two-pass validation: (1) functional E2E, (2) design compliance — token audit, spacing, contrast, visual regression against design report."
    consumes:
      - ".dadaia/reports/{context}/frontend-engineer/{run_ts}-{task_id}-green.handoff.json"
      - ".dadaia/reports/{context}/design-specialist/{run_ts}-design.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-design-compliance.handoff.json"
      must_include: ["E2E pass", "Design compliance pass"]
    inputs:
      - kind: stage_output
        from: stages.implementation.output
        as: green_report
      - kind: stage_output
        from: stages.design_production.output
        as: design_report

exit_criteria:
  - all_stages: completed
---

# design-first-implementation

Formal workflow encoding the design-first gate for browser surfaces. Guarantees that no
HTML/CSS/JS is written until a `design-specialist` report with a Figma artifact exists and
has passed the quality gate.

## When to use

Use this workflow when:
- A new page, layout, or distinctive component is being built from scratch
- An existing surface is receiving a significant visual redesign (not a bug fix)
- `project-manager` determines that the feature touches browser surfaces requiring formal design review

For bug fixes and minor non-visual refactors, use `tdd-cycle` directly and document the
skip reason in the implementation report.

## Stages

1. **design_production** — `design-specialist` produces the full design spec + Figma artifact.
   An operator-approval gate here ensures the design is reviewed before any code is written.
   The Figma artifact must contain: cover frame, component frames (1× and 2×), token
   annotations, responsive breakpoints (360/768/1280px), and state variants.

2. **design_quality_gate** — `design-specialist` runs `design-report-quality-gate` skill.
   All 8 sections must PASS, including the new section 8 (figma_url). An INCOMPLETE report
   blocks the workflow until the design-specialist resolves all FAIL items.

3. **implementation** — `frontend-engineer` implements against the approved spec. The
   design report flows in as a hard stage input — the agent's design gate prose enforces
   it. Any ambiguity triggers a STOP and escalation back to design-specialist.

4. **qa_validation** — `qa-engineer` runs two passes:
   - *Pass 1 (Functional E2E):* user flows, a11y (axe-core), responsive breakpoints
   - *Pass 2 (Design compliance):* token audit, spacing grid check, contrast verification,
     visual regression at 360/768/1280px. Both passes must return PASS.

## Relationship to tdd-cycle

`design-first-implementation` wraps the green-phase of `tdd-cycle` — the
`frontend-engineer` implementation stage is equivalent to the TDD green phase. You may
run a `qa-engineer` red phase (via `tdd-cycle`) inside the `implementation` stage for
unit/component tests; the qa_validation stage here covers E2E + design compliance.
