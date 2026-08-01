---
name: drift-detection
description: >
  Reference for project-auditor agent. Protocol for comparing specs/memory/*.md
  to actual implementation, dead-code detection methodology, 1–10 compliance
  scoring rubric across 6 dimensions, and dadaia CLI integration.
applyTo: ".dadaia/reports/**"
---

# drift-detection — Memory ↔ Implementation Drift Audit

> **This skill is the procedure.** `project-auditor` runs it directly; there is no
> engine that runs it for you. The audit's product is evidence, and the
> `audit-without-disposition` doctor invariant is what keeps that evidence from being
> filed and forgotten.

## Memory Atom Inventory

All spec memory is stored as atomic Markdown files (`*.md`, with YAML frontmatter)
under `<specs-dir>/memory/`. Load each atom in order; read the Markdown directly.

| Atom | Path | What it declares | Sections of interest |
|---|---|---|---|
| Architecture | `memory/architecture.md` | Layers, module boundaries, ADRs, data-flow topology | `#layers`, `#adr-log`, `#module-map` |
| Product catalog | `memory/product/index.md` | Feature catalog (one entry per shipped feature) | `#catalog` |
| Feature detail | `memory/product/<slug>.md` | Acceptance criteria, behavior spec, edge cases per feature | `#criteria`, `#behavior` |
| Tech stack | `memory/tech-stack.md` | Languages, frameworks, versions, tooling, rationale | `#stack`, `#tooling` |

Rules for loading:
- Load `architecture.md` and `tech-stack.md` on every audit.
- Load `product/index.md` first; then load individual feature files only for features
  that are in-scope for the current audit.
- Never use `_archive/` atoms as the authoritative source.
- If an atom is missing, that is itself a drift finding (severity HIGH).

---

## Drift Detection Method

### Step 1 — Layer Sample Walk

For each architectural layer declared in `architecture.md`:

1. List the declared responsibilities and module paths.
2. `find <repo-root>/<module-path> -type f -name "*.py" -o -name "*.ts" | head -20`
3. Read 3–5 representative files per layer.
4. Compare: does the code structure match the declared layer responsibilities?

Record each mismatch as a drift item with evidence on both sides (spec:line + code:line).

### Step 2 — Feature Cross-Reference

For each feature in `memory/product/index.md`:

1. Extract the acceptance criteria from `memory/product/<slug>.md`.
2. Locate the corresponding implementation file(s) via:
   ```bash
   grep -rn "<feature-keyword>" <repo-root>/src --include="*.py" -l
   ```
3. Read the implementation. Verify each acceptance criterion is satisfied.
4. If a criterion has no implementation evidence: drift item, severity HIGH.
5. If implementation has behavior not in any criterion: drift item, severity LOW
   (possible undocumented feature or cruft).

### Step 3 — Tech-Stack Cross-Reference

For each declared dependency in `tech-stack.md`:

1. Verify it appears in `pyproject.toml` / `package.json` / `go.mod`.
2. Verify the pinned version matches the declared version.
3. Check for dependencies in lockfiles that are not declared in the memory atom.

```bash
# Python — compare declared vs installed
cat pyproject.toml | grep -A50 "\[tool.poetry.dependencies\]"
pip show <package> | grep Version

# Node
jq '.dependencies' package.json
cat package-lock.json | jq '.packages["node_modules/<pkg>"].version'
```

---

## Dead-Code Detection

### Unused Python Symbols

```bash
# vulture: find unused code
pip install vulture
vulture <src-dir> --min-confidence 80

# or with ruff
ruff check <src-dir> --select F401,F811,F841
```

### Unused TypeScript/JavaScript Exports

```bash
# ts-prune: find unused exports
npx ts-prune --project tsconfig.json

# or knip
npx knip
```

### Dangling Imports

```bash
# Python
grep -rn "^import \|^from " <src-dir> | sort | uniq
# Cross-reference against actual usage; an import with no usage in the file is drift

# Node
npx depcheck --json
```

### Unreachable Layers

A layer is "unreachable" if no other layer imports from it AND it is not an
entry point. Detect with:

```bash
# Python import graph
pip install pydeps
pydeps <src-dir> --max-bacon 3 --show-deps
```

Flag any module with zero importers and no declared entry-point role as a
dead-layer candidate.

---

## Compliance Scoring Rubric (1–10)

Score each dimension independently. Use the anchors at 1 / 4 / 7 / 10 as
calibration points; interpolate for intermediate values.

### Dimension A — Architecture

| Score | Anchor |
|---|---|
| 10 | Every module in code maps exactly to a declared layer; no cross-layer violations; all ADRs reflected |
| 7 | Minor violations (1–2 files in wrong layer); ADRs mostly reflected; no undeclared external deps |
| 4 | Significant layer mixing; 1–2 ADRs ignored; architecture docs lagging by 1 release |
| 1 | Architecture memory does not reflect code; layers not enforced; no ADR log maintained |

### Dimension B — Product Features

| Score | Anchor |
|---|---|
| 10 | Every criterion in every feature slug file has a passing test and matching implementation |
| 7 | 90%+ criteria covered; 1–2 minor behaviors undocumented |
| 4 | 70–89% criteria covered; several edge cases missing from impl or from memory |
| 1 | < 50% criteria covered; feature memory significantly outdated |

### Dimension C — Tech Stack

| Score | Anchor |
|---|---|
| 10 | All deps declared in memory; versions match lockfile exactly |
| 7 | 1–2 minor version discrepancies; no undeclared prod deps |
| 4 | Several undeclared deps in lockfile; versions drifted |
| 1 | Tech-stack memory does not reflect actual tooling |

### Dimension D — Security

| Score | Anchor |
|---|---|
| 10 | OWASP checklist green; no secrets in repo; all auth patterns correct |
| 7 | No CRITICAL/HIGH findings; 1–2 MEDIUMs with mitigations planned |
| 4 | 1 HIGH finding open; or 3+ MEDIUMs unmitigated |
| 1 | CRITICAL open; secrets in repo; auth bypasses present |

### Dimension E — Test Coverage

| Score | Anchor |
|---|---|
| 10 | ≥ 90% line coverage; every public API has unit + integration tests |
| 7 | 75–89% coverage; all critical paths tested |
| 4 | 50–74% coverage; some public functions untested |
| 1 | < 50% coverage; core features untested |

### Dimension F — Design / UX

| Score | Anchor |
|---|---|
| 10 | WCAG 2.2 AA fully compliant; design system tokens used consistently; no one-off values |
| 7 | WCAG AA met; 1–2 minor token deviations |
| 4 | Several WCAG failures; inconsistent token usage |
| 1 | No accessibility audit performed; design system not followed |

---

## Aggregation Formula

```
weighted_avg = (A×0.20 + B×0.25 + C×0.15 + D×0.20 + E×0.15 + F×0.05)

floor_score  = min(A, B, C, D, E, F)

final_score  = min(weighted_avg, floor_score + 2)
```

The floor term prevents a very low score on any single dimension from being
hidden by high scores elsewhere. A floor of 3 caps the final score at 5.

---

## dadaia CLI Integration

```bash
# Validate 11 SDD structural invariants (memory atomicity, CLOSURE evidence, etc.)
dadaia specs doctor

# Verify all public lib projections are installed and hash-matched
dadaia public doctor

# Resolve active context and specs_dir
dadaia context show --json

# Example: extract specs_dir from context show
SPECS_DIR=$(dadaia context show --json | python3 -c "import sys,json; print(json.load(sys.stdin)['specs_dir'])")
```

Run `dadaia specs doctor` and `dadaia public doctor` at the start of every audit.
Any `[ERROR]` output is a drift finding in its own right (dimension depends on
which invariant failed).

---

## Drift Item Template

```
ID: DRIFT-<n>
Dimension: A (Architecture) | B (Product) | C (Tech-Stack) | D (Security) | E (Tests) | F (Design)
Severity: CRITICAL | HIGH | MEDIUM | LOW
Description: <what is drifted and why it matters>
Spec evidence: <specs-dir>/memory/<atom>.md#<section> — "<quoted text>"
Code evidence: <repo-root>/<path>:<line> — "<quoted snippet>"
Recommendation: <specific action to close the drift>
Proposed owner: <agent responsible for the fix>
```

---

## Recommendation Policy

| Condition | Recommendation |
|---|---|
| final_score ≥ 8 | Healthy — no action required; schedule next audit at CLOSURE of next release |
| 6 ≤ final_score < 8 | Minor drift — create backlog items; address in next release |
| 5 ≤ final_score < 6 | Moderate drift — recommend a dedicated tech-debt release via `project-manager` |
| final_score < 5 | Significant drift — recommend immediate hotfix release; escalate to `product-engineer` |
| Any dimension score < 3 | Floor breach — mandatory escalation regardless of weighted average |

When recommending a release, emit a `next_handoff` in the `.handoff.json` handoff
with `agent: "project-manager"` and a summary of the drift areas requiring a release.
