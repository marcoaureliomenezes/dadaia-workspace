---
name: cross-cutting-feature
description: Feature that spans frontend and backend simultaneously. product-engineer scopes, software-architect approves the API contract, qa runs parallel red tests, frontend-engineer and backend-engineer implement in parallel, qa validates the integration end-to-end.
version: 0.1.0
schema_version: "1"
inputs:
  context:
    type: string
    required: true
    description: Active spec context.
  feature_topic:
    type: string
    required: true
    description: "Release ID under `specs/releases/` (alias of legacy `feature_topic` slug under specs/features/ — use release_id for new callers)."
  task_id_frontend:
    type: string
    required: true
    description: Approved frontend task identifier from TASKS.md.
  task_id_backend:
    type: string
    required: true
    description: Approved backend task identifier from TASKS.md.
stages:
  - id: discovery
    agent: product-engineer
    expected_output:
      path: ".dadaia/reports/{context}/product-engineer/{run_ts}-{feature_topic}-cross-discovery.html"
      must_include: ["API contract", "Frontend impact", "Backend impact"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.feature_topic"
        as: feature_topic

  - id: contract_review
    agent: software-architect
    needs: [discovery]
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-{feature_topic}-contract.html"
      must_include: ["Contract approved"]
    inputs:
      - kind: stage_output
        from: stages.discovery.output
        as: discovery_report
    gate:
      kind: operator-approval
      prompt: "Approve API contract between frontend and backend before red tests start?"

  - id: red_test_frontend
    agent: qa-engineer
    needs: [contract_review]
    parallel_group: red_tests
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_frontend}-red.html"
      must_include: ["Failing tests"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id_frontend"
        as: task_id
      - kind: stage_output
        from: stages.contract_review.output
        as: contract_report

  - id: red_test_backend
    agent: qa-engineer
    needs: [contract_review]
    parallel_group: red_tests
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_backend}-red.html"
      must_include: ["Failing tests"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.task_id_backend"
        as: task_id
      - kind: stage_output
        from: stages.contract_review.output
        as: contract_report

  - id: green_frontend
    agent: frontend-engineer
    needs: [red_test_frontend]
    parallel_group: green_impls
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-{task_id_frontend}-green.html"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test_frontend.output
        as: failing_tests_report

  - id: green_backend
    agent: backend-engineer
    needs: [red_test_backend]
    parallel_group: green_impls
    expected_output:
      path: ".dadaia/reports/{context}/backend-engineer/{run_ts}-{task_id_backend}-green.html"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test_backend.output
        as: failing_tests_report

  - id: integration_validation
    agent: qa-engineer
    needs: [green_frontend, green_backend]
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{feature_topic}-integration.html"
      must_include: ["Integration validated"]
    inputs:
      - kind: stage_output
        from: stages.green_frontend.output
        as: frontend_green_report
      - kind: stage_output
        from: stages.green_backend.output
        as: backend_green_report
    gate:
      kind: operator-approval
      prompt: "Approve integration validation and close cross-cutting feature?"

exit_criteria:
  - all_stages: completed
---

# cross-cutting-feature

For features where the user-visible change AND the server-side change must ship together.
Coordinates `frontend-engineer` and `backend-engineer` in parallel, around a single
API contract that `software-architect` approves up front.

## When to use

- A new endpoint that the UI consumes — both sides need to be built and they must agree
  on the contract
- A schema change that affects the rendered shape and the producing service
- Anything where shipping only one side leaves the system in an incoherent state

When in doubt, prefer two separate `tdd-cycle` runs (one per side) unless the contract
risk is high.

## Stages

1. **discovery** — `product-engineer` writes a focused discovery report explicitly
   listing the API contract (endpoints, request/response shape, error envelopes) and the
   impact on each side.
2. **contract_review** — `software-architect` validates the proposed contract.
   Operator-approval gate here is the single most important gate of the workflow — once
   approved, both implementers race ahead in parallel.
3. **red_test_frontend / red_test_backend** — `qa-engineer` writes failing tests for
   each side in parallel. Both consume the approved contract as input.
4. **green_frontend / green_backend** — `frontend-engineer` and `backend-engineer` work
   in parallel against the contract. Each closes when its own failing test passes.
5. **integration_validation** — `qa-engineer` runs E2E tests that exercise the full
   contract (frontend calls backend, real network). Operator-approval gate at the end.

## Why not run two `tdd-cycle` workflows in parallel?

You could, but you'd lose:
- The explicit contract review gate before either side starts implementing
- A formal integration validation stage that exercises the joined behavior
- Synchronization of timing — without this workflow you have to coordinate manually

## Caveats

- The frontend and backend MAY land in different repos. The orchestrator must understand
  multi-repo context for this workflow to be useful — confirm before running.
- `qa-engineer` runs 3 times in this workflow (2 red, 1 integration). Watch maxTurns
  budget across the full pipeline.
