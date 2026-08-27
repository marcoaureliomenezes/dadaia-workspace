# MEMORY-UPDATE — dd-release-implement (final-rc step 8 detail)

Disclosed reference reached at `SKILL.md` step 8 — `product-engineer` reads this before
touching any `specs/memory/**` atom at closure. Carries forward `CLOSURE-CHECKS.md`
§1 verbatim (T-050-21 rename; content unchanged in substance).

## Protocol

1. **Verify gate phase.** Confirm the live release is in `CLOSURE` phase before writing
   `specs/memory/**` (also writable in `DEFINITION`). The gate's own decision authority
   is still `releases/ACTIVE.md`'s `phase:` line during the FR4 transition — dual-write
   it alongside the `RELEASE.jsonl` `phase` record (`RELEASE-EVENTS.md`) until
   T-050-21A repoints the gate to the fold. Otherwise the gate blocks the write.
2. **Do not author legacy HTML memory.** If legacy HTML memory exists, treat it as
   read-only migration input. New memory writes are Markdown atoms.
3. **Update Markdown atoms.** Apply the release's deltas to the corresponding
   `specs/memory/*.md` or `specs/memory/product/*.md` files. Memory describes the
   product **as it is now** — not what changed. The change history now lives in this
   release's `RELEASE.jsonl` records (`RELEASE-EVENTS.md`) and the archived release dir.
4. **Diagrams.** Use fenced Mermaid blocks:
   ```mermaid
   flowchart LR
     A --> B
   ```
   The v6 canon root carries no `assets/` member (FR1, T-050-06) — memory Markdown
   carries no external image references; a diagram belongs in-doc as a fenced Mermaid
   block. `ARCHITECTURE.md`'s own `## Architecture Diagrams` section is the pattern.
5. **Forbidden in memory Markdown:**
   - `<h2>Changelog</h2>`, `<h2>History</h2>`, `<h2>Histórico</h2>`, `<h2>Versions</h2>`
   - `<section class="changelog">` and similar
   - Narrative of past versions ("we used to use X, now we use Y")

   If the operator asks for history, point to this release's `RELEASE.jsonl` or
   `_archive/`.
6. **Validate** with `dadaia specs doctor` before moving to archive. Doctor checks
   atomicity and Mermaid script presence.
7. **Product memory is a folder catalog** at `specs/memory/product/`, not a single file —
   a product has many features and bundling them overloads humans and wastes tokens for
   agents that need only one feature's depth.
   - `index.md` — entry point, read first: Vision (2–3 sentences), Users, the feature
     catalog in daily-relevance order (each entry links to `<feature-slug>.md`), a
     capability-map Mermaid diagram, and explicit non-goals (Limits). Plain Markdown
     headings — no HTML `<section>` wrapper.
   - `<area>/<feature-slug>.md` — one Markdown atom per production feature: Purpose (2–3
     paragraphs, functionally), Usage flow (3–5 numbered steps, optional Mermaid),
     Typical trigger (1 sentence), Differentiator (the problem it solves), Runtime state
     touched (files/dirs touched), Dependencies (run order) — English canon,
     `.heading-allowlist`.
   - The top-level trio's scaffold source is
     `dadaia_workspace/public/scaffold/memory/ARCHITECTURE.md`,
     `dadaia_workspace/public/scaffold/memory/TECHSTACK.md` (source and dest share the
     name — no `.j2` templating); product atoms are authored directly as Markdown
     during release closure.
   - Update `index.md` only if the catalog order changed or a feature was added/removed;
     update affected feature atoms; leave the rest intact. A new feature gets its atom
     created and linked from `index.md`; a deprecated feature's link is removed and its
     atom moves to `_archive/legacy-memory/<timestamp>/`.

*Done when:* every affected atom reflects current product truth, `dadaia specs doctor`
reports the memory atoms clean, and the `phase` record (RELEASE.jsonl + dual-written
`ACTIVE.md`) reads `CLOSURE`.
