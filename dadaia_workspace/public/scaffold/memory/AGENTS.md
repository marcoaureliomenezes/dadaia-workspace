# specs/memory/AGENTS.md — Memory Rules

Scope: this file governs only the `specs/memory/**` tree of one Spec Context
Project. Broader SDD rules are in the sibling `specs/AGENTS.md`.

Memory is **product truth**: it describes the product as it is now, never how it
got there. History lives in each release's `RELEASE.json` `log` entries and
under `_archive/`. Memory is the grounding context every agent reads before
implementation, review, or report work.

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

## The Two Tiers

`ARCHITECTURE.md`, `TECHSTACK.md` and `QUALITY.md` each carry **exactly two
top-level (`##`) parts, in this order**:

| Part | Holds | Changes how |
|---|---|---|
| `## Part 1 — Principles` | the fundamental, ADR-gated rules of the product | only in the commit that carries its accepted ADR |
| `## Part 2 — Implementation` | modules, diagrams, flows, dependencies, boundaries, tunables | freely, at every DEFINITION/CLOSURE, no ADR needed |

**Part 1 admission rule.** A principle is admitted only with an existing
mechanical check that fails when it is violated. Each entry is:

```markdown
### P-NN · <statement, in the form "We …">
Measured by: `<the exact command that measures it>`
ADR: NNNN (proposed) | none
Rationale: <one line — why this rule exists>
```

`Measured by:` names a check that already runs — a doctor code, a contract test,
a lint contract, a CI job. A rule nobody can measure is **not** a principle: it
is Part-2 description or a proposed ADR, never a `P-NN`. An ADR is written when a
Part-1 principle is created or changed — never one file per principle that merely
exists. `ADR: <id>` points at a `ADRs/decisions.jsonl` record (shape:
`specs/ADRs/AGENTS.md`) and reads `(proposed)` until the operator accepts it; a
principle predating this canon carries `ADR: none` until the change that next touches
it mints one. **Only the operator flips a decision to `accepted`** — an agent that
writes `accepted` has violated the law.

**Part 2 is the living description.** It is where a rule without a measure lands
when it survives, where every diagram lives, and where a number that has a home
elsewhere (a pinned test constant, `pyproject.toml`, a skill's `PARAMETERS.md`)
is referenced rather than restated — one number per parameter.

**Never silently.** Moving a block between parts, or deleting one, is recorded
row by row in the release's coverage table under
`specs/releases/<id>/reviews/`: old section → new home, or `deleted: <reason>`.

**`product/` atoms are functional descriptions only** — what a feature does for
its user, its boundaries and its current behavior. An architecture principle or
an implementation tour found in a `product/` atom belongs in Part 1 or Part 2 of
the trio; the atom keeps the functional half.

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
Mermaid block (`ARCHITECTURE.md`'s own diagram subsections are the pattern); memory
Markdown carries no external image references.

`TECHSTACK.md`'s `Snapshot` bullets stay at the top of its Part 2: the
once-per-session bootstrap (`hooks/ctx_inject.py`) injects only the leading lines
of that atom, so content pushed below them leaves the digest.

Regenerate the machine index after any atom path change:

```bash
dadaia memory catalog generate
```

## Atom Format

- YAML frontmatter validated against `memory-frontmatter-v1`
  (`dadaia_workspace/public/schemas/memory/memory-frontmatter-v1.schema.json`).
  All 6 fields are required: `slug`, `title`, `category`, `tldr`, `summary`,
  `tags` — and
  `additionalProperties: false` makes any stray field a hard error.
  `agent_tier` is **rejected** by the schema (deprecated v0.1.53, schema-dropped
  in v0.1.61) — do not include it. The catalog computes the atom's size from its
  body — no stored size field belongs in frontmatter.
- Body uses curated headings only — the `lint-memory-atoms` allowlist governs
  which h2 sections are valid. In the trio those are exactly the two Part
  headings; every former section lives on as an `###` subsection inside a part.
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
