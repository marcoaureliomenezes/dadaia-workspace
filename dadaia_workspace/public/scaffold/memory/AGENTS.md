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

The write-lock is enforced by the SDD gate. `product-engineer` is the sole
author of memory atoms; gate details are in `constitution.md §13`. Stale memory
found mid-implementation becomes a bug or a closure note — never patch it in
place outside the allowed phases.

## Tree Shape

| Path | Holds |
|---|---|
| `architecture.md` | top-level — system structure, layers, dispatch topology |
| `tech-stack.md` | top-level — languages, runtimes, dependencies |
| `quality-assurance.md` | top-level — QA contract and test policy |
| `product/index.md` | human entry point for the product catalog |
| `product/catalog.json` | machine index, regenerated from atom frontmatter |
| `product/<area>/<slug>.md` | one product-truth atom per feature/area |
| `assets/` | images referenced by atoms |

Regenerate the machine index after any atom path change:

```bash
dadaia memory catalog generate
```

## Atom Format

- YAML frontmatter with `name`, `description`, `agent_tier`, `token_estimate`,
  and any catalog fields the index expects.
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
