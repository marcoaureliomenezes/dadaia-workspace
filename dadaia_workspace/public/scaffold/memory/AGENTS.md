# specs/memory/AGENTS.md — Memory Rules

Scope: `specs/memory/**`; broader SDD rules are in the sibling `specs/AGENTS.md`.

Memory is current product truth: it describes the product as it is now, never how it got
there — read it before changing production behavior. History lives in each release's
`_RELEASE.json` `log` entries, under `_archive/`, and in git.

## 1. Write ownership

| Action | Allowed |
|---|---|
| Read any atom | every agent, any phase |
| Write/edit any atom | `project-manager` only, in `DEFINITION` or `CLOSURE` phase |
| Edit by any other agent | never, in any phase |

- Neither half is gated: `specs/memory/**` is MUTATING in every phase; both are agent discipline, measured by the audit's memory pillar.
- Stale memory found mid-implementation becomes a bug or a closure note, never an in-place patch.

## 2. The two tiers

`ARCHITECTURE.md`, `TECHSTACK.md`, `QUALITY.md` each carry exactly two top-level (`##`) parts, in this order:

| Part | Holds | Changes how |
|---|---|---|
| `## Part 1 — Principles` | the fundamental, ADR-gated rules of the product | only in the commit that carries its accepted ADR |
| `## Part 2 — Implementation` | modules, diagrams, flows, dependencies, boundaries, tunables | freely, at every DEFINITION/CLOSURE, no ADR needed |

### 2.1 Part 1 admission rule

- A principle is admitted only with an existing mechanical check that fails when violated.

```markdown
### P-NN · <statement, in the form "We …">
Measured by: `<the exact command that measures it>`
ADR: NNNN (proposed) | none
Rationale: <one line — why this rule exists>
```

- `Measured by:` names a check that already runs — a doctor code, a contract test, a lint contract, a CI job.
- A rule nobody can measure is not a principle — it is Part-2 description or a proposed ADR.
- `ADR: <id>` points at a `decisions.jsonl` record and reads `(proposed)` until the operator accepts it.

### 2.2 Part 2 is the living description

- Where a rule without a measure lands, where every diagram lives, and where a number with a home elsewhere is referenced rather than restated.

### 2.3 Never silently

- Moving a block between parts, or deleting one, is recorded row by row in the reviewer's coverage table and its handoff: old section -> new home, or `deleted: <reason>`.

### 2.4 `product/` atoms are functional descriptions only

- What a feature does for its user, its boundaries, its current behavior.
- An architecture principle or implementation tour found in a `product/` atom belongs in Part 1/2 of the trio instead.

## 3. Tree shape

| Path | Holds |
|---|---|
| `ARCHITECTURE.md` | top-level — system structure, layers, dispatch topology |
| `TECHSTACK.md` | top-level — languages, runtimes, dependencies |
| `QUALITY.md` | top-level — QA contract and test policy |
| `product/index.md` | human entry point for the product catalog |
| `product/catalog.json` | machine index, regenerated from atom frontmatter |
| `product/<area>/<slug>.md` | one product-truth atom per feature/area |

- `TECHSTACK.md`'s `Snapshot` bullets stay at the top of its Part 2 — the bootstrap hook injects only the leading lines.

```bash
dadaia memory catalog generate
```

## 4. Atom format

- YAML frontmatter validated against `memory-frontmatter-v1`; all 5 fields required: `slug`, `title`, `tldr`, `summary`, `tags`.
- `additionalProperties: false` makes any stray field a hard error.
- Body uses curated headings only (`lint-memory-atoms` allowlist); in the trio those are exactly the two Part headings, every former section an `###` subsection.
- `[[slug]]` wikilinks resolve by slug at any depth; never hardcode paths.
- No `Changelog`, `History` or version-log section — truth only, never narrative.

## 5. Validation

```bash
dadaia doctor --context <ctx>
```

- Fix findings at the source atom — never hand-edit `catalog.json` to silence a check, regenerate it instead.

Generated from `dadaia_workspace/public/scaffold/memory/AGENTS.md`.
Project teams may customize this file; `dadaia doctor` reports drift instead of overwriting it.
