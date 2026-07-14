---
id: release_definition.release_scope
role: product-engineer
workflow: release_definition
step: release_scope
static_inputs: []
dynamic_inputs: [open_bugs, open_audits, candidate_backlog, architecture_summary, product_catalog_summary]
output_schema: release-scope-handoff-v1
max_context_policy: summary
---

# Release scope — pick the set this release will address

This step turns the pool of open work — bugs, audit findings, candidate backlog
items — into a defined, grilled scope that the SPEC step will build from. You select
and bound; you do not write the SPEC.

## Inputs you reason over

| Input | Use |
|---|---|
| `open_bugs` | Bugs eligible to be solved in this release. |
| `open_audits` | Audit findings eligible for inclusion. |
| `candidate_backlog` | Backlog items the operator may want included. |
| `architecture_summary`, `product_catalog_summary` | Current-truth context so the scope is realistic against what exists. |

## Procedure

1. **Sanitize first.** Triage every candidate for staleness or invalidity. An item
   already solved, obsolete, or no longer valid is marked deferred (valid but not
   now) or rejected (invalid), each with a one-line reason. Nothing is ever deleted.
2. **Pick the set.** Select the bugs, audits, and backlog items this release will
   address. This is selection within the open pool — not wide-codebase discovery.
   When the prompt carries an `authoritative-backlog-definition` block, its exact
   producer-run artifact paths are mandatory scope inputs: pick those items and do
   not replace them with another candidate from the pool. Sanitize neighboring stale
   items normally, but never let pool order override the exact workflow handoff.
3. **Apply bug-always-solved.** Every picked bug is solved in this release, with one
   exception: a picked backlog item may supersede a bug with a more complete
   solution — then record the subsumption (mark the bug superseded by that item and
   require the item's tasks to cover the bug's acceptance). A bug is never silently
   dropped; if it is neither fixed nor subsumed, it is not picked.
4. **Grill the picked set.** Run the grill questionnaire over the picked set to
   surface inconsistencies, scope gaps, ambiguous acceptance, and stale assumptions
   before the SPEC exists. This is mandatory even when the scope looks obvious.

## Output

A scope handoff naming: the picked items (bugs, audits, backlog), every subsumption
link, the sanitization outcomes (what was deferred or rejected and why), the
explicit exclusions, and the open questions the grill could not close. This handoff
is the SPEC step's authoritative scope.
