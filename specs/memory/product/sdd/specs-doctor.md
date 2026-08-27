---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates the v6 canon tree, memory and catalog integrity, the RELEASE.jsonl fold, bug and backlog governance, and audit findings folded from JSONL.
summary: >-
  `dadaia specs doctor` coordinates structural, memory, release, closure/audit, governance and
  coherence validators over the v6 canon. TREE-8 reports anything under `specs/` outside the
  canon root as a WARNING, never a block, and `--recipe` renders ordered copy-pasteable steps
  hanging off the same finding objects `--json` emits, from its own function. The active
  release and its phase are the fold of `RELEASE.jsonl` with no fallback branch, a duplicate
  sha-bearing milestone is a warning, and every `CLOSURE.md` parser is deleted rather than left
  behind its retired subject. The audit checks fold `FINDINGS.jsonl` instead of regexing prose,
  and the bug lane reads the one canonical ledger through the shared record reader. Placeholder
  detection covers memory atoms as an error and an installed tests rule file as a warning,
  never the canonical template. A live segment pointer at a missing segment directory is an
  explicit error, never a silent skip. `--fix` performs only deterministic repairs.
tags:
- specs
- doctor
- validation
- sdd
last_updated: '2026-08-27'
release_origin: 0.5.0
---

## Purpose

Specs doctor verifies that SDD artifacts are structurally and semantically coherent before
release advancement or closure. It **reports**; it does not block. Every check it owns is a
diagnosis an agent or the operator acts on — the enforcement lane is the gate and the
publication boundary, not this verb.

## Validator Families

- `TREE-*` and repo hygiene: canonical tree, required rule files, and no repo-local
  runtime/cache state. **TREE-8 is the v6 canon-root check** — every top-level entry directly
  under `specs/` must be one of `backlog/`, `bugs/`, `memory/`, `releases/`, `audits/`,
  `ADRs/`, `constitution.md`, `AGENTS.md`, and nothing else. It is **WARN-only** and never
  changes the exit code: a canon that exits non-zero on a migration-in-progress tree is exactly
  the slop the canon exists to remove. Its scope is root membership; the shape of an area's own
  members is left to that area's checks. Dotfiles are ignored.
- `SPEC-DOC-*` release checks: the active release and phase, artifact presence and
  `**Status:** Aprovado`, task-marker coherence, SemVer naming, unique release ids, the
  archive-shape and partial-archive-residue invariants, and release references. **The active
  release, its optional segment and its phase are resolved by folding `RELEASE.jsonl`** — one
  reader owns that disk read, and no `ACTIVE.md` fallback branch survives; a workspace with
  zero live release directories resolves cleanly to "no active release". **SPEC-DOC-043**
  warns on a duplicate sha-bearing milestone: `defined`/`implemented`/`shipped` are immutable
  facts, the fold keeps the first record of each kind and this check surfaces every later one,
  at WARNING severity with the exit code unchanged.
- memory checks: Markdown/frontmatter/atomicity, forbidden history sections, image and Mermaid
  references, generated catalog/index agreement, and unfilled `<PLACEHOLDER>` tokens.
  Placeholder detection covers two document families with one validator shape: memory atoms
  (ERROR), and an **installed** `tests/AGENTS.md` still carrying angle-bracket tokens (WARN,
  naming the file). The second is scoped to the installed consumer file and **never** to the
  canonical template, which ships parameterized by design — a check that fired on the template
  could not be satisfied by any legal action. The trio's pre-migration lowercase names are
  recognised by the orphan check so a consumer tree mid-rename is not reported twice.
- governance checks: the bug-ledger invariant and the backlog single source.
  **SPEC-DOC-033** reads the one canonical `specs/bugs/BUGS.jsonl` through the same shared
  record reader the feature uses — never a second hand-kept parser, never `str.splitlines()`
  — and reports two things: a line that does not parse as a native record (a surviving v5
  `"event"`-keyed line reads "v5 line in a v6 ledger — migrate", an ERROR), and a coherence
  gap on a native record (resolved with no `cause`/`caused_by`/`resolved_release`, superseded
  with no `superseded_by`) as a WARNING with the exit code unchanged. **SPEC-DOC-041** is the
  archive-overdue signal: terminal records past the 90-day threshold still live in the ledger,
  WARN only. Two checks cover the backlog, both WARNING: SPEC-DOC-031 iterates the `## ACTIVE`
  subsections of the live-photo `BACKLOG.md` and flags an item left non-terminal while an
  archived release **asserts** it was consumed; SPEC-DOC-035 is the single-source invariant —
  any item `*.md` loose directly under `specs/backlog/`, other than `BACKLOG.md` and its scoped
  rule file and excluding `_archive/`, is drift. No check reads `BACKLOG.md` as if it were a
  per-slug entry, so no finding is ever keyed to a phantom slug. There is no per-entry
  frontmatter schema check: the entry schema belongs to `backlog doctor`'s BL-* codes, and
  specs doctor holds no second opinion on it.
- closure/audit checks: **SPEC-DOC-036 and SPEC-DOC-038 fold `FINDINGS.jsonl`**, never audit
  prose. An `open` finding inside an archived audit is an ERROR — an audit archives only once
  every finding is terminal. A live audit whose findings are all terminal and each name a
  disposing release is an archive-due WARNING. An archived audit predating the findings schema
  carries no `FINDINGS.jsonl`, is skipped by the fold, and is named in one collective WARNING
  rather than treated as an error. SPEC-DOC-030 checks the collision-safe audit directory
  shape, whose pattern has a single home in `core/workspace_layout.py`.
- constitution/version checks: required invariant references and pattern-version compatibility
  (`specs_pattern_version` 6).

**No checker outlives the file it parses.** `CLOSURE.md` retired with `ACTIVE.md`, and every
parser that read it is **deleted** rather than adapted — the closure-completeness check, the
disposition-marker regexes, the archived-closure disposition evidence, and the release-artifact
constant that named it. A check standing guard over a file that no longer exists is dead code
behind a dead artifact, which is the shape the canon change exists to stop. `SPEC.md`,
`PLAN.md` and `TASKS.md` are the release artifacts a directory is judged on.

SPEC-DOC-031 counts **consumption, not conversation**. The one shape that asserts a release
consumed a slug is an archived SPEC's `**Consumes:**` declaration, continuation lines included.
Candidate slugs are isolated as whole tokens, so a slug that is merely a substring of a longer
word or of another slug never matches. Every other mention — a non-goal, a provenance note, an
inheritance remark, any prose at all — asserts nothing, which is why the check carries no
section-exclusion list to maintain. The consequence is deliberate: it under-detects a genuinely
consumed slug whose SPEC never declared it, and that accepted false negative costs less than
the false positives any free-text match would produce. Severity stays WARNING, backstopped from
the ledger side by `backlog doctor`'s BL-STALE.

Because only archived documents assert consumption, a closure's own archive move is what makes
its assertions countable: a release that archives while naming a still-non-terminal `ACTIVE`
slug adds one warning per such slug, measured **after** the move.

**A missing segment directory is an ERROR, never a silent skip.** When the release fold carries
a `segment`, both the release-artifact check (`SPEC-DOC-004`) and the tree check (`TREE-6`)
route into `releases/<release>/<segment>/`. If that directory does not exist, each raises an
explicit ERROR naming it. It is not covered elsewhere: the release-level check validates only
the release directory, so returning quietly there disabled artifact-presence and
`**Status:** Aprovado` validation for the whole release at once. A doctor that goes blind is
worse than one that goes loud. The refusal is scoped to a live segment pointer; a flat release
fires nothing here.

The doctor is not the only checker in this family, and the split is by subject. `dadaia public
doctor` carries the privacy-baseline **carve-out rationale** check: an `exclude_regex` with no
`exclude_rationale` is reported on every run ([[sdd-gate-v3]]). `dadaia doctor` owns every
**workspace-state** invariant — the `.dadaia/` layout allowlist, repository coherence, and the
registry-wide repo-slug ownership check `INV-6` ([[workspace-doctor]]). `dadaia backlog doctor`
owns the backlog document model's own BL-* codes. Specs doctor holds no second opinion on any
of them: it validates SDD documents.

There is no lease/session-coherence validator. Workspace concurrency state is advisory presence
and belongs to `dadaia doctor`.

The memory validators are unchanged by the catalog's injection-tier curation: `CAT-1`
reconciles catalog entries against atom files by **slug set**, so which optional fields the
persisted catalog carries is outside what it asserts ([[context-management]]).

## Usage

```bash
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia specs doctor --json
.dadaia/.venv/bin/dadaia specs doctor --recipe
.dadaia/.venv/bin/dadaia specs doctor --fix
```

`--recipe` renders ordered, concrete, copy-pasteable steps for the findings a migration cannot
execute automatically. It is a **rendering of the same finding objects `--json` already
emits** — the recipe text hangs off each finding, never a second step table that could drift
from the findings — and it renders in its **own** function, never inside the doctor command
body. A run with zero findings emits zero steps, and every step traces to a finding id present
in the same run's `--json` output. The canon's case-only file renames are recipe steps executed
by hand: `specs upgrade` is deliberately not grown to automate them, and both its and the
doctor's complexity are pinned by a measured ratchet.

`--fix` may regenerate deterministic catalog/tree artifacts and normalize supported archive
layout. It does not invent approval, task completion, evidence, dispositions, or operator
decisions.

## Dependencies

[[sdd-bug-backlog-governance]], [[audits-canon]], [[workspace-doctor]], [[sdd-gate-v3]].
