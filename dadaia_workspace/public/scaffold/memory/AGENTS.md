# specs/memory/AGENTS.md — Memory Rules

Scope: `specs/memory/**`; broader SDD rules are in the sibling `specs/AGENTS.md`.

Memory is current product truth: what the product is now, never how it got there.

## 1. The two tiers

| Tier | Files | Changes how |
|---|---|---|
| Canonical memory | `ARCHITECTURE.md`, `QUALITY.md` | only in the commit carrying its accepted ADR; text (never a statement) may be rewritten by an audit or on the operator's explicit order |
| Product memory | `product/<area>/<slug>.md` | at every closure, by `dd-product-engineer`, reconciled from the window's code diff |

- No other agent edits memory in any phase; `specs/memory/**` is MUTATING for the hook, the doctor and the audit's memory pillar measure the discipline.
- Stale memory found mid-implementation becomes a bug or a closure note, never an in-place patch.

## 2. Canonical memory

- `ARCHITECTURE.md`: `## Principles`, `## Tech Stack`, `## Structure`. `QUALITY.md`: `## Principles`, `## Test architecture`, `## Gates`. Fixed `<!-- dadaia:fixed … -->` blocks keep their place.
- `## Tech Stack` is one line per technology, 8 to 15 lines — a soft ceiling a large stack may exceed, never with prose.
- A principle needs an existing mechanical check that fails when violated: `### P-NN · We …` / `Measured by:` (a doctor code, contract test, lint contract or CI job) / `ADR: NNNN (proposed|accepted) | none` / `Rationale:` one line. An unmeasurable rule is a proposed ADR, not a principle.
- Moving or deleting a statement is recorded row by row in the reviewer's coverage table: old section -> new home, or `deleted: <reason>`.

## 3. Product memory — reconciled, never appended

- An atom describes what a feature does for its user, its boundaries, its current behavior; an architecture principle found in one belongs in canonical memory.
- Every atom declares `sources:` — the repo path globs of the code it describes; `catalog.json` carries them.
- At closure, `MEMORY_PY drift --since <sha>` lists the atoms whose sources changed and the packages no atom covers. Per listed atom, read the sources' `git diff`, then in this order: DELETE every claim the code no longer supports, UPDATE every claim that changed, only then ADD what is new. An uncovered package gets its atom; a dead feature's atom is deleted outright.
- The pass ends with `RELEASE_PY memory --since <sha> --worklist <drift.json> --reviewed … --changed …`; it refuses an uncovered worklist, and `dadaia doctor` (`RELEASE-TREE-MEMORY`) keeps the candidate red until the entry exists.

## 4. Tree, format, validation

- `MEMORY_PY` = `python3 .agents/skills/dd-spec-navigator/scripts/memory.py`; `RELEASE_PY` = `python3 .agents/skills/dd-release-implementation/scripts/release.py`.
- `product/index.md` and `product/catalog.json` are generated together by `MEMORY_PY catalog generate`; an atom is added by writing its file, which `MEMORY_PY check` validates.
- Frontmatter `memory-frontmatter-v1`: `slug`, `title`, `tldr`, `summary`, `tags` on every atom, `sources` on every product atom; a stray field is a hard error.
- Body: curated headings only; `[[slug]]` wikilinks resolve by slug, never a path; no history heading, and no history line — a date or a release, candidate or task id anywhere, or a history phrase in a product atom, is `MEM-NARRATIVE-1`.
- The bootstrap hook injects `ARCHITECTURE.md`'s `## Tech Stack` section and the catalog digest.
- Fix findings at the source atom; never hand-edit `catalog.json`, regenerate it.

Generated from this release's scaffold image. Project teams may customize this file; `dadaia doctor` reports drift instead of overwriting it.
