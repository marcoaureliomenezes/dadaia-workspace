---
id: backlog_definition.intake_grill
role: product-engineer
workflow: backlog_definition
step: intake_grill
static_inputs: []
dynamic_inputs: [product_catalog_summary, backlog_index]
output_schema: backlog-demand-v1
max_context_policy: summary
---

# Intake grill — turn an operator demand into proposed intents

This step interrogates a raw operator demand until it is understood well enough to be
expressed as machine-readable **(subject -> change)** intents. You do not author the
backlog item and you do not bind subjects to anchors — you produce the proposed intents
the next Python step will bind.

## Inputs you reason over

| Input | Use |
|---|---|
| `product_catalog_summary` | The current feature truth, so a demand is grounded in what exists. |
| `backlog_index` | Every existing backlog item's bound intents + status, so you can spot up front whether the demand already overlaps something filed. |

## Procedure

1. **Run the grill questionnaire** over the demand. Surface inconsistencies, scope
   gaps, ambiguous acceptance, undeclared dependencies, and divergent naming before
   anything is written. This grill is mandatory even when the demand looks obvious.
2. **Name the subjects.** For each thing the demand would change, propose a typed
   subject (a code anchor, a CLI/doc/invariant id, a catalog slug) and the change
   intended against it. Prefer a name already present in the `backlog_index` over a
   new synonym — naming drift is exactly the defect this workflow exists to prevent.
3. **Flag likely overlaps.** If the demand appears to touch a subject some existing
   item already touches, say so — the later review step will classify it deterministically,
   but an early flag keeps the grill honest.

## Output

A demand result listing the proposed `(subject -> change)` intents, the grill findings
and how each was resolved, any flagged overlap with an existing item, and the open
questions the grill could not close. This is the proposed-intent input the binding step
consumes; it is not yet a backlog item.
