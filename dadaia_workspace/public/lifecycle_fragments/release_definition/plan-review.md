---
id: release_definition.plan_review
role: qa-engineer, software-architect
workflow: release_definition
step: plan_review
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [plan_draft, approved_spec, architecture_summary, quality_assurance_atom]
output_schema: plan-review-verdict-v1
max_context_policy: exact-files-only
---

# PLAN review — verdict on soundness and test coverage

You review the PLAN draft against the approved SPEC and return a verdict. This step
is reviewed from two angles — architectural soundness and test adequacy — and your
verdict must cover both: the plan must be both buildable within the structure and
provable against the SPEC's acceptance.

## Inputs you reason over

| Input | Use |
|---|---|
| `plan_draft` | The plan under review. |
| `approved_spec` | The authority the plan must fully cover. |
| `architecture_summary` | Layer rules and seams the plan must respect. |
| `quality_assurance_atom` | The test strategy the plan must embody. |

## Review rubric

| Angle | Check | Pass condition |
|---|---|---|
| Architecture | Contract bindings present | Every NEW or CHANGED caller-facing surface carries its explicit contract binding: exact public type/function/method name, parameter and return signature, field names and types, and module/export path. A PLAN that leaves any of these to TASKS or implementation is REJECTED. Not a style note: `tasks-create` is forbidden to invent a binding the PLAN omitted, while `tasks-review-implementability` requires it present — so a PLAN approved without bindings traps the TASKS author between two rules it cannot both satisfy, and the failure surfaces at the one step that cannot repair it (bug plan-review-approves-a-plan-missing-its-contract-bindings). Catch it HERE, where it is fixable. |
| Architecture | Boundary fidelity | No workstream crosses a forbidden layer boundary or invents a parallel seam. |
| Architecture | Sequencing | Dependencies between workstreams are correct and ordered; neither implementation nor validation depends on work scheduled later. |
| Architecture | Prior art | The plan reuses existing mechanisms where they fit rather than building bespoke. |
| Architecture | Public contract bound | Every new or changed caller-facing value/API names its exact symbol, signature, fields, and module/export path; no public design decision is deferred to TASKS or implementation. |
| QA | SPEC coverage | Every SPEC requirement maps to at least one workstream; nothing is orphaned. |
| QA | Test-first | Each workstream names how it is verified, with the test strategy stated before the build. |
| QA | Risk | Regression and failure-mode coverage is planned, not assumed. |

Treat validation as a real dependency, not prose attached to a workstream. For every
workstream, verify that every named command, API, fixture, snapshot, integration path,
or other evidence source exists by the end of that workstream. Reject when an earlier
workstream can pass only after a later workstream creates the evidence surface, even if
the implementation dependencies themselves look ordered.

The PLAN must include the exact `## Validation Dependency Table` contract from the
create step. Cross-check its claims against the detailed workstreams: a row that says
`None` while its direct validation actually needs a later fixture, replay surface,
adapter, orchestrator, UI, or snapshot is a rejection. Foundational values must have
direct contract tests; later end-to-end evidence belongs to the workstream that first
makes that complete path available.

Reject a PLAN that says only "add a value", "add an API", or equivalent generic
language for a caller-facing surface. The implementer must not have to choose the
public name, signature, field contract, or import path after PLAN approval.

## Output

A verdict — `APPROVED` or `REJECTED` — with a one-sentence reason and a findings
list spanning both angles. Each finding cites the exact plan section and names the
gap (a missing requirement, an unprovable workstream, a boundary violation, a wrong
dependency order) with a recommended fix. Reject when either angle fails; do not
approve to be agreeable.
