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
| Architecture | Boundary fidelity | No workstream crosses a forbidden layer boundary or invents a parallel seam. |
| Architecture | Sequencing | Dependencies between workstreams are correct and ordered; nothing depends on work scheduled later. |
| Architecture | Prior art | The plan reuses existing mechanisms where they fit rather than building bespoke. |
| QA | SPEC coverage | Every SPEC requirement maps to at least one workstream; nothing is orphaned. |
| QA | Test-first | Each workstream names how it is verified, with the test strategy stated before the build. |
| QA | Risk | Regression and failure-mode coverage is planned, not assumed. |

## Output

A verdict — `APPROVED` or `REJECTED` — with a one-sentence reason and a findings
list spanning both angles. Each finding cites the exact plan section and names the
gap (a missing requirement, an unprovable workstream, a boundary violation, a wrong
dependency order) with a recommended fix. Reject when either angle fails; do not
approve to be agreeable.
