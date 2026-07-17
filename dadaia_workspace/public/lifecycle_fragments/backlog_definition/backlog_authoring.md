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

Your deliverable is a FILE ON DISK: create or edit exactly one Markdown item under
`specs/backlog/<slug>.md` using your file tools, then confirm it exists by reading it
back. Answering with the item's content in your final message WITHOUT writing the file
is a FAILED step — a Python gate diffs the `specs/backlog/` directory and blocks when
nothing landed there.

You author the result of the reconciliation: either a NEW backlog item or an EDIT to an
existing one. Write a single, consistent item that carries bound intents (YAML
frontmatter `intents:` list of `subject: { kind: code, ref: path#symbol }` + `change`),
a valid status, and a clear scope. You never write both a new file and an edit, and you
never create a twin of an existing item.

## Inputs you reason over

| Input | Use |
|---|---|
| `backlog_index` | The existing items' bound intents + status, so an EDIT folds into the right item and a NEW item does not duplicate one. |
| `Canonical subject anchors` | The registry's resolvable anchor list injected into this prompt — the ONLY refs `intents[]` may bind. Copy `ref` verbatim from it; match the `kind`. |

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
- Keep subjects canonical: every `subject.ref` is copied VERBATIM from the "Canonical
  subject anchors" list in this prompt (kind must match the anchor's kind). Never invent
  a ref — an unlisted ref is rejected by `backlog_review_gate` as an unresolved subject.
- Anchors stay module-relative `path#symbol` (or a non-path anchor id) — never an
  operator-local absolute path or a private name.
- Author content, not history: the item states current intended scope, not a changelog.

## Output

One backlog item — a new file or an in-place edit — with bound intents, status, and scope,
emitted per the output contract. The Python review gate re-runs the classifier over the
result and blocks any duplicate or divergent conflict it would introduce.
