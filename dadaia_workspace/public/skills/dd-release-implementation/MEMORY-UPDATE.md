# MEMORY-UPDATE — dd-release-implementation (final-rc step 8 detail)

Disclosed reference reached at `SKILL.md` step 8 — `product-engineer` reads this before touching any `specs/memory/**` atom at closure.
The closure memory protocol.

## Protocol

1. Verify gate phase: confirm the live release is in `CLOSURE` phase before writing `specs/memory/**` (also writable in `DEFINITION`).
2. Set `phase` in `_RELEASE.json` (`RELEASE-EVENTS.md`; there is no mirror document to keep in sync).
3. Otherwise the gate blocks the write.
4. Do not author legacy HTML memory — if it exists, treat it as read-only migration input; new memory writes are Markdown.
5. Update Markdown atoms: apply the release's deltas to the corresponding `specs/memory/*.md` / `specs/memory/product/*.md` files.
6. Memory describes the product as it is now, not what changed — change history lives in this release's `_RELEASE.json` `log` and git.
7. Diagrams: use fenced Mermaid blocks; memory Markdown carries no external image references.
8. `ARCHITECTURE.md`'s own `## Architecture Diagrams` section is the pattern to follow.
9. Forbidden in memory Markdown: `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, `<h2>Versions</h2>`.
10. Forbidden (continued): `<section class="changelog">` and similar; narrative of past versions ("we used to use X, now Y").
11. Point the operator to this release's `_RELEASE.json` `log` or git if they ask for history.
12. Validate with `dadaia specs doctor` before moving to archive — it checks atomicity and Mermaid script presence.

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

*Done when:* every affected atom reflects current product truth, and `dadaia specs doctor` reports the memory atoms clean.
*Done when* (continued): `_RELEASE.json`'s `phase` field reads `CLOSURE`.
