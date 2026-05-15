---
name: spec-refinement
description: Discovery → 3-way parallel specialist analysis → synthesis with operator gates.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context name (e.g. dadaia-workspace).
  topic:
    type: string
    required: false
    default: "next-evolution"
    description: Free-form topic label persisted into output paths.
stages:
  - id: discovery
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-discovery.md"
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
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-arch.md"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: devops_review
    agent: devops-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/devops-engineer/{run_ts}-devops.md"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: qa_review
    agent: qa-engineer
    needs: [discovery]
    parallel_group: specialists
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-qa.md"
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report

  - id: synthesis
    agent: product-engineer
    needs: [arch_review, devops_review, qa_review]
    expected_output:
      path: "specs/features/{topic}/SPEC.md"
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
    gate:
      kind: operator-approval
      prompt: "Approve the synthesized SPEC before promoting it to 'Em revisão'?"

exit_criteria:
  - all_stages: completed
---

# spec-refinement

This workflow runs the canonical SDD spec refinement pipeline for any feature topic:
discovery by `product-engineer`, parallel analysis by `software-architect`,
`devops-engineer` and `qa-engineer`, then synthesis back through `product-engineer`.

Operator gates are placed (a) after discovery — to validate that the right problem
is framed — and (b) after synthesis — to validate the resulting SPEC before it is
checked in.
