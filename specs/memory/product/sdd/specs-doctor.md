---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates canonical specs structure, memory/catalog and placeholder integrity, release/segment markers, closure evidence, dispositions, bugs, and audits.
summary: >-
  `dadaia specs doctor` coordinates structural, memory, release, closure/audit,
  governance, and coherence validators. Placeholder detection covers memory atoms (ERROR)
  and an installed tests/AGENTS.md (WARN, never the canonical template). A live segment
  pointer at a missing segment directory is an explicit ERROR, never a silent skip.
  `--fix` performs only deterministic repairs.
tags:
- specs
- doctor
- validation
- sdd
last_updated: '2026-08-27'
release_origin: v0.4.2
---

## Purpose

Specs doctor verifies that SDD artifacts are structurally and semantically coherent
before release advancement or closure.

## Validator Families

- `TREE-*` and repo hygiene: canonical tree, required rule files, and no repo-local
  runtime/cache state.
- `SPEC-DOC-*` release checks: ACTIVE/release id/phase/status, task-marker coherence,
  closure evidence triples, archive shape, backlog and bug dispositions, consumed
  ledgers, audit naming, and release references.
- memory checks: Markdown/frontmatter/atomicity, forbidden history sections, image and
  Mermaid references, generated catalog/index agreement, and unfilled `<PLACEHOLDER>`
  tokens. Placeholder detection covers two document families with one validator shape:
  memory atoms (ERROR), and an **installed** `tests/AGENTS.md` still carrying angle-bracket
  tokens (WARN, naming the file). The second is scoped to the installed consumer file and
  **never** to the canonical template, which ships parameterized by design — a check that
  fired on the template could not be satisfied by any legal action.
- governance checks: event-sourced bug JSONL vocabulary and terminal state; the backlog
  single source. Two checks cover the backlog, both **WARNING**: SPEC-DOC-031 iterates the
  `## ACTIVE` subsections of `specs/backlog/BACKLOG.md` and flags an item left at a
  non-terminal status while an archived release **asserts** it was consumed; SPEC-DOC-035
  is the single-source invariant — any item
  `*.md` loose directly under `specs/backlog/`, other than `BACKLOG.md` and `README.md`
  and excluding `_archive/` and `remote-bugs/`, is drift. No check reads `BACKLOG.md` as
  if it were a per-slug entry, so no finding is ever keyed to a phantom `BACKLOG` slug.
  There is no per-entry frontmatter schema check: the entry schema is validated by
  `backlog doctor`'s BL-* codes over the document model, and specs doctor does not hold a
  second opinion on it.
- constitution/version checks: required invariant references and pattern-version
  compatibility.

SPEC-DOC-031 counts **consumption, not conversation**. Exactly two shapes assert that a
release consumed a slug, and only they are read: an archived SPEC's `**Consumes:**`
declaration, continuation lines included, and an archived CLOSURE's `## Dispositions` table
rows. Candidate slugs are isolated as whole tokens, so a slug that is merely a substring of a
longer word or of another slug never matches. Every other mention — a non-goal, a provenance
note, an inheritance remark, a returns section, any prose at all — asserts nothing and is
never evidence, which is why the check carries no section-exclusion list to maintain. The
consequence is deliberate: the check under-detects a genuinely consumed slug whose SPEC never
declared it, and that accepted false negative costs less than the false positives any
free-text match over the same documents would produce. Severity stays WARNING, backstopped
from the ledger side by `backlog doctor`'s BL-STALE.

Because only archived documents assert consumption, a closure's own archive move is what
makes its assertions countable: a release that archives while naming a still-non-terminal
`ACTIVE` slug adds one warning per such slug, measured **after** the move.

**A missing segment directory is an ERROR, never a silent skip.** When `ACTIVE.md` carries
a non-`none` `segment:`, both the release-artifact check (`SPEC-DOC-004`) and the tree
check (`TREE-6`) route into `releases/<release>/<segment>/`. If that directory does not
exist, each raises an explicit ERROR naming the missing segment directory. It is not
covered elsewhere: the ACTIVE.md check validates only the **release** directory and never
the segment subdirectory, so returning quietly there disabled artifact-presence and
`**Status:** Aprovado` validation for the whole release at once. A doctor that goes blind
is worse than one that goes loud. The refusal is scoped to a live segment pointer: a flat
release is genuinely covered by the release-directory check and fires nothing here.

The doctor is not the only checker in this family, and the split is by subject. `dadaia
public doctor` carries the privacy-baseline **carve-out rationale** check: an
`exclude_regex` with no `exclude_rationale` is reported on every run, so a carve-out nobody
can explain cannot sit in the baseline unnoticed ([[sdd-gate-v3]]). `dadaia doctor` owns
every **workspace-state** invariant — the `.dadaia/` layout allowlist, repository
coherence, and the registry-wide repo-slug ownership check `INV-6` ([[workspace-doctor]]).
Specs doctor holds no second opinion on any of them: it validates SDD documents.

There is no lease/session-coherence validator. Workspace concurrency state is advisory
presence and belongs to `dadaia doctor`, not specs doctor.

The memory validators are unchanged by the catalog's injection-tier curation: `CAT-1`
reconciles catalog entries against atom files by **slug set**, so which optional fields the
persisted catalog carries is outside what it asserts ([[context-management]]).

## Usage

```bash
.dadaia/.venv/bin/dadaia specs doctor
.dadaia/.venv/bin/dadaia specs doctor --fix
```

`--fix` may regenerate deterministic catalog/tree artifacts and normalize supported
archive layout. It does not invent approval, task completion, evidence, dispositions, or
operator decisions.

## Dependencies

[[sdd-bug-backlog-governance]], [[workspace-doctor]], [[sdd-gate-v3]].
