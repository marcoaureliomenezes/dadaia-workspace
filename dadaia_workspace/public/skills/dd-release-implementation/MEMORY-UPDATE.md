# MEMORY-UPDATE — dd-release-implementation (RC-FLOW step 5 detail)

Disclosed reference reached at `SKILL.md` step 6 — `product-engineer` reads this before touching any `specs/memory/**` atom at closure.

## Protocol

1. The live release is in `CLOSURE` phase (`dadaia release phase CLOSURE --sha <sha>`) before any `specs/memory/**` write; the gate blocks it otherwise.
2. Apply the candidate's deltas to the corresponding `specs/memory/*.md` and `specs/memory/product/**` atoms.
3. Heading rule, forbidden history sections and the atom's shape: `specs/memory/AGENTS.md`.
4. Point the operator to this release's `_RELEASE.json` `log` or git if they ask for history.
5. Validate with `dadaia doctor` — its `specs` section checks atomicity and Mermaid script presence.

## Product memory is a folder catalog

- `specs/memory/product/` holds many small atoms, not a single file — bundling overloads humans and wastes agent tokens.
- `index.md` — entry point, read first: Vision (2-3 sentences), Users, the feature catalog in daily-relevance order.
- `index.md` (continued): each catalog entry links to `<feature-slug>.md`, plus a capability-map Mermaid diagram and explicit non-goals.
- `index.md` uses plain Markdown headings — no HTML `<section>` wrapper.
- `<area>/<feature-slug>.md` — one atom per production feature: Purpose (2-3 paragraphs), Usage flow (3-5 steps, optional Mermaid).
- `<area>/<feature-slug>.md` (continued): Typical trigger (1 sentence), Differentiator, Runtime state touched, Dependencies.
- Feature atoms follow English canon, curated headings only (`specs/memory/AGENTS.md`'s heading rule).
- Top-level trio's scaffold source: `dadaia_workspace/public/scaffold/memory/ARCHITECTURE.md` and `.../TECHSTACK.md` (no `.j2` templating).
- Product atoms are authored directly as Markdown during release closure.
- Update `index.md` only if the catalog order changed or a feature was added/removed; update affected atoms; leave the rest intact.
- A new feature gets its atom created and linked from `index.md`.
- A deprecated feature's link and its atom are deleted outright — memory carries no archive of its own (history lives in git).

*Done when:* every affected atom reflects current product truth, `dadaia doctor` reports the memory atoms clean, and one `kind: memory` log entry records atoms reviewed-unchanged vs changed.
