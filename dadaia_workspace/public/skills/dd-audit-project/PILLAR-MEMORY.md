# PILLAR-MEMORY — memory and constitution drift

Disclosed sibling of `SKILL.md`, pillar 3. Input: the memory trio's Part 1 sections
(`ARCHITECTURE.md`, `QUALITY.md`, `TECHSTACK.md`), `specs/memory/product/**` atoms, and
`specs/constitution.md`, over the audit window (`SKILL.md`'s window section).

## 1 — Every Part-1 principle, run through its own named check

For each `P-NN` entry across the three Part-1 sections, execute exactly the check its
own `Measured by:` line names (a `lint-imports` contract, a contract test node id, a
doctor check code, a ratchet script) and record the result — pass, fail, or "check does
not run" (the last is itself a finding against whoever authored the principle, never a
skipped row). A principle carrying no `Measured by:` line, or one accepted with no
`Accepted by: ADR NNNN`, is a finding on its own (memory FR17/FR18 territory, not this
pillar's to fix — only to report).

## 2 — "Part 1 principle changed without an accepted ADR"

```bash
git log -p --since="<window start>" -- specs/memory/ARCHITECTURE.md specs/memory/QUALITY.md specs/memory/TECHSTACK.md
```

For every hunk that touches a `## Part 1 — Principles` section, find the `accepted` ADR
it should be paired with: the same commit (or the immediately preceding one, per FR19's
"accept commit also carries the Part-1 memory hunk") must add or update a
`docs(adr): accept NNNN-<slug>` under `specs/ADRs/`, and that ADR's own text must name
the changed principle. An unmatched hunk is a **HIGH** finding — Part 1 is ADR-gated by
law, and this is the only mechanical check that law has.

## 3 — Product atoms and Part-2 implementation vs code (the retained drift-walk method)

Reused, unscored, from the retired six-dimension audit — the walk survives here as
evidence-gathering technique, never as a weighted score:

- **Layer sample walk.** For each layer `ARCHITECTURE.md`'s Part 2 declares: list its
  module paths, sample 3–5 files
  (`find <repo-root>/<module-path> -name "*.py" | head -20`, then read), and compare
  structure to the declared responsibility. Record a mismatch as `spec:line` vs
  `code:line` evidence.
- **Feature cross-reference.** For each `product/<area>/<slug>.md` atom: locate its
  implementation (`grep -rn "<feature-keyword>" <repo-root>/src -l`), read it, and check
  every functional claim against the code. A claim with no implementation evidence is a
  finding (HIGH); code behavior absent from any atom is a finding (LOW — undocumented
  surface).
- **Tech-stack cross-reference.** For each dependency `TECHSTACK.md`'s Part 2 declares:
  confirm it in `pyproject.toml`/`package.json` and confirm the pinned version, then
  check the lockfile for an undeclared dependency the memory atom is silent on.

## 4 — Dead-code detection (folded from the retired `TOOLING.md`)

Supports the Part-2/product-atom walk above — a module claimed live in memory but
actually unreachable is itself a drift finding. Every install pins an exact
version/hash, never `latest` (the same supply-chain discipline production dependencies
already follow):

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

Flag a zero-importer, no-entry-point-role module as a dead-layer candidate.

## 5 — `constitution.md` violations

Check every absolute law in `constitution.md` against the window's commits and current
tree state; a violated absolute law is a **CRITICAL** finding by definition — it is the
one document nothing in this workspace is permitted to contradict.

## Findings

Every check above emits `pillar: "memory"` records via `FINDINGS-FORMAT.md`'s shape.
