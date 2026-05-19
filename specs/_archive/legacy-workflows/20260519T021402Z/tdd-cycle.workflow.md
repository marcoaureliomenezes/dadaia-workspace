---
name: tdd-cycle
description: implementer ↔ qa-engineer alternating red-green-refactor with optional product consult. The implementer is parameterized — pass implementer_agent=frontend-engineer | backend-engineer | software-engineer. Game agents use game-dev-cycle instead.
version: 0.4.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context.
  task_id:
    type: string
    required: true
    description: Approved task identifier from TASKS.md (e.g. T123).
  implementer_agent:
    type: string
    required: false
    default: software-engineer
    description: "Which engineer runs green_impl and refactor. One of frontend-engineer, backend-engineer, software-engineer. NOTE: game-developer, game-designer, game-tester use game-dev-cycle workflow instead."
stages:
  - id: red_test
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-red.html"
      must_include: ["Failing tests"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id

  - id: green_impl
    agent: "{{implementer_agent}}"
    needs: [red_test]
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-{task_id}-green.html"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test.output
        as: failing_tests_report

  - id: refactor
    agent: "{{implementer_agent}}"
    needs: [green_impl]
    expected_output:
      path: ".dadaia/reports/{context}/{implementer_agent}/{run_ts}-{task_id}-refactor.html"
    inputs:
      - kind: stage_output
        from: stages.green_impl.output
        as: green_report
    gate:
      kind: operator-approval
      prompt: "Approve refactor and proceed to deploy validation?"

  - id: deploy_validation
    agent: qa-engineer
    needs: [refactor]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-deploy.html"
      must_include: ["Deploy validated"]
    inputs:
      - kind: stage_output
        from: stages.refactor.output
        as: refactor_report
    gate:
      kind: operator-approval
      prompt: "Approve deploy validation and mark task DONE?"

  - id: consult_product
    agent: product-engineer
    needs: [red_test]
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-{task_id}-consult.html"
    inputs:
      - kind: stage_output
        from: stages.red_test.output
        as: failing_tests_report
    on_failure: continue
    gate:
      kind: operator-approval
      prompt: "Trigger product consult before green implementation?"

exit_criteria:
  - all_stages: completed
---

# tdd-cycle

Paired loop between an implementer agent and `qa-engineer` for a single approved
TASKS.md task: `qa-engineer` writes failing tests (red), the implementer makes
them pass (green), then refactors, and finally `qa-engineer` validates the
deploy against the live target environment. The implementer is parameterized via
the `implementer_agent` input — pass `frontend-engineer`, `backend-engineer`,
or `software-engineer` (default). Game agents (`game-developer`,
`game-designer`, `game-tester`) use the `game-dev-cycle` workflow instead.
A `consult_product` branch lets the operator pause the loop and trigger
`product-engineer` for clarification on the task contract.

The `deploy_validation` stage closes the loop: qa-engineer runs the E2E suite
against the deploy target (using Playwright MCP for browser surfaces), gating
the operator-approval that marks the task DONE in TASKS.md.

Resolution: the orchestrator substitutes `{{implementer_agent}}` (in the stage
agent and in the expected_output paths) with the value of the input at run
time. Reports land under `.dadaia/reports/{context}/<implementer>/...`.
