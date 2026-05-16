---
name: architecture-review
description: Formal REVIEW mode for software-architect. Architect audits a codebase against its declared architecture, surfaces violations, then product-engineer converts the improvement backlog into TASKS.md entries.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context (repo to review).
  scope:
    type: string
    required: false
    default: "full"
    description: Audit scope — "full" (entire repo) or "feature" (a single feature directory).
  feature_topic:
    type: string
    required: false
    default: ""
    description: When scope=feature, the release id under `specs/releases/`.
stages:
  - id: code_audit
    agent: software-architect
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-review.html"
      must_include: ["Architectural violations", "Improvement backlog"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.scope"
        as: scope
      - kind: workflow_input
        from: "$.inputs.feature_topic"
        as: feature_topic
    gate:
      kind: operator-approval
      prompt: "Approve the architectural audit and improvement backlog before tasks creation?"

  - id: tasks_creation
    agent: product-engineer
    needs: [code_audit]
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-arch-tasks.html"
      must_include: ["TASKS.md updated"]
    inputs:
      - kind: stage_output
        from: stages.code_audit.output
        as: arch_report

exit_criteria:
  - all_stages: completed
---

# architecture-review

Formal entry point for `software-architect`'s REVIEW mode. Pairs the audit with a
follow-through to actionable backlog items.

## When to use

- A repo has been in active development for a while and the operator wants a health check
- A feature was implemented and the operator wants confidence the implementation respects
  the declared architecture
- Onboarding a new architect to an existing project (combine with `onboarding-new-repo`)

## Stages

1. **code_audit** — `software-architect` applies the `architect-code-audit` skill: dead
   code, stale layers, SOLID violations, design pattern misuse. Produces a structured
   report with severity-tagged findings and a prioritized improvement backlog.
2. **tasks_creation** — `product-engineer` reads the audit report and converts each
   approved improvement into atomic `TASKS.md` entries with explicit owners (one of the
   4 implementers). Specs may be updated to reflect any architectural decision changes.

## Operator gate

Placed between the audit and tasks_creation. The operator reviews each finding and
decides which are accepted (and become TASKS) vs deferred (annotated in the audit
report).

## What this workflow does NOT do

- Does not implement the fixes — that's separate `tdd-cycle` runs per task
- Does not change code — `software-architect` is read-only; `product-engineer` only
  edits `specs/`
