---
name: dd-audit-project
description: "project-auditor's audit protocol: memory-atom inventory, the drift-detection method, dead-code detection, the 6-dimension scoring rubric, and evidence-agent dispatch through the audit-to-release lifecycle."
applyTo: ".dadaia/reports/**"
disable-model-invocation: true
---

# dd-audit-project — Memory ↔ Implementation Drift Audit

> **Not a hook-enforced mechanism.** There is no workflow engine that runs the audit
> stage or its gates. `project-auditor` drives this protocol directly, dispatched by
> the operator or a dispatching agent. This skill is the authoritative protocol.

## Memory Atom Inventory

All spec memory is stored as atomic Markdown files (`*.md`, with YAML frontmatter)
under `<specs-dir>/memory/`. Load each atom in order; read the Markdown directly.

| Atom | Path | What it declares | Headings of interest |
|---|---|---|---|
| Architecture | `memory/ARCHITECTURE.md` | Layers, module boundaries, subsystems, runtime state, dependencies | `Primary Subsystems`, `Concurrency`, `Runtime State` |
| Product catalog | `memory/product/index.md` | Feature catalog (one entry per shipped feature) | catalog listing (Markdown headings, no `<section>` wrapper) |
| Feature detail | `memory/product/<area>/<slug>.md` | Purpose, usage flow, trigger, differentiator, runtime state, dependencies per feature | `Purpose`, `Usage flow`, `Differentiator`, `Dependencies` |
| Tech stack | `memory/TECHSTACK.md` | Languages, frameworks, versions, tooling, rationale | `Snapshot`, `Canonical Commands`, `Packaging Notes` |

Rules for loading:
- Load `ARCHITECTURE.md` and `TECHSTACK.md` on every audit.
- Load `product/index.md` first; then load individual feature files only for features
  that are in-scope for the current audit.
- Never use `_archive/` atoms as the authoritative source.
- If an atom is missing, that is itself a drift finding (severity HIGH).

---

## Evidence-Agent Dispatch

`project-auditor` never gathers primary evidence itself — it dispatches specialists
(parallel-capable where supported) and consolidates. One agent per dimension:

| Dimension | Evidence agent | Supplies |
|---|---|---|
| A — Architecture | `software-architect` | layer-boundary / module-dependency drift vs `ARCHITECTURE.md` |
| B — Product Features | `software-engineer` | code-surface drift vs each feature's acceptance criteria |
| C — Tech Stack | `software-engineer` | dependency/version drift vs `TECHSTACK.md` and lockfiles |
| D — Security | `security-reviewer` | OWASP scan, CVEs, secrets, IaC findings |
| E — Test Detection Quality | `qa-engineer` | test-pyramid health, intent taxonomy, quarantine/SCAFFOLD state |
| F — Agent-surface | `ai-engineer` | prompt-efficiency / persona-shape drift vs `public/agents`, `public/skills`, `public/data` |

`code-reviewer` supplements A/E.

---

## Drift Detection Method

### Step 1 — Layer Sample Walk

For each architectural layer declared in `ARCHITECTURE.md`:

1. List the declared responsibilities and module paths.
2. `find <repo-root>/<module-path> -type f -name "*.py" -o -name "*.ts" | head -20`
3. Read 3–5 representative files per layer.
4. Compare: does the code structure match the declared layer responsibilities?

Record each mismatch as a drift item with evidence on both sides (spec:line + code:line).

### Step 2 — Feature Cross-Reference

For each feature in `memory/product/index.md`:

1. Extract the feature detail from `memory/product/<area>/<slug>.md`.
2. Locate the corresponding implementation file(s) via:
   ```bash
   grep -rn "<feature-keyword>" <repo-root>/src --include="*.py" -l
   ```
3. Read the implementation. Verify each acceptance criterion is satisfied.
4. If a criterion has no implementation evidence: drift item, severity HIGH.
5. If implementation has behavior not in any criterion: drift item, severity LOW
   (possible undocumented feature or cruft).

### Step 3 — Tech-Stack Cross-Reference

For each declared dependency in `TECHSTACK.md`:

1. Verify it appears in `pyproject.toml` / `package.json` / `go.mod`.
2. Verify the pinned version matches the declared version.
3. Check for dependencies in lockfiles that are not declared in the memory atom.

```bash
# Python — compare declared vs installed (dependency table name varies by build
# backend: [project.dependencies] PEP 621, [tool.poetry.dependencies] Poetry, etc.)
cat pyproject.toml
pip show <package> | grep Version

# Node
jq '.dependencies' package.json
cat package-lock.json | jq '.packages["node_modules/<pkg>"].version'
```

---

## Dead-Code Detection

Flag unused symbols, dangling imports and unreachable layers. Concrete tool
invocations (vulture/ruff, ts-prune/knip, depcheck, pydeps) and the version-pinning
rule they inherit: `TOOLING.md` (sibling).

---

## Compliance Scoring Rubric (1–10)

Six dimensions — A Architecture, B Product Features, C Tech Stack, D Security, E Test
Detection Quality, F Agent-surface. Score each independently against the 1/4/7/10
anchors declared in `RUBRIC.md` (sibling) — the one dimension list, reconciled with
`public/agents/project-auditor.md` (A26.3); neither file restates the anchor tables.

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

Command syntax is `dd-cli-library`'s (never restated here). Run `dadaia specs doctor`
and `dadaia public doctor` at the start of every audit; any `[ERROR]` output is a drift
finding in its own right (dimension depends on which invariant failed).

---

## Drift Item Template

```
ID: DRIFT-<n>
Dimension: A (Architecture) | B (Product) | C (Tech-Stack) | D (Security) | E (Tests) | F (Agent-surface)
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

---

## Lifecycle Wrapper

This section implements the audit-lifecycle law (`DADAIA.md` §6 Audits) — consult it for
the rule itself, not restated here. In practice: this audit's scorecard exists to seed
**one** remediation release, and archiving waits on that release closing every finding
out with a token, never on the scan alone. A `deferred`/`rejected` disposition routes
through the compiled intake report (`dd-backlog-definition` §5 — an operator-ratified
deferral taken at the remediation release's own approval is already pre-approved intake,
not re-adjudicated later).

**Finding → TASKS-row mapping.** Each `DRIFT-<n>` item maps 1:1 to a `TASKS.md` row citing
its id, so `dd-release-implement`'s `## Dispositions` sweep can trace every finding to its
terminal disposition token (`dd-backlog-definition` §2 — canonical vocabulary, not
repeated here). A finding with no `TASKS.md` row at SPEC approval is unaddressed — the
SPEC is not `Aprovado`-ready until every finding from this round is accounted for.
