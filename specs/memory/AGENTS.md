# specs/memory/AGENTS.md — Memory Rules

Scope: the `specs/memory/**` tree of one Spec Context Project. Broader SDD rules are in the sibling
`specs/AGENTS.md`.

Memory is **product truth**: it describes the product as it is now, never how it got there. History
lives in each release's `RELEASE.json` closure log and under `_archive/`.

## Write ownership

Every agent reads any atom in any phase. Only `product-engineer` writes, and only in `DEFINITION` or
`CLOSURE`. Enforcement is split: the SDD gate enforces the **phase** half (`specs/memory/**` is the
MEMORY path class); the **who** half is agent discipline, since no hook can verify persona identity.
Stale memory found mid-implementation becomes a bug or a closure note, never an in-place patch
outside the allowed phases.

## The two tiers

`ARCHITECTURE.md`, `TECHSTACK.md` and `QUALITY.md` each carry exactly two top-level (`##`) parts, in
order: `## Part 1 — Principles` (ADR-gated, changed only in the commit carrying their accepted ADR)
and `## Part 2 — Implementation` (modules, diagrams, flows, dependencies, boundaries, tunables —
changed freely at any DEFINITION/CLOSURE). A principle is admitted only with an existing mechanical
check that fails when it is violated:

```markdown
### P-NN · <statement, in the form "We …">
Measured by: `<the exact command that measures it>`
ADR: none | NNNN (proposed|accepted)
Rationale: <one line — why this rule exists>
```

`Measured by:` names a check that already runs — a doctor code, a contract test, a lint contract, a
CI job. A rule nobody can measure is Part-2 description, never a `P-NN`. `ADR: none` marks a
pre-canon principle; otherwise `ADR: NNNN` points at the ADR record, one per principle. Any future
change to a principle requires a new ADR: an agent proposes, and **only the operator flips an ADR to
`accepted`.** Part 2 references a number whose home is elsewhere rather than restating it — one
number per parameter. Moving a block between parts, or deleting one, is recorded row by row in the
release's coverage table: old section → new home, or `deleted: <reason>`.

**`product/` atoms are functional descriptions only** — what a feature does, its boundaries, its
current behavior. An architecture principle or an implementation tour found in a `product/` atom
belongs in Part 1 or Part 2 of the trio.

## Tree shape and atom format

`ARCHITECTURE.md` (structure, layers, dispatch topology), `TECHSTACK.md` (languages, runtimes,
dependencies) and `QUALITY.md` (QA contract and test policy) sit at the root beside `product/`,
whose generated `index.md` and `catalog.json` index one `<area>/<slug>.md` atom per feature. The v6
canon root carries no `assets/` member: a diagram belongs in-doc as a fenced Mermaid block, and
memory Markdown carries no external image references. `TECHSTACK.md`'s `Snapshot` bullets stay at
the top of its Part 2, because `hooks/ctx_inject.py` injects only that atom's leading lines.
Regenerate the machine index after any atom path change with `dadaia memory catalog generate`.

- YAML frontmatter validated against `memory-frontmatter-v1`, carrying exactly `slug`, `title`,
  `category`, `tldr`, `summary`, `tags`; `additionalProperties: false` makes any stray field a hard
  error, and `tldr` stays at or below 160 characters.
- One `##` heading per section, no duplicates; `Changelog`, `History` and version-log sections are
  refused. In the trio the only `##` headings are the two Part headings.
- `[[slug]]` wikilinks resolve by slug at any depth; never hardcode a path.

Run `dadaia specs doctor` before closing spec work: it checks atom presence, the top-level trio and
catalog consistency. Fix findings at the source atom; never hand-edit `catalog.json` to silence a
check — regenerate it.

Generated from `dadaia_workspace/public/data/memory-AGENTS.md`. Project teams may customize this
file; `dadaia specs doctor` reports drift instead of overwriting it.
