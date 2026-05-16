---
name: spec-refinement
description: Discovery → 5-way parallel specialist analysis (arch + devops + qa + frontend + backend) → synthesis with operator gates.
version: 0.2.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (e.g. dadaia-workspace).
  release_id:
    type: string
    required: false
    default: "next-evolution"
    description: Release ID under `specs/releases/`. (Alias: formerly `topic` — pass `release_id` for new callers.)
stages:
  - id: discovery
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-discovery.html"
      must_include: ["Findings", "Riscos", "Decisões necessárias"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.topic"
        as: topic
    gate:
      kind: operator-approval
      prompt: "Approve discovery report before triggering 3-way parallel analysis?"

  - id: arch_review
    agent: software-architect
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-arch.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: devops_review
    agent: devops-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-devops.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: qa_review
    agent: qa-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-qa.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: frontend_review
    agent: frontend-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-spec-review.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: backend_review
    agent: backend-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/backend-engineer/{run_ts}-spec-review.html"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: synthesis
    agent: product-engineer
    needs: [arch_review, devops_review, qa_review, frontend_review, backend_review]
    expected_output:
      path: "specs/releases/{release_id}/SPEC.md"
      must_include: ["Status", "Critérios de Aceite"]
    inputs:
      - kind: stage_output
        from: stages.arch_review.output
        as: arch_report
      - kind: stage_output
        from: stages.devops_review.output
        as: devops_report
      - kind: stage_output
        from: stages.qa_review.output
        as: qa_report
      - kind: stage_output
        from: stages.frontend_review.output
        as: frontend_report
      - kind: stage_output
        from: stages.backend_review.output
        as: backend_report
    gate:
      kind: operator-approval
      prompt: "Approve the synthesized SPEC before promoting it to 'Em revisão'?"

exit_criteria:
  - all_stages: completed
---

# spec-refinement

This workflow runs the canonical SDD spec refinement pipeline for any feature topic:
discovery by `product-engineer`, parallel analysis by five specialists
(`software-architect`, `devops-engineer`, `qa-engineer`, `frontend-engineer`,
`backend-engineer`), then synthesis back through `product-engineer`.

`frontend-engineer` and `backend-engineer` were added in v0.2.0 to capture
stack-specific concerns at spec time: the frontend agent reviews UX/UI
implications, accessibility, performance budgets, and component decomposition;
the backend agent reviews data model, API contract, DB index implications, and
performance budgets. When a feature is purely backend or purely frontend, the
non-relevant specialist produces a short "not applicable" report — but always
runs, to make implicit decisions explicit.

Operator gates are placed (a) after discovery — to validate that the right problem
is framed — and (b) after synthesis — to validate the resulting SPEC before it is
checked in.
