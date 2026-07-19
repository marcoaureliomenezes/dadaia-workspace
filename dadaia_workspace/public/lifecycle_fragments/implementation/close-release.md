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
   recorded as a memory ATOM at `specs/memory/product/<area>/<slug>.md`. PREFER the
   generator — `dadaia memory product add <slug> --specs-dir <specs-dir>` — then edit
   the generated body. If you write the file directly, copy this template VERBATIM
   and fill it (a malformed atom blocks this close — the Python gate validates
   frontmatter, allowlisted headings, and the mandatory markdown heading):

   ```markdown
   ---
   slug: <kebab-case-slug>
   title: <Feature Title>
   category: product
   tldr: <one-line summary under 160 chars>
   summary: <2-3 sentence description of the shipped capability>
   tags:
     - <tag>
   token_estimate: 0
   last_updated: "<YYYY-MM-DD>"
   release_origin: <release-id>
   ---

   ## Visão atômica

   <what this feature does, grounded in the shipped behavior>
   ```

   NEVER hand-edit `catalog.json` or
   `memory/product/index.md` — both are DERIVED files the workflow regenerates from
   the atoms after this step; a catalog entry without its atom is a doctor CAT-1
   defect and will be erased by the regeneration. Atom body headings must come from
   the memory heading allowlist (the scaffolded atoms show the canonical set; a
   workspace may extend it via `specs/memory/.heading-allowlist`) — a Python lint
   gate BLOCKS this close step on unknown/forbidden headings. `token_estimate` is
   derived and auto-corrected by the workflow; do not hand-tune it.
4. NEVER touch `releases/ACTIVE.md` — pointing it at none/none is a Python-owned
   effect applied only after this step and every gate succeed (a blocked close must
   leave the active release intact for resume). The Python workflow body also owns
   the final `[-]` to `[x]` task-marker transition; do not self-complete task markers.
5. Emit one closure handoff referencing the closure artifact.

Do not add history to memory, invent evidence, or close with an unresolved review.
