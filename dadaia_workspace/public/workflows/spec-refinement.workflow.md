---
name: spec-refinement
description: Discovery -> 5-way parallel-capable specialist analysis topology (arch + devops + qa + frontend + backend) -> synthesis with operator gates. Codex runtime receives manual/reference handoffs, not spawned subagents.
version: 0.3.0
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
    description: "Release ID under `specs/releases/` (alias of legacy `topic` — pass `release_id` for new callers)."
stages:
  - id: research_evidence
    name: research-evidence
    agent: researcher
    description: "Evidence harvest — dispatch researcher to gather facts before main analysis."
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.release_id"
        as: release_id

  - id: discovery
    agent: project-manager
    needs: [research_evidence]
    consumes:
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
      must_include: ["Findings", "Riscos", "Decisões necessárias"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.context"
        as: context
      - kind: workflow_input
        from: "$.inputs.topic"
        as: topic
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report
    gate:
      kind: operator-approval
      prompt: "Approve discovery report before triggering parallel-capable specialist analysis?"

  - id: arch_review
    agent: software-architect
    needs: [discovery]
    parallel_group: specialists
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-arch.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: devops_review
    agent: devops-engineer
    needs: [discovery]
    parallel_group: specialists
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-devops.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: qa_review
    agent: qa-engineer
    needs: [discovery]
    parallel_group: specialists
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-qa.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: frontend_review
    agent: frontend-engineer
    needs: [discovery]
    parallel_group: specialists
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-spec-review.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: backend_review
    agent: backend-engineer
    needs: [discovery]
    parallel_group: specialists
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/backend-engineer/{run_ts}-spec-review.handoff.json"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: synthesis
    agent: project-manager
    needs: [arch_review, devops_review, qa_review, frontend_review, backend_review]
    consumes:
      - ".dadaia/reports/{context}/software-architect/{run_ts}-arch.handoff.json"
      - ".dadaia/reports/{context}/devops-engineer/{run_ts}-devops.handoff.json"
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-qa.handoff.json"
      - ".dadaia/reports/{context}/frontend-engineer/{run_ts}-spec-review.handoff.json"
      - ".dadaia/reports/{context}/backend-engineer/{run_ts}-spec-review.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-synthesis.handoff.json"
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
      prompt: "Approve the synthesized report before product-engineer authors the SPEC?"

  - id: spec_write
    agent: product-engineer
    needs: [synthesis]
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-synthesis.handoff.json"
    expected_output:
      path: "specs/releases/{release_id}/SPEC.md"
      must_include: ["Status", "Critérios de Aceite"]
    inputs:
      - kind: stage_output
        from: stages.synthesis.output
        as: synthesis_report

exit_criteria:
  - all_stages: completed
---

# spec-refinement

This workflow runs the canonical SDD spec refinement pipeline for any feature topic:
discovery by `project-manager`, parallel-capable analysis by five specialists
(`software-architect`, `devops-engineer`, `qa-engineer`, `frontend-engineer`,
`backend-engineer`), then synthesis by `project-manager`, and finally SPEC authoring
by `product-engineer` as a leaf.

Runtime note: `parallel_group` records workflow topology. Claude may delegate
parallel-capable stages with native tools. Codex receives manual/reference
handoff files and does not spawn subagents or execute runtime parallelism.

`frontend-engineer` and `backend-engineer` were added in v0.2.0 to capture
stack-specific concerns at spec time: the frontend agent reviews UX/UI
implications, accessibility, performance budgets, and component decomposition;
the backend agent reviews data model, API contract, DB index implications, and
performance budgets. When a feature is purely backend or purely frontend, the
non-relevant specialist produces a short "not applicable" report — but always
runs, to make implicit decisions explicit.

In v0.3.0 the discovery and synthesis stages moved from `product-engineer` to
`project-manager`, who owns the intake interview (grill-me) and report assembly.
`product-engineer` is now a leaf: it only authors the final SPEC artifact. This
separation keeps PE's prompt focused on spec quality and memory atomicity rather
than orchestration concerns.

Operator gates are placed (a) after discovery — to validate that the right problem
is framed — and (b) after synthesis — to validate the assembled findings before
PE writes the SPEC.

Pre-implementation agreement gate: before TASKS reaches `Aprovado`, every
implementation task must be reviewed by the owning implementer(s), `qa-engineer`,
`code-reviewer`, and `security-reviewer`; UI tasks also require
`design-specialist`. The task must define implementation scope, write set,
unit/integration test plan, E2E or validation plan, review criteria, and
security/privacy checks. If any required agent objects, TASKS stays out of
approval until the task is revised.
