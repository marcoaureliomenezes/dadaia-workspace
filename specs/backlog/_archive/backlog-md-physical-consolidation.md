---
title: "Physical BACKLOG.md consolidation: per-entry files + candidates.md → single-source ACTIVE + LEDGER"
status: picked
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

## Pick provenance (v0.12.0)

**picked — v0.12.0**, 2026-08-15. Delivered as **FR7** of release `v0.12.0`
"backlog-tooling-single-source", in the **same** release as
`backlog-tooling-reconciliation` (operator ruling **D1**). Provenance record:
`specs/releases/v0.12.0/SPEC.md` §7; grill: `specs/releases/v0.12.0/GRILL.md`.

**The sequencing question this entry raised is settled by an atomic cutover, not by
ordering.** Grill P3 established that neither order is green: consolidating first makes the
per-entry loader parse `BACKLOG.md` as an item with slug `BACKLOG` (a BL-SCHEMA ERROR in the
pre-commit gate and CI), and shipping the tooling first leaves 31 live files unvalidated for
a window. The document, the tooling wiring, the loader deletion and the governance re-target
therefore ride **one commit** (T-120-08), with every pure module landing before it against
fixtures.

**Never-delete becomes countable** (operator ruling **D4**, form fixed by grill P15): the
slug set discoverable before the consolidation — live entry files ∪ `candidates.md`
candidate/idea rows ∪ `_archive/` files ∪ LEDGER lines ∪ terminal-table rows — must equal the
slug set in `BACKLOG.md` after it, each slug exactly once and in exactly one section, with
both set differences captured as evidence. Measured baseline: 31 live files, 30 live rows,
46 archived files, 20 LEDGER lines. Per **D5**, the superseded per-entry files **and**
`candidates.md` leave by `git mv` into `specs/backlog/_archive/` — archived, never deleted —
and SPEC-DOC-035 is re-pointed at the single-source invariant (no per-entry item file loose
under `specs/backlog/`). One live drift is reconciled here rather than absorbed silently:
`tag-push-carve-out-reachability` (grill P6) resolves to **LEDGER only**. Terminal
disposition `DELIVERED — v0.12.0` lands at closure.
