---
id: backlog_definition.backlog_authoring
role: product-engineer
workflow: backlog_definition
step: backlog_author
static_inputs: []
dynamic_inputs: [backlog_index]
output_schema: backlog-item-v1
max_context_policy: summary
---

# Backlog authoring — write the one consistent item

You author the result of the reconciliation: either a NEW backlog item or an EDIT to an
existing one. The reconcile plan has already decided which — your job is to write a single,
consistent item that carries bound intents, a valid status, and a clear scope. You never
write both a new file and an edit, and you never create a twin of an existing item.

## Inputs you reason over

| Input | Use |
|---|---|
| `backlog_index` | The existing items' bound intents + status, so an EDIT folds into the right item and a NEW item does not duplicate one. |

## What the item must carry

| Field | Requirement |
|---|---|
| `intents[]` | The bound `(subject -> change)` set from the reconcile plan — each subject already resolved to a canonical anchor; no free-text subjects. |
| Status | A valid backlog status reflecting where the item stands. |
| Scope | A concise statement of what the item covers, grounded in the resolved intents. |

## Rules

- **NEW file XOR edit EXISTING — never both, never a twin.** A NEW item is permitted only
  when the review found every existing item `UNRELATED`. Any overlap means an EDIT/MERGE
  into the existing item, folding the new scope in.
- Keep subjects canonical: reuse the bound anchors from the plan; introduce no synonym.
- Anchors stay module-relative `path#symbol` (or a non-path anchor id) — never an
  operator-local absolute path or a private name.
- Author content, not history: the item states current intended scope, not a changelog.

## Output

One backlog item — a new file or an in-place edit — with bound intents, status, and scope,
emitted per the output contract. The Python review gate re-runs the classifier over the
result and blocks any duplicate or divergent conflict it would introduce.
