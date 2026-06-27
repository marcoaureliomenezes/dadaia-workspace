---
id: backlog_definition.conflict_scan
role: product-engineer
workflow: backlog_definition
step: existing_backlog_review
static_inputs: []
dynamic_inputs: [backlog_index]
output_schema: overlap-report-v1
max_context_policy: summary
---

# Conflict scan — adjudicate a same-anchor merge (model only)

Python owns the conflict boundary. It has already computed the canonical-anchor set
intersection between the bound demand and every existing item: an empty intersection is
`UNRELATED`, a shared anchor with an identical change is `DUPLICATE`, and a shared anchor
with a **differing** change defaults — fail-closed — to `DIVERGENT_CONFLICT`. You are
consulted on exactly one question, and only for a shared-anchor differing-change pair:
**is this difference a compatible merge, or a real conflict?**

## Inputs you reason over

| Input | Use |
|---|---|
| `backlog_index` | The bound intents + status of the existing item that shares the anchor, so you can judge whether the two changes can coexist. |

## The single judgement you may make

For the one shared anchor whose change differs between the demand and the existing item:

- If the two changes are **provably compatible or additive** — they can both hold against
  the same subject without contradiction — return an explicit, structured compatible-merge
  verdict (`OVERLAP` to fold scope, or `SUPERSEDES` when the new change wholly replaces the
  old). State the evidence that proves compatibility.
- Otherwise return **nothing** to downgrade. Absent a structured proven-compatible merge,
  the class stays `DIVERGENT_CONFLICT`. You may only downgrade a conflict with evidence;
  you can never upgrade an `UNRELATED` or miss a conflict — that is Python's call, not yours.

## Output

An adjudication for the shared-anchor pair: either a structured compatible-merge verdict
with its evidence, or an explicit "no compatible merge — remains divergent". The Python
review step folds this into the overlap report; it never advances on your say-so alone.
