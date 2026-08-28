---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates the v6 canon tree, memory and catalog integrity, RELEASE.json, bug and backlog governance, and audit findings folded from JSONL.
summary: "`dadaia specs doctor` coordinates structural, memory, release, closure/audit, governance and coherence validators over the v6 canon; it reports and never blocks, and `--fix` performs only deterministic repairs."
tags:
- specs
- doctor
- validation
- sdd
---

## Validator families

Specs doctor verifies that SDD artifacts are structurally and semantically coherent before release
advancement or closure. It **reports**; the enforcement lane is the gate and the publication
boundary ([[sdd-gate-v3]]).

- **`TREE-*` and repo hygiene** — canonical tree, required rule files, no repo-local runtime or
  cache state. **TREE-8** is the v6 canon-root check: every top-level entry directly under `specs/`
  must be one of `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`, `ADRs/`, `constitution.md`,
  `AGENTS.md`. It is WARN-only, scoped to root membership, and ignores dotfiles.
- **`SPEC-DOC-*` release checks** — the active release and phase, artifact presence and
  `**Status:** Aprovado`, task-marker coherence, SemVer naming, unique release ids, archive-shape
  and partial-archive-residue invariants, release references. The active release, its optional
  segment and its phase are read from `RELEASE.json` through one reader with no `ACTIVE.md`
  fallback; zero live release directories resolves cleanly to "no active release". A missing segment
  directory is an ERROR, never a silent skip.
- **Memory checks** — Markdown/frontmatter/atomicity, forbidden history sections, image and Mermaid
  references, generated catalog/index agreement, and unfilled `<PLACEHOLDER>` tokens in memory atoms
  (ERROR) or an **installed** `tests/AGENTS.md` (WARN), never in the canonical template, which ships
  parameterized. `CAT-1` reconciles catalog entries against atom files by **slug set**, so which
  optional fields the persisted catalog carries is outside what it asserts ([[context-management]]).
- **Governance checks** — **SPEC-DOC-033** reads `BUGS.jsonl` through the shared record reader,
  reporting a line that does not parse as a native record (ERROR) and a coherence gap on a native
  record (WARNING). **SPEC-DOC-041** is the archive-overdue signal at 90 days. **SPEC-DOC-031**
  flags an active item left non-terminal while an archived release asserts it was consumed, and
  counts consumption rather than conversation — the only asserting shape is an archived SPEC's
  `**Consumes:**` declaration, with candidate slugs isolated as whole tokens, backstopped from the
  ledger side by BL-STALE. **SPEC-DOC-035** is the single-source invariant: any item file loose
  directly under `specs/backlog/`, other than `BACKLOG.json` and its scoped rule file, is drift. The
  entry schema belongs to `backlog doctor`'s BL-* codes.
- **Closure/audit checks** — **SPEC-DOC-036** and **SPEC-DOC-038** fold `FINDINGS.jsonl`, never
  audit prose: an `open` finding inside an archived audit is an ERROR, and a live audit whose
  findings are all terminal and each name a disposing release is an archive-due WARNING. An archived
  audit predating the findings schema is skipped and named in one collective WARNING. SPEC-DOC-030
  checks the collision-safe audit directory shape.
- **Constitution/version checks** — required invariant references and `specs_pattern_version` 6.

**No checker outlives the file it parses**: every `CLOSURE.md` parser is deleted rather than
adapted. The split across doctors is by subject — `public doctor` carries the privacy-baseline
carve-out rationale check, `dadaia doctor` owns every workspace-state invariant
([[workspace-doctor]]), `backlog doctor` owns the backlog document model — with no second opinion
here and no lease or session-coherence validator. `--recipe` renders ordered, copy-pasteable steps
over the same finding objects `--json` emits, every step tracing to a finding id in that run;
`--fix` regenerates deterministic catalog/tree artifacts and normalizes supported archive layout,
inventing no approval, task completion, evidence, disposition or operator decision.

## Dependencies

[[sdd-bug-backlog-governance]], [[audits-canon]], [[workspace-doctor]], [[sdd-gate-v3]].
