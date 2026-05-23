---
name: cross-cutting-feature
description: Feature that spans two or more domain surfaces simultaneously (frontend↔backend, Python↔Node, pipeline↔dashboard, AI-entity↔runtime). project-manager scopes, software-architect approves the contract, qa runs parallel red tests, the chosen implementer pair (or trio) builds in parallel against the contract, qa validates the integration end-to-end. Implementer slot is selected from {frontend-engineer, backend-engineer, software-engineer-python, software-engineer-node, data-engineer, data-analyst, ai-engineer} based on the file paths the release touches.
version: 0.3.0
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
  - id: research_evidence
    name: research-evidence
    agent: researcher
    description: "Evidence harvest — dispatch researcher to gather facts before main analysis."
    consumes: []
    expected_output:
      path: ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    inputs:
      - kind: workflow_input
        from: "$.inputs.feature_topic"
        as: feature_topic

  - id: discovery
    agent: project-manager
    needs: [research_evidence]
    consumes:
      - ".dadaia/reports/{context}/researcher/{run_ts}-evidence.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/project-manager/{run_ts}-{feature_topic}-cross-discovery.handoff.json"
      must_include: ["API contract", "Frontend impact", "Backend impact"]
    inputs:
      - kind: workflow_input
        from: "$.inputs.feature_topic"
        as: feature_topic
      - kind: stage_output
        from: stages.research_evidence.output
        as: evidence_report

  - id: contract_review
    agent: software-architect
    needs: [discovery]
    consumes:
      - ".dadaia/reports/{context}/project-manager/{run_ts}-{feature_topic}-cross-discovery.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/software-architect/{run_ts}-{feature_topic}-contract.handoff.json"
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
    consumes:
      - ".dadaia/reports/{context}/software-architect/{run_ts}-{feature_topic}-contract.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_frontend}-red.handoff.json"
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
    consumes:
      - ".dadaia/reports/{context}/software-architect/{run_ts}-{feature_topic}-contract.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_backend}-red.handoff.json"
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
    consumes:
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_frontend}-red.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/frontend-engineer/{run_ts}-{task_id_frontend}-green.handoff.json"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test_frontend.output
        as: failing_tests_report

  - id: green_backend
    agent: backend-engineer
    needs: [red_test_backend]
    parallel_group: green_impls
    consumes:
      - ".dadaia/reports/{context}/qa-engineer/{run_ts}-{task_id_backend}-red.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/backend-engineer/{run_ts}-{task_id_backend}-green.handoff.json"
      must_include: ["All tests pass"]
    inputs:
      - kind: stage_output
        from: stages.red_test_backend.output
        as: failing_tests_report

  - id: integration_validation
    agent: qa-engineer
    needs: [green_frontend, green_backend]
    consumes:
      - ".dadaia/reports/{context}/frontend-engineer/{run_ts}-{task_id_frontend}-green.handoff.json"
      - ".dadaia/reports/{context}/backend-engineer/{run_ts}-{task_id_backend}-green.handoff.json"
    expected_output:
      path: ".dadaia/reports/{context}/qa-engineer/{run_ts}-{feature_topic}-integration.handoff.json"
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

For features where two or more domain surfaces must ship together against a single agreed
contract. Coordinates the implementer pair (or trio) in parallel, around a contract that
`software-architect` approves up front.

The canonical example remains frontend↔backend — a new endpoint that the UI consumes,
where shipping only one side leaves the system incoherent. But the same coordination
shape applies whenever a release straddles surfaces owned by different specialists:
Python↔Node, pipeline↔dashboard, AI-entity↔runtime.

## When to use

- A new endpoint that the UI consumes — both sides need to be built and they must agree
  on the contract
- A schema change that affects the rendered shape and the producing service
- A Python CLI that shells out to a Node helper (twin specialists, disjoint write sets)
- A new curated table that hydrates a new BI dashboard (data-engineer ⇄ data-analyst)
- A new agent persona whose runtime adapter lives in Python (ai-engineer ⇄
  software-engineer-python)
- Anything where shipping only one side leaves the system in an incoherent state

When in doubt, prefer two separate `tdd-cycle` runs (one per side) unless the contract
risk is high.

## Routing decision — pick the implementer pair (or trio)

Before dispatch, project-manager (or product-engineer in spec entry) reads the release's
SPEC.md to identify the file paths the cross-cutting feature will touch, then maps each
path family to its owning specialist using the table below. The implementer slot is
**always** filled by one or more of the seven leaf specialists listed below — never the
retired generic implementer that the legacy lib used to expose.

| Path family the feature touches | Implementer dispatched |
|---|---|
| Browser surfaces (`*.tsx`, `*.jsx`, browser `*.ts`/`*.js`, `*.css`, `*.html`, `*/frontend/`, `*/client/`, `*/web/`, `*/ui/`) | `frontend-engineer` |
| Go services, `*.go`, `go.mod`, `go.sum`, production DB integrations | `backend-engineer` |
| Python lib + scripts (`*.py`, `pyproject.toml`, `dadaia_workspace/{features,infrastructure,cli,core}/**`, Python-marked `repos/**`) | `software-engineer-python` |
| Node tooling, server-side (`package.json` projects without browser bundler, CLIs, agent runtimes, npm tooling) | `software-engineer-node` |
| Data pipelines (`*.sql`, `**/databricks/**`, `**/dabs/**` excluding `dashboards/`, `**/notebooks/**`, `**/pipelines/**`) | `data-engineer` |
| BI dashboards (`**/dashboards/**`, `**/genie/**`, `**/bi/**`, `**/dabs/dashboards/**`) | `data-analyst` |
| AI-entity surface (`dadaia_workspace/public/{skills,rules,workflows,commands,agents,hooks}/**`) | `ai-engineer` |

Dispatch rules:

1. **One path family touched → single implementer**. Use `tdd-cycle` directly; this
   workflow is overkill.
2. **Exactly two path families → pair dispatch**. Both implementers run in parallel
   inside the `green_impls` parallel group. Their `paths.write_allowlist` boundaries
   guarantee no collision on disk.
3. **Three or more path families → trio (or more) dispatch**. Same parallel group, same
   disjoint-write-set guarantee. Watch maxTurns budget across qa-engineer (red + red +
   ... + integration).
4. **Python↔Node twin tasks** — when both lib languages are touched, dispatch both
   `software-engineer-python` and `software-engineer-node` in parallel; each handles its
   own file subset.
5. **Data pipeline + BI dashboard** — dispatch `data-engineer` to produce the curated
   table first, then `data-analyst` to consume it. If both ship in the same release, the
   workflow stages them with `data-engineer` ahead of `data-analyst` (sequential, not
   parallel — BI needs the table to exist).
6. **AI-entity + Python runtime** — dispatch `ai-engineer` and `software-engineer-python`
   in parallel; the persona file and the Python adapter ship together.

The YAML stage graph below shows the canonical frontend↔backend instantiation. When the
implementer pair is different (e.g. python↔node), the orchestrator substitutes the
`green_frontend` / `green_backend` slots with the chosen implementer agents while keeping
the same red-test-then-green-impl-then-integration shape.

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
