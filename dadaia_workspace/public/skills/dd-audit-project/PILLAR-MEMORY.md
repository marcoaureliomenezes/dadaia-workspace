# PILLAR-MEMORY — memory and constitution drift

Disclosed sibling of `SKILL.md`, pillar 3. Input: the memory trio's Part 1 (`ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md`).
Also input: `specs/memory/product/**` atoms and `specs/constitution.md`, over the audit window.

## 1 — Every Part-1 principle, run through its own named check

1. For each `P-NN` entry across the three Part-1 sections, execute exactly the check its own `Measured by:` line names.
2. Record the result: pass, fail, or "check does not run" — the last is itself a finding against whoever authored the principle.
3. Flag a principle carrying no `Measured by:` line, or accepted with no `Accepted by: ADR NNNN`, as a finding on its own.
4. Report the finding only — fixing it is memory FR17/FR18 territory, not this pillar's.

## 2 — "Part 1 principle changed without an accepted ADR"

```bash
git log -p --since="<window start>" -- specs/memory/ARCHITECTURE.md specs/memory/QUALITY.md specs/memory/TECHSTACK.md
```

1. For every hunk touching a `## Part 1 — Principles` section, find the `accepted` ADR it should pair with.
2. The same commit (or the immediately preceding one, per FR19) must add/update a `docs(adr): accept NNNN-<slug>`.
3. That ADR's own text must name the changed principle.
4. An unmatched hunk is a HIGH finding — Part 1 is ADR-gated by law, and this is the only mechanical check for it.
5. Exception: the first-inventory case — read `specs/ADRs/AGENTS.md`'s "Relationship to memory and audits" section before scoring a CREATING commit.

## 3 — Product atoms and Part-2 implementation vs code

Reused, unscored, from the retired six-dimension audit — evidence-gathering technique, never a weighted score.

1. Layer sample walk: for each layer `ARCHITECTURE.md`'s Part 2 declares, list its module paths, sample 3-5 files.
2. Layer sample walk: compare structure to the declared responsibility; record a mismatch as `spec:line` vs `code:line`.
3. Feature cross-reference: for each `product/<area>/<slug>.md` atom, locate and read its implementation.
4. Feature cross-reference: check every functional claim against the code.
5. A claim with no implementation evidence is HIGH; code behavior absent from any atom is LOW (undocumented surface).
6. Tech-stack cross-reference: for each dependency `TECHSTACK.md`'s Part 2 declares, confirm it and its pinned version in the manifest.
7. Tech-stack cross-reference: check the lockfile for an undeclared dependency the memory atom is silent on.

## 4 — Dead-code detection (folded from the retired `TOOLING.md`)

Supports the Part-2/product-atom walk — a module claimed live in memory but actually unreachable is drift.
Every install pins an exact version/hash, never `latest`.

```bash
# Unused Python symbols
ruff check <src-dir> --select F401,F811,F841
pip install vulture==2.14 && vulture <src-dir> --min-confidence 80

# Unused TS/JS exports
npx ts-prune@0.10.3 --project tsconfig.json   # or: npx knip@5.36.3

# Dangling imports (Node)
npx depcheck@1.4.7 --json

# Unreachable layers
pip install pydeps==3.0.1 && pydeps <src-dir> --max-bacon 3 --show-deps
```

- Flag a zero-importer, no-entry-point-role module as a dead-layer candidate.

## 5 — `constitution.md` violations

- Check every absolute law in `constitution.md` against the window's commits and current tree state.
- A violated absolute law is a CRITICAL finding by definition — nothing in this workspace is permitted to contradict it.

## Findings

- Every check above emits `pillar: "memory"` records via `FINDINGS-FORMAT.md`'s shape.
