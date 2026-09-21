# MEMORY-UPDATE — dd-release-implementation (RC-FLOW step 5 detail)

Disclosed reference reached at `SKILL.md` step 6 — `dd-project-manager` reads this before touching any `specs/memory/**` atom at closure.

## Protocol

1. The live release is in `CLOSURE` phase (`python3 .agents/skills/dd-release-implementation/scripts/release.py phase CLOSURE --sha <sha>`) before any `specs/memory/**` write; the gate blocks it otherwise.
2. Apply the candidate's deltas to the corresponding `specs/memory/*.md` and `specs/memory/product/**` atoms.
3. Heading rule, forbidden history sections and the atom's shape: `specs/memory/AGENTS.md`.
4. Run `pytest tests/contract/test_docs_derived_from_memory.py` after the atom writes — a red row names the atom to re-read and the doc line to re-record.
5. Re-derive each red section of `README.md`, `llms.txt` and `docs/*.md` from its atom, and re-record its `derived-from` marker's `sha256:<12 hex>`.
6. Re-record in the SAME commit as the atom — a doc and its source move together, never in a follow-up commit.
7. `docs/cli.md` regenerates from `dadaia help tree` whenever the candidate changed a verb.

## Product memory is a folder catalog

- `specs/memory/product/` holds many small atoms, not a single file — bundling overloads humans and wastes agent tokens.
- `index.md` — entry point, read first: Vision (2-3 sentences), Users, the feature catalog in daily-relevance order.
- `index.md` (continued): each catalog entry links to `<feature-slug>.md`, plus a capability-map Mermaid diagram and explicit non-goals.
- `index.md` uses plain Markdown headings — no HTML `<section>` wrapper.
- `<area>/<feature-slug>.md` — one atom per production feature: Purpose (2-3 paragraphs), Usage flow (3-5 steps, optional Mermaid).
- `<area>/<feature-slug>.md` (continued): Typical trigger (1 sentence), Differentiator, Runtime state touched, Dependencies.
- Top-level trio's scaffold source: `dadaia_workspace/public/scaffold/memory/ARCHITECTURE.md` and `.../TECHSTACK.md` (no `.j2` templating).
- Update `index.md` only if the catalog order changed or a feature was added/removed; update affected atoms; leave the rest intact.
- A new feature gets its atom created and linked from `index.md`.
- A deprecated feature's link and its atom are deleted outright — memory carries no archive of its own (history lives in git).

*Done when:* every affected atom reflects current product truth, `dadaia doctor` reports the memory atoms clean, and one `kind: memory` log entry records atoms reviewed-unchanged vs changed.
