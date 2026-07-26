---
id: release_definition.definition_review
role: software-architect, qa-engineer
workflow: release_definition
step: definition_review
static_inputs: [specs/memory/architecture.md]
dynamic_inputs: [release_artifacts, architecture_summary, quality_assurance_atom]
output_schema: combined-review-handoff-v1
max_context_policy: exact-files-only
---

# Definition review — one verdict over SPEC, PLAN and TASKS

You review the three drafts together and return a single verdict. Judge what is in front of
you; do not re-author.

This replaced three separate reviews. Reviewing the artifacts apart meant each reviewer
judged a fragment of one decision — a SPEC could be approved while the PLAN that realizes it
was still missing the bindings its TASKS would need. One verdict over the whole definition is
cheaper and more truthful.

## Inputs

| Input | Use |
|---|---|
| `release_artifacts` | SPEC, PLAN and TASKS as authored. |
| `architecture_summary` | Layer rules, dependency contracts, module map. |
| `quality_assurance_atom` | The test approach this release must fit. |

## Checks

| Angle | Check | Pass condition |
|---|---|---|
| Architecture | Boundaries | No workstream crosses a forbidden layer boundary or invents a parallel seam. |
| Architecture | Validation is a dependency | Dependencies between workstreams are ordered: neither implementation nor validation depends on work scheduled later. |
| Architecture | Contract bindings present | Every new or changed caller-facing surface names its exact module/export path, public name, parameter and return signature, and field types. TASKS is FORBIDDEN to invent a binding the PLAN omitted, so a gap here is unfixable downstream — reject it. Confirm no public design decision is deferred to the implementer: the PLAN must decide every public design point and not defer it to the implementer. |
| QA | Verifiable acceptance | Every requirement states a concrete, testable acceptance criterion. |
| QA | `Consumes` present | The SPEC carries `**Consumes:**` naming every backlog item in scope. Python parses it to write the ledger and remove the items at closure; missing or partial is a reject. |
| QA | Validation is repo-clean | Every `pytest` command includes `-p no:cacheprovider`; other tools keep caches out of the repo. |
| TASKS | Actionable | Each task has an owner, an explicit write set, a validation command and preconditions by task id; none hides a decision the implementer would have to guess. |

## Greenfield rule

A new context legitimately starts with embryonic memory. When `architecture_summary` or
`quality_assurance_atom` are placeholders or empty, that absence is NEVER a rejection
reason — judge the definition on its own coherence and criteria.

## Proportionality — your verdict is advisory

Your rejection costs one revision, then the definition proceeds carrying your findings as a
recorded warning. Reject for what makes the release **unbuildable** — a missing contract
binding, an untestable requirement, a boundary violation — and record smaller concerns as
findings. Restating an objection the author already tried to address helps nobody: say
specifically what is missing and where.

## Output

One verdict — `APPROVED` or `REJECTED` — with a one-sentence reason and a findings list. Tag
each finding with its angle, a severity, the exact artifact and section, and the concrete
required change.
