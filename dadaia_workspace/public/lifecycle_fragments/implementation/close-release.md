---
id: implementation.close_release
role: product-engineer
workflow: implementation_reviews
step: close
static_inputs: []
dynamic_inputs: [release_artifacts, review_evidence, current_memory]
output_schema: closure-handoff-v1
max_context_policy: exact-files-only
---

# Close the approved release

Close only after QA, security, and code review have approved the same change.

1. Read SPEC, PLAN, TASKS, the review evidence, and current memory.
2. Write `CLOSURE.md` with the delivered scope and exact verification evidence. Cite
   the durable `.dadaia/runs/lifecycle/<run>/steps/*.step-payload.json` refs supplied
   by the workflow, never the temporary worker `artifact_refs` nested inside them.
3. Update memory only where the shipped product truth changed. A shipped feature is
   recorded as a memory ATOM: create/update
   `specs/memory/product/<area>/<slug>.md` with valid frontmatter (slug, title,
   category, tldr, summary, tags). NEVER hand-edit `catalog.json` or
   `memory/product/index.md` — both are DERIVED files the workflow regenerates from
   the atoms after this step; a catalog entry without its atom is a doctor CAT-1
   defect and will be erased by the regeneration. Atom body headings must come from
   the memory heading allowlist (the scaffolded atoms show the canonical set; a
   workspace may extend it via `specs/memory/.heading-allowlist`) — a Python lint
   gate BLOCKS this close step on unknown/forbidden headings. `token_estimate` is
   derived and auto-corrected by the workflow; do not hand-tune it.
4. Set `ACTIVE.md` to `release: none` and `phase: none`. The Python workflow body
   owns the final `[-]` to `[x]` task-marker transition after this closure step and
   every review gate succeed; do not self-complete task markers.
5. Emit one closure handoff referencing the closure artifact.

Do not add history to memory, invent evidence, or close with an unresolved review.
