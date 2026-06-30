---
id: backlog_definition.conflict_resolution_grill
role: product-engineer
workflow: backlog_definition
step: conflict_resolution_grill
static_inputs: []
dynamic_inputs: [backlog_index]
output_schema: conflict-resolution-v1
max_context_policy: summary
---

# Conflict resolution grill — reconcile a divergent conflict into one item

This step runs only when the review found at least one `DIVERGENT_CONFLICT`: a demand and an
existing item touch the same subject with incompatible targets (the `C->D` vs `C->E` twin).
That divergence is exactly the defect that has corrupted a project before, so it must be
reconciled with the operator before anything is authored — no unresolved divergence may pass.

## Inputs you reason over

| Input | Use |
|---|---|
| `backlog_index` | The existing item's bound intents + status, so each conflict can be rendered as "you previously asked X@anchor; now Y@anchor". |

## Procedure

1. **Render the conflict plainly.** For each divergent anchor, state the prior change and
   the new change against the same canonical subject — "previously X@anchor; now Y@anchor" —
   so the operator sees the contradiction without jargon.
2. **Grill to a single decision.** Run the grill questionnaire on the conflict set. Drive
   each conflict to one resolution: keep the old target, adopt the new target, or define a
   single reconciled change that supersedes both. "It depends" is not an answer.
3. **Forbid the twin.** The outcome is exactly one intended change per shared subject. You
   never resolve a conflict by letting both items survive — that recreates the divergence.

## Output

A resolution result naming, for every divergent anchor, the single agreed change that will
hold against that subject and which existing item it folds into. This is what the authoring
step writes into one reconciled backlog item; an unresolved divergence blocks the workflow.
