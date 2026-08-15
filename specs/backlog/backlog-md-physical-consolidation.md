---
title: "Physical BACKLOG.md consolidation: per-entry files + candidates.md → single-source ACTIVE + LEDGER"
status: candidate
opened: 2026-08-15
description: >-
  Execute the physical half of the ADR #14 convergence that v0.10.0 shipped as doctrine
  (law §5 Backlog + dd-backlog-definition §2): fold every live per-entry file under
  specs/backlog/*.md plus the candidates.md index into ONE specs/backlog/BACKLOG.md with
  an ACTIVE section (one strict-schema subsection per live candidate: Title, Opened,
  Status, Description, Provenance) and a LEDGER section (one line per closed item
  carrying its terminal disposition token). Never-delete law holds throughout: every
  terminal row from candidates.md and _archive/ frontmatter gets a LEDGER line; no
  record is lost. PM curation surface (specs/backlog/** is project-manager-owned).
  Sequences WITH/AFTER backlog-tooling-reconciliation — consolidating before the tooling
  ships would break `backlog new`/`backlog doctor`/SPEC-DOC-031, which still read and
  validate per-entry files (v0.10.0 SPEC §4.4/D5 + §4.5, R6).
intents:
  - subject:
      kind: doc
      ref: memory/product/sdd/sdd-bug-backlog-governance.md#Backlog
    change: >-
      The runtime-state reality matches the atom's single-source BACKLOG.md doctrine:
      specs/backlog/ carries BACKLOG.md (ACTIVE + LEDGER) as the format of record; the
      per-entry files and candidates.md are consolidated in, with provenance lines
      preserved per entry; the atom's pending-consolidation note is retired at the
      consolidating release's CLOSURE.
---

# Physical BACKLOG.md consolidation

## Description

See frontmatter. The doctrine (target schema, disposition vocabulary, purge-on-pick,
operator-gated intake) shipped in v0.10.0; the physical shape did not — candidates.md
and the per-entry files remain the format of record until this executes
(candidates.md header, addendum 2026-08-15).

## Motivation

Two formats of record is a standing discipline hazard: every curation touch pays a
double-write, and the law describes a file that does not physically exist yet. The
consolidation is deliberate PM work — entry numbering, ledger folding of three tables
(terminal-at-materialization, rejected, history) and per-entry provenance all require
curation judgment, not a script.

## Acceptance criteria

- `specs/backlog/BACKLOG.md` exists with `## ACTIVE` (strict `dd-backlog-definition` §2
  subsection schema) and `## LEDGER`; every live candidate and idea is an ACTIVE
  subsection; every terminal row/entry from candidates.md, `_archive/` frontmatter and
  the history table has a LEDGER line with its disposition token.
- Zero information loss: each ACTIVE subsection carries a Provenance line traceable to
  its origin (operator request or intake-report item + approval date).
- Per-entry `.md` files and `candidates.md` are archived by `git mv` (FROZEN discipline,
  SPEC-DOC-035 style), never deleted.
- `dadaia backlog doctor` and `dadaia specs doctor` are clean on the consolidated shape
  (hence the sequencing dependency on `backlog-tooling-reconciliation`).

## Provenance

Pre-approved intake P-2 (operator ratification D-A at v0.10.0 approval; SPEC §4.4/D5).
Trace: operator-delegated adjudication, 2026-08-15 (goal directive), verdicts per PM
recommendation — intake report #2
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`project-manager` executes (backlog curation surface); depends on
`backlog-tooling-reconciliation` (`software-engineer`) for the tooling that validates
the consolidated file.
