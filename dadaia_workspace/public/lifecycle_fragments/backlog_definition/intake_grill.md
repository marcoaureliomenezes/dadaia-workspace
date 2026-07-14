---
id: backlog_definition.intake_grill
role: product-engineer
workflow: backlog_definition
step: intake_grill
static_inputs: []
dynamic_inputs: [product_catalog_summary, backlog_index, source_summary, open_bugs]
output_schema: backlog-demand-v1
max_context_policy: summary
---

# Intake grill — turn an operator demand into proposed intents

This step researches and interrogates a raw operator demand until it is understood well
enough to become machine-readable **(subject -> change)** intents. Bug reports enter
through the same intake: normalize and redact the symptom, establish whether it is new,
then express the required correction as an intent. You do not author the backlog item or
bind subjects here.

## Inputs you reason over

| Input | Use |
|---|---|
| `product_catalog_summary` | The current feature truth, so a demand is grounded in what exists. |
| `backlog_index` | Every existing backlog item's bound intents + status, so you can spot up front whether the demand already overlaps something filed. |
| `source_summary` | Existing implementation evidence used to test the demand's assumptions. |
| `open_bugs` | Current bug records used to deduplicate a reported symptom before proposing work. |

## Procedure

1. **Run the grill questionnaire** over the demand. Surface inconsistencies, scope
   gaps, ambiguous acceptance, undeclared dependencies, and divergent naming before
   anything is written. This grill is mandatory even when the demand looks obvious.
2. **Investigate uncertain claims.** Inspect the relevant implementation and existing
   evidence. When external facts matter, prefer primary sources. Record what is proven,
   contradicted, or still open; do not create a separate research workflow or report.
3. **Normalize bug input.** When a symptom is present, capture expected behavior,
   reproduction, severity, and likely owning subject; compare it with existing bugs and
   backlog entries before proposing new work.
4. **Name the subjects.** For each thing the demand would change, propose a typed
   subject (a code anchor, a CLI/doc/invariant id, a catalog slug) and the change
   intended against it. Prefer a name already present in the `backlog_index` over a
   new synonym — naming drift is exactly the defect this workflow exists to prevent.
5. **Flag likely overlaps.** If the demand appears to touch a subject some existing
   item already touches, say so — the later review step will classify it deterministically,
   but an early flag keeps the grill honest.

## Output

A demand result listing evidence considered, normalized bug data when applicable,
proposed `(subject -> change)` intents, grill findings and resolutions, overlaps, and
open questions. This is the proposed-intent input the binding step consumes; it is not
yet a backlog item.
