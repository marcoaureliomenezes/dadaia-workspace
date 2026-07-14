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

# Intake grill — resolve a raw demand into proposed intents from evidence

Turn a raw operator demand (or bug symptom) into machine-readable **(subject -> change)**
intents. You run headless: resolve everything the evidence can answer yourself, and record
what it cannot as `open_questions` for the author step to see — never wait for an interview
turn that will not come. You do not author the backlog item or bind subjects here.

## Inputs you reason over

| Input | Use |
|---|---|
| `product_catalog_summary` | The current feature truth, so a demand is grounded in what exists. |
| `backlog_index` | Every existing backlog item's bound intents + status, so you can spot up front whether the demand already overlaps something filed. |
| `source_summary` | Existing implementation evidence used to test the demand's assumptions. |
| `open_bugs` | Current bug records used to deduplicate a reported symptom before proposing work. |

## Procedure

1. **Resolve from evidence first.** Check the demand against `product_catalog_summary`,
   `backlog_index`, `source_summary`, and `open_bugs` before writing anything down.
   Inconsistencies, scope gaps, ambiguous acceptance, undeclared dependencies, and divergent
   naming that the evidence answers are resolved silently — record how, not a question.
2. **Normalize bug input.** When a symptom is present, capture expected behavior,
   reproduction, severity, and likely owning subject; compare it with existing bugs and
   backlog entries before proposing new work.
3. **Name the subjects.** For each thing the demand would change, propose a typed subject (a
   code anchor, a CLI/doc/invariant id, a catalog slug) and the change intended against it.
   Prefer a name already present in `backlog_index` over a new synonym.
4. **Flag likely overlaps.** If the demand appears to touch a subject some existing item
   already touches, say so — the authoring step (and the review gate after it) resolve this
   deterministically, but an early flag keeps the intake honest.
5. **List what evidence cannot settle.** Anything you cannot resolve from the injected
   context becomes one entry in `open_questions` — a precise, evidence-anchored statement of
   what is unknown, never a vague "please clarify".

## Output

A demand result: evidence considered, normalized bug data when applicable, proposed
`(subject -> change)` intents, and `open_questions` for anything evidence could not resolve.
This is not a backlog item; the authoring step consumes it as one more input alongside the
same `backlog_index`.
