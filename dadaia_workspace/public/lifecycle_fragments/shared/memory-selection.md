---
id: shared.memory_selection
role: shared
workflow: shared
step: memory_selection
static_inputs: [specs/memory/product/catalog.json]
dynamic_inputs: [selected_memory_atoms, product_catalog_summary]
output_schema: handoff-v1.1
max_context_policy: summary
---

# Memory selection — read the few atoms the step needs

The workflow injects current product truth as selected memory, not as the whole
memory tree. You receive a catalog summary and zero or more pre-selected atoms in
`selected_memory_atoms`. Reason over those; do not demand the entire memory.

## What you are given

| Input | Use |
|---|---|
| `product_catalog_summary` | Index of features with a one-line summary each; use it to know what exists and which atoms matter. |
| `selected_memory_atoms` | The 1–3 atoms the step actually needs, supplied in full. Read these closely. |

## How to use it

- Ground every claim about current product behavior in the supplied atoms or the
  catalog summary — never in assumption or memory of an earlier state.
- The catalog summary tells you a feature exists and roughly what it does; that is
  enough for most reasoning. Only escalate to a full atom when the step must decide
  something that turns on the feature's exact contract.
- If the step needs an atom that was not supplied, say so explicitly in your result
  (name the feature and why) rather than guessing its contents. The workflow's
  context selector can widen the bundle; you must not invent the missing detail.
- Architecture-level memory (layer rules, dependency contracts, agent topology) is
  large and is supplied only when a step's decision touches structure. When it is
  absent, do not assume structural facts.

## Rule

Read the relevant atoms before deciding. Working from a stale or absent atom is the
failure this fragment exists to prevent: a step that reasons over a feature it never
read produces drift, not truth. Never edit a memory atom — memory is current truth,
written only in the definition and closure phases of a release.
