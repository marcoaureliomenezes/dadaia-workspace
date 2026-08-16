---
slug: specs-doctor
title: specs-doctor
category: product
tldr: Validates canonical specs structure, memory/catalog integrity, release markers, closure evidence, dispositions, bug ledgers, and audit coherence.
summary: >-
  `dadaia specs doctor` coordinates structural, memory, release, closure/audit,
  governance, and coherence validators. `--fix` performs only deterministic repairs.
tags:
- specs
- doctor
- validation
- sdd
token_estimate: 355
last_updated: '2026-08-15'
release_origin: v0.3.0
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
  Mermaid references, generated catalog/index agreement.
- governance checks: event-sourced bug JSONL vocabulary and terminal state; the backlog
  single source. Two checks cover the backlog, both **WARNING**: SPEC-DOC-031 iterates the
  `## ACTIVE` subsections of `specs/backlog/BACKLOG.md` and flags an item left at a
  non-terminal status while an archived SPEC or CLOSURE names its slug outside a
  `## Backlog returns` section; SPEC-DOC-035 is the single-source invariant — any item
  `*.md` loose directly under `specs/backlog/`, other than `BACKLOG.md` and `README.md`
  and excluding `_archive/` and `remote-bugs/`, is drift. No check reads `BACKLOG.md` as
  if it were a per-slug entry, so no finding is ever keyed to a phantom `BACKLOG` slug.
  There is no per-entry frontmatter schema check: the entry schema is validated by
  `backlog doctor`'s BL-* codes over the document model, and specs doctor does not hold a
  second opinion on it.
- constitution/version checks: required invariant references and pattern-version
  compatibility.

There is no lease/session-coherence validator. Workspace concurrency state is advisory
presence and belongs to `dadaia doctor`, not specs doctor.

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
