# specs/memory/AGENTS.md — Memory Rules

Scope: this file governs only the `specs/memory/**` tree of one Spec Context Project.
Broader SDD rules are in the sibling `specs/AGENTS.md`.

Memory is product truth: it describes the product as it is now, never how it got there.
History lives in each release's `RELEASE.json` `log` entries and under `_archive/`.

## 1. Write ownership

| Action | Allowed |
|---|---|
| Read any atom | every agent, any phase |
| Write/edit any atom | `product-engineer` only, in `DEFINITION` or `CLOSURE` phase |
| Edit by any other agent | never, in any phase |

- The SDD gate deterministically enforces only the phase half (`specs/memory/**` = MEMORY path class).
- The who half — `product-engineer` as sole author — is agent discipline, not gate-enforced.
- See `constitution.md §13` for the discipline statement.
- Stale memory found mid-implementation becomes a bug or a closure note — never patch it in place outside the allowed phases.

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
- An ADR is written when a Part-1 principle is created or changed.
- `ADR: <id>` points at a `decisions.jsonl` record and reads `(proposed)` until the operator accepts it.
- A principle predating this canon carries `ADR: none` until the change that next touches it mints one.
- Only the operator flips a decision to `accepted` — an agent that writes `accepted` has violated the law.

### 2.2 Part 2 is the living description

- Where a rule without a measure lands when it survives; where every diagram lives.
- Where a number that has a home elsewhere is referenced rather than restated — one number per parameter.

### 2.3 Never silently

- Moving a block between parts, or deleting one, is recorded row by row in the release's coverage table.
- Table lives under `specs/releases/<id>/reviews/`: old section -> new home, or `deleted: <reason>`.

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

- The v6 canon root carries no `assets/` member — a diagram is an in-doc fenced Mermaid block.
- `TECHSTACK.md`'s `Snapshot` bullets stay at the top of its Part 2 — the bootstrap hook injects only the leading lines.

```bash
dadaia memory catalog generate
```

## 4. Atom format

- YAML frontmatter validated against `memory-frontmatter-v1`; all 6 fields required: `slug`, `title`, `category`, `tldr`, `summary`, `tags`.
- `additionalProperties: false` makes any stray field a hard error.
- `agent_tier` is rejected by the schema (deprecated v0.1.53, schema-dropped v0.1.61) — do not include it.
- The catalog computes atom size from its body — no stored size field belongs in frontmatter.
- Body uses curated headings only — the `lint-memory-atoms` allowlist governs which h2 sections are valid.
- In the trio those are exactly the two Part headings; every former section lives on as an `###` subsection.
- `[[slug]]` wikilinks resolve by slug at any depth — do not hardcode paths.
- Mermaid diagrams are allowed for structure; keep them current with the body.
- No forbidden h2 sections: no `Changelog`, `History`, or version logs — truth only, not narrative.

## 5. Validation

```bash
dadaia specs doctor
```

- Doctor checks atom presence, the top-level trio, and catalog consistency.
- Fix findings at the source atom — never hand-edit `catalog.json` to silence a check, regenerate it instead.

Generated from `dadaia_workspace/public/data/memory-AGENTS.md`.
Project teams may customize this file; `dadaia specs doctor` reports drift instead of overwriting it.
