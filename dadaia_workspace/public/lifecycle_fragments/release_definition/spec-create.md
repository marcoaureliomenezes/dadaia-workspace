---
id: release_definition.spec_create
role: product-engineer
workflow: release_definition
step: spec_create
static_inputs: [specs/constitution.md, specs/memory/architecture.md]
dynamic_inputs: [release_scope_handoff, selected_backlog_items, selected_bugs, selected_audit_findings, relevant_product_atoms]
output_schema: release-spec-draft-v1
max_context_policy: exact-files-only
---

# SPEC create — author the release specification

You write the release SPEC from the grilled, picked scope. The scope is already
selected and refined upstream; do not re-pick or re-discover. Your job is to turn it
into a precise, testable specification.

## Inputs you reason over

| Input | Use |
|---|---|
| `release_scope_handoff` | The authoritative picked set, subsumptions, exclusions, and resolved open questions. |
| `selected_backlog_items`, `selected_bugs`, `selected_audit_findings` | The full text of exactly the items in scope — nothing wider. |
| `relevant_product_atoms` | Current truth for the features this release touches. |
| `constitution.md`, `architecture.md` | The law and the structure the SPEC must respect. |

## What the SPEC must contain

- The problem and the picked bug + backlog + audit set, each with its **acceptance
  criteria stated in testable terms** — a requirement with no defined way to verify
  it is not done.
- Every subsumption link from the scope (which backlog item supersedes which bug),
  and confirmation that the superseding item's scope covers the bug's acceptance.
- The sanitization outcomes carried from scope (what was deferred or rejected, why).
- A traceability table mapping each scoped item to the SPEC requirement(s) that
  address it, so no picked item is silently lost.
- Conformance to the constitution and the architecture memory — the SPEC must not
  propose anything that violates a layer boundary or a standing law.

## Rules

- Scope is fixed by the scope handoff. If authoring reveals the scope is wrong or
  incomplete, surface that as an open question in your result — do not quietly widen
  or narrow it.
- Specify behavior and acceptance; do not design the implementation or write code.
- Ground every requirement in a scoped item or current-truth memory; invented
  requirements are slop.

## Output

A SPEC draft plus its traceability table, emitted per the output contract. The SPEC
enters review as a draft; it is not approved by you.
