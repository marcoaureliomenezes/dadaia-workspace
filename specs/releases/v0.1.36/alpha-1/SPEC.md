# SPEC: v0.1.36 alpha-1 - PI Layer-2 Release-Definition Hardening

**Status:** Aprovado
**Release ID:** v0.1.36
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Objective

Make PI usable as a real Layer-2 worker for the release-definition workflow by fixing
the live failures found while attempting this release with `--harness pi`.

## Scope

**Consumes:** none

This segment does not consume the historical delivered epics
`workflow-model-governance-panel-control-plane` or
`workflow-step-handoff-data-plane-cleanup`; both are already delivered and were
sanitized as current-truth context only. It also does not consume the residual
`pi-agent-fourth-harness` WS-PI-5 item, because DEAD-marking the standalone
`dadaia-pi-workspace` context is operator-gated. The release advances the PI backlog by
solving concrete residual bugs blocking PI Layer-2 workflow execution.

## Requirements

| ID | Requirement | Verification |
|---|---|---|
| R1 | PI model ids passed to `pi` MUST be provider-qualified to the operator's Codex provider, and the selected reasoning effort MUST reach PI's `--thinking` flag. | Contract test captures the generated PI argv and asserts `--model openai-codex/<id>` plus `--thinking <effort>`. |
| R2 | The PI catalog and built-in PI implementation profile MUST use a model id present in the live PI Codex model list: `gpt-5.3-codex-spark`, not stale `gpt-5.3-codex`. | Catalog/profile tests and public asset tests resolve the new id. |
| R3 | `lifecycle release define --step-model` MUST be label-specific. Two steps on the same harness may select different models without collapsing by `AgentRuntimeKind`. | CLI integration test runs two PI steps with distinct `--step-model` values and asserts each request carries its own `resolved_model`. |
| R4 | Release-definition create fragments MUST instruct workers to write canonical `SPEC.md`, `PLAN.md`, and `TASKS.md` files and return artifact refs plus SHA-256 content hashes. | Fragment/public asset tests and fake release-definition workflow tests cover canonical artifact production; real PI validation is run after implementation. |
| R5 | The live bug records for PI model routing, step-model collapse, and `spec_create` missing artifacts MUST reflect the fixed root cause and residual risk. | Bug markdown updated with resolution notes and validation evidence. |
| R6 | While release-definition waits on a live Layer-2 worker, the lifecycle run state MUST expose which worker is active instead of showing an unchanged opaque running record. | Integration test inspects the persisted run from inside the worker call and asserts `active_worker` is present, then cleared after the worker returns. |

## Traceability

| Scoped item | Requirement(s) |
|---|---|
| `lifecycle-step-model-overrides-collapse-by-runtime-kind` | R3 |
| `pi-default-review-profiles-gpt-5-5-unreachable-provider` | R1, R2 |
| `bug-spec-create-pi-no-artifact-bug_write` | R4 |
| `release-define-pi-worker-long-running-no-progress-heartbeat` | R6 |
| `pi-agent-fourth-harness` residual review | R1, R2, R3, R4; WS-PI-5 remains deferred |
| `workflow-model-governance-panel-control-plane` residual review | R2, R3 |
| `workflow-step-handoff-data-plane-cleanup` residual review | R4 |
