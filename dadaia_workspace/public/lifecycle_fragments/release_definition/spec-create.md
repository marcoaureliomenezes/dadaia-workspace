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
- A concrete verification path for every acceptance criterion. Public behavior must
  name the observable input, output, or failure that proves it. Internal or negative
  constraints (for example, "must not recompute", "must not call", or "contains no
  duplicate rule") must name a controlled probe/fake, call-observation test,
  structural/static inspection, or review evidence that can prove the claim. Do not
  rely on equal end results to prove which internal path produced them.
- Every subsumption link from the scope (which backlog item supersedes which bug),
  and confirmation that the superseding item's scope covers the bug's acceptance.
- The sanitization outcomes carried from scope (what was deferred or rejected, why).
- A traceability table mapping each scoped item to the SPEC requirement(s) that
  address it, so no picked item is silently lost.
- **A `**Consumes:**` line — mandatory, machine-read.** Immediately after the Status
  line, write:

  ```
  **Consumes:** <slug>, <slug>, <slug>
  ```

  listing the bare slug of EVERY backlog item in scope (no `.md`, comma-separated).
  When the prompt carries an `authoritative-backlog-definition` block, that block's
  items are exactly the list — all of them, nothing else. This is not documentation:
  Python parses this one line to write the `consumed_backlog` ledger and to remove the
  consumed items at closure, and a definition that omits an item the scope declared is
  REFUSED by the commit gate (`ScopeNotConsumedError`). The traceability table above is
  prose for humans; this line is the contract the tooling reads.
- Conformance to the constitution and the architecture memory — the SPEC must not
  propose anything that violates a layer boundary or a standing law.

## Rules

- Scope is fixed by the scope handoff. If authoring reveals the scope is wrong or
  incomplete, surface that as an open question in your result — do not quietly widen
  or narrow it.
- Specify behavior and acceptance; do not design the implementation or write code.
- Verification design is part of acceptance, not implementation design: state enough
  about the observable seam or evidence type that QA can decide whether the claim is
  provable. If no proof mechanism exists, rewrite the requirement as observable
  behavior or surface it as an unresolved question instead of asserting it.
- Ground every requirement in a scoped item or current-truth memory; invented
  requirements are slop.
- **Greenfield context:** when the architecture memory is embryonic (placeholder or
  explicitly greenfield), the SPEC is the FOUNDING structural reference — it must
  additionally propose the initial module layout (components and their
  responsibilities) and state end-to-end acceptance scenarios in Given/When/Then
  form, so the review has concrete structure and observable criteria to approve.

## Output

A SPEC draft plus its traceability table, emitted per the output contract. The SPEC
enters review as a draft; it is not approved by you.
