# specs/memory/AGENTS.md — Memory Rules

Scope: this file governs only the `specs/memory/**` tree of one Spec Context
Project. Broader SDD rules are in the sibling `specs/AGENTS.md`.

Memory is **product truth**: it describes the product as it is now, never how it
got there. History lives in each release's `CLOSURE.md` and under `_archive/`.
Memory is the grounding context every agent reads before implementation, review,
or report work.

## Write Ownership

| Action | Allowed |
|---|---|
| Read any atom | every agent, any phase |
| Write/edit any atom | `product-engineer` only, in `DEFINITION` or `CLOSURE` phase |
| Edit by any other agent | never, in any phase |

Enforcement is split. The SDD gate deterministically enforces only the **phase**
half: `specs/memory/**` is the MEMORY path class, writable through file tools
only while the active phase is `DEFINITION` or `CLOSURE`. The **who** half —
`product-engineer` as sole author — is agent discipline, not gate-enforced (no
hook can verify persona identity); see `constitution.md §13`. Stale memory
found mid-implementation becomes a bug or a closure note — never patch it in
place outside the allowed phases.

## Tree Shape

| Path | Holds |
|---|---|
| `ARCHITECTURE.md` | top-level — system structure, layers, dispatch topology |
| `TECHSTACK.md` | top-level — languages, runtimes, dependencies |
| `QUALITY.md` | top-level — QA contract and test policy |
| `product/index.md` | human entry point for the product catalog |
| `product/catalog.json` | machine index, regenerated from atom frontmatter |
| `product/<area>/<slug>.md` | one product-truth atom per feature/area |

The v6 canon root carries no `assets/` member — a diagram belongs in-doc as a fenced
Mermaid block (`ARCHITECTURE.md`'s own `## Architecture Diagrams` section is the
pattern); memory Markdown carries no external image references.

Regenerate the machine index after any atom path change:

```bash
dadaia memory catalog generate
```

## Atom Format

- YAML frontmatter validated against `memory-frontmatter-v1`
  (`dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`).
  All 8 fields are required: `slug`, `title`, `category`, `tldr`, `summary`,
  `tags`, `last_updated`, `release_origin` — and
  `additionalProperties: false` makes any stray field a hard error.
  `agent_tier` was deprecated in v0.1.53 and schema-dropped in v0.1.61: the
  schema now rejects it (`additionalProperties: false`) — do not include it.
  The catalog computes the atom's size from its body — no stored size field
  belongs in frontmatter.
- Body uses curated headings only — the `lint-memory-atoms` allowlist governs
  which h2 sections are valid.
- `[[slug]]` wikilinks resolve by slug at any depth; do not hardcode paths.
- Mermaid diagrams are allowed for structure; keep them current with the body.
- No forbidden h2 sections: no `Changelog`, `History`, or version logs. Truth
  only, not narrative.

## Validation

Run before closing spec work:

```bash
dadaia specs doctor
```

Doctor checks atom presence, the top-level trio, and catalog consistency. Fix
findings at the source atom; never hand-edit `catalog.json` to silence a check —
regenerate it instead.

Generated from `dadaia_workspace/public/data/memory-AGENTS.md`. Project teams may
customize this file; `dadaia specs doctor` reports drift instead of overwriting it.
