---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates the v6 canon tree, memory and catalog integrity, the RELEASE.jsonl fold, bug and backlog governance, and audit findings folded from JSONL.
summary: "`dadaia specs doctor` coordinates structural, memory, release, closure/audit, governance and coherence validators over the v6 canon; it reports and never blocks, and `--fix` performs only deterministic repairs."
tags:
- specs
- doctor
- validation
- sdd
---

## Purpose

Specs doctor verifies that SDD artifacts are structurally and semantically coherent before
release advancement or closure. It **reports**; the enforcement lane is the gate and the
publication boundary ([[sdd-gate-v3]]).

## Validator families

- **`TREE-*` and repo hygiene** — canonical tree, required rule files, no repo-local
  runtime or cache state. **TREE-8** is the v6 canon-root check: every top-level entry
  directly under `specs/` must be one of `backlog/`, `bugs/`, `memory/`, `releases/`,
  `audits/`, `ADRs/`, `constitution.md`, `AGENTS.md`. It is WARN-only and never changes the
  exit code; its scope is root membership, and dotfiles are ignored.
- **`SPEC-DOC-*` release checks** — the active release and phase, artifact presence and
  `**Status:** Aprovado`, task-marker coherence, SemVer naming, unique release ids, the
  archive-shape and partial-archive-residue invariants, and release references. The active
  release, its optional segment and its phase are resolved by folding `RELEASE.jsonl`
  through one reader, with no `ACTIVE.md` fallback; zero live release directories resolves
  cleanly to "no active release". **SPEC-DOC-043** warns on a duplicate sha-bearing
  milestone, exit code unchanged.
- **Memory checks** — Markdown/frontmatter/atomicity, forbidden history sections, image
  and Mermaid references, generated catalog/index agreement, and unfilled `<PLACEHOLDER>`
  tokens. Placeholder detection covers memory atoms (ERROR) and an **installed**
  `tests/AGENTS.md` still carrying angle-bracket tokens (WARN, naming the file); it never
  fires on the canonical template, which ships parameterized. `CAT-1` reconciles catalog
  entries against atom files by **slug set**, so which optional fields the persisted
  catalog carries is outside what it asserts ([[context-management]]).
- **Governance checks** — **SPEC-DOC-033** reads `specs/bugs/BUGS.jsonl` through the same
  shared record reader the feature uses and reports a line that does not parse as a native
  record (a surviving v5 `"event"`-keyed line, ERROR) and a coherence gap on a native
  record (WARNING, exit code unchanged). **SPEC-DOC-041** is the archive-overdue signal at
  the 90-day threshold, WARN only. Two WARNING checks cover the backlog: **SPEC-DOC-031**
  flags an `## ACTIVE` item left non-terminal while an archived release asserts it was
  consumed, and **SPEC-DOC-035** is the single-source invariant — any item `*.md` loose
  directly under `specs/backlog/`, other than `BACKLOG.md` and its scoped rule file and
  excluding `_archive/`, is drift. There is no per-entry frontmatter schema check; the
  entry schema belongs to `backlog doctor`'s BL-* codes.
- **Closure/audit checks** — **SPEC-DOC-036** and **SPEC-DOC-038** fold `FINDINGS.jsonl`,
  never audit prose: an `open` finding inside an archived audit is an ERROR, and a live
  audit whose findings are all terminal and each name a disposing release is an
  archive-due WARNING. An archived audit predating the findings schema is skipped by the
  fold and named in one collective WARNING. SPEC-DOC-030 checks the collision-safe audit
  directory shape, whose pattern lives in `core/workspace_layout.py`.
- **Constitution/version checks** — required invariant references and
  `specs_pattern_version` 6.

**No checker outlives the file it parses.** Every `CLOSURE.md` parser is deleted rather
than adapted; `SPEC.md`, `PLAN.md` and `TASKS.md` are the release artifacts a directory is
judged on.

SPEC-DOC-031 counts **consumption, not conversation**: the only shape asserting a release
consumed a slug is an archived SPEC's `**Consumes:**` declaration, continuation lines
included, with candidate slugs isolated as whole tokens. Every other mention asserts
nothing, so the check carries no section-exclusion list. It under-detects a consumed slug
whose SPEC never declared it, backstopped from the ledger side by `backlog doctor`'s
BL-STALE.

**A missing segment directory is an ERROR, never a silent skip.** When the fold carries a
`segment`, both `SPEC-DOC-004` and `TREE-6` route into `releases/<release>/<segment>/` and
each raises an explicit ERROR naming a directory that does not exist. A flat release fires
nothing here.

The split across doctors is by subject: `public doctor` carries the privacy-baseline
carve-out rationale check, `dadaia doctor` owns every workspace-state invariant
([[workspace-doctor]]), and `backlog doctor` owns the backlog document model's BL-* codes.
Specs doctor holds no second opinion on any of them, and there is no lease or
session-coherence validator.

## Usage

```bash
.dadaia/.venv/bin/dadaia specs doctor [--json | --recipe | --fix]
```

`--recipe` renders ordered, copy-pasteable steps for findings a migration cannot execute
automatically. It is a rendering of the same finding objects `--json` emits, from its own
function: a run with zero findings emits zero steps, and every step traces to a finding id
in the same run's `--json`. `--fix` may regenerate deterministic catalog/tree artifacts and
normalize supported archive layout; it invents no approval, task completion, evidence,
disposition or operator decision.

## Dependencies

[[sdd-bug-backlog-governance]], [[audits-canon]], [[workspace-doctor]], [[sdd-gate-v3]].
