---
id: release_definition.definition_draft
role: product-engineer
workflow: release_definition
step: definition_draft
static_inputs: [specs/constitution.md, specs/memory/architecture.md]
dynamic_inputs: [selected_backlog_items, selected_bugs, selected_audit_findings, relevant_product_atoms]
output_schema: generic-step-handoff-v1
max_context_policy: exact-files-only
---

# Definition draft — SPEC, PLAN and TASKS in one pass

You write the three release artifacts together, from the picked scope, in one session.

They used to be three separate worker sessions with a review between each: six model calls,
each re-sent the same constitution, architecture and scope, and each split decisions that
belong together. The PLAN's contract bindings are exactly what the TASKS must copy, so
authoring them apart guaranteed drift and a rejection. One pass is cheaper AND more
coherent — you decide a contract once and use it immediately.

## What you write

| Artifact | Must contain |
|---|---|
| `SPEC.md` | The problem and the picked set, each with **acceptance criteria stated in testable terms**, and a concrete verification path for every acceptance criterion — public behaviour names the observable input/output/failure that proves it; an internal or negative constraint names a controlled probe/fake, call-observation test, or structural/static inspection that
can prove it — never rely on equal end results to prove which internal path produced them. Plus the `**Consumes:**` line below. |
| `PLAN.md` | The ordered workstreams, where each change lands, and — for every new or changed caller-facing surface — its **contract binding**. Plus the `## Validation Dependency Table`. |
| `TASKS.md` | One task per unit of work: owner role, explicit write set, description, validation command, preconditions by task id, and the `[ ]` marker. |

## Three things Python reads literally

Parsed by tooling, not by a human. Get them exactly right.

1. **`**Consumes:** <slug>, <slug>`** in `SPEC.md` — MANDATORY, machine-read. Right
   after the Status line, naming the
   bare slug of EVERY backlog item in scope. When the prompt carries an
   `authoritative-backlog-definition` block, that block's items ARE the list — all of them.
   Python writes the consumed-backlog ledger from this line and removes those items at
   closure; a definition that omits one is refused.

2. **Contract bindings** in `PLAN.md`: for each new or changed caller-facing surface, the
   exact module/export path, public type/function/method name, parameter and return
   signature, and field names with types. Decide them here — do not leave them for TASKS or implementation to invent. TASKS
   copies them verbatim. Copy those bindings faithfully — copy those bindings faithfully — and is forbidden to invent one
   you left out — anything you omit becomes unfixable downstream.

3. **`## Validation Dependency Table`** in `PLAN.md` — a Python lint blocks the step without
   it. One row per workstream (`WS-1`, `WS-2`, …), `None` for an empty cell:

   ```
   | Workstream | Produces by end | Direct validation | Validation dependencies | Deferred integration evidence |
   |---|---|---|---|---|
   ```

   The `Consumes` line is written literally like this, one line, comma-separated:

   ```
   **Consumes:** <slug>, <slug>
   ```

   Each workstream's validation is part of its dependency graph, so the table must be
   validation dependency-safe: no workstream may depend on validation
   scheduled after it, and anything that can only be proven later goes in the deferred
   integration evidence column.

## Rules

- Scope is fixed. If authoring reveals it is wrong, say so in your result — never widen or
  narrow it silently.
- Every `pytest` command in TASKS must include `-p no:cacheprovider`; a deterministic lint
  rejects it otherwise (`--cache-clear` is not a substitute).
- Specify behaviour and acceptance; do not write implementation code.
- Ground every requirement in a scoped item or in current-truth memory. Invented
  requirements are slop.
- **When revising, REWRITE ALL THREE FILES.** Never append or patch: a leftover tail from a
  previous draft creates duplicate task ids, which is an automatic rejection.

## Output

The three artifacts on disk, emitted per the output contract. They enter review as drafts;
you do not approve them.
