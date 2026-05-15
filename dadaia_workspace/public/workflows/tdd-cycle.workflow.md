---
name: tdd-cycle
description: software-engineer ↔ qa-engineer alternating red-green-refactor with optional product consult.
version: 0.1.0
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
stages:
  - id: red_test
    agent: qa-engineer
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id}-red.md"
      must_include: ["Failing tests"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id"
        as: task_id

  - id: green_impl
    agent: software-engineer
    needs: [red_test]
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-{task_id}-green.md"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test.output
        as: failing_tests_report

  - id: refactor
    agent: software-engineer
    needs: [green_impl]
    expected_output:
      path: ".dadaia/reports/{context}/software-engineer/{run_ts}-{task_id}-refactor.md"
    inputs:
      - kind: stage_output
        from: stages.green_impl.output
        as: green_report
    gate:
      kind: operator-approval
      prompt: "Approve refactor and close task?"

  - id: consult_product
    agent: product-engineer
    needs: [red_test]
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-{task_id}-consult.md"
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

Paired loop between `software-engineer` and `qa-engineer` for a single approved
TASKS.md task: `qa-engineer` writes failing tests (red), `software-engineer`
makes them pass (green), then refactors. A `consult_product` branch lets the
operator pause the loop and trigger `product-engineer` for clarification on the
task contract.
