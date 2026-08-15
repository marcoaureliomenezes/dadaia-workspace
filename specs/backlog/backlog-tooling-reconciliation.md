---
title: "Backlog tooling reconciliation: point the per-entry-file tooling at single-source BACKLOG.md (incl. the Consumes checklist consumer)"
status: picked
opened: 2026-08-15
description: >-
  v0.10.0 shipped the ADR #14 doctrine (law + dd-backlog-definition schema): the backlog
  converges to one specs/backlog/BACKLOG.md with an ACTIVE section and a LEDGER section.
  The tooling still implements the per-entry-file model end to end (v0.10.0 SPEC §4.5,
  operator-ratified deferral): features/backlog/{doctor,ledger,ledger_writer,preview,
  removal_lifecycle}.py, the `dadaia backlog new`/`backlog doctor` CLI verbs
  (new_artifacts.py + newartifacts.py), SPEC-DOC-031 in doctor_governance.py, the
  BL-SCHEMA/BL-STALE codes, public/scaffold/backlog/README.md, and
  public/data/CONSUMER_VALIDATION_RECIPE.md. Reconcile all of it with the single-source
  schema. FOLDED IN (intake report #2 item 2-2, approved as merge): dd-release-definition
  §5 keeps the `**Consumes:**` protocol as a checklist requirement while no CLI verb
  invokes removal_lifecycle.py — its former caller was the deleted workflow engine — so a
  required release-definition step has no executor; this release must either ship the CLI
  consumer for the removal lifecycle or rewrite the checklist to the mechanism that
  actually runs.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/backlog/doctor.py#run_backlog_doctor
    change: >-
      Validate the single-source BACKLOG.md (ACTIVE subsection schema, LEDGER line
      grammar, terminal disposition tokens) instead of per-entry files; keep
      BL-SCHEMA/BL-STALE/BL-CONFLICT semantics over the new physical shape.
  - subject:
      kind: cli
      ref: backlog new
    change: >-
      Author a new ACTIVE subsection in BACKLOG.md (title/opened/status/description/
      provenance) instead of scaffolding a per-entry file.
  - subject:
      kind: code
      ref: dadaia_workspace/features/backlog/removal_lifecycle.py#BacklogRemovalLifecycle
    change: >-
      2-2 fold: give consume_at_release_definition/remove_at_closure a live CLI consumer
      (or retire them in favor of the documented manual disposition sweep) so the
      dd-release-definition §5 `**Consumes:**` checklist item is executable again;
      reconcile purge-on-pick and LEDGER writing with the BACKLOG.md shape.
  - subject:
      kind: code
      ref: dadaia_workspace/features/backlog/preview.py#load_backlog_items
    change: >-
      Load items from BACKLOG.md ACTIVE subsections (one item per subsection) instead of
      globbing per-entry files; intents/anchor binding preserved.
  - subject:
      kind: code
      ref: dadaia_workspace/features/specs/doctor_governance.py#_BACKLOG_AGGREGATE_FILES
    change: >-
      Re-target SPEC-DOC-031 (and any sibling backlog-governance checks) at BACKLOG.md;
      drop checks that only make sense for per-entry files.
---

# Backlog tooling reconciliation — per-entry model → single-source BACKLOG.md

## Description

See frontmatter. Scope enumerated by v0.10.0 SPEC §4.5 (the operator-ratified
deferral): the five `features/backlog/*` modules, the `backlog new`/`backlog doctor`
verbs, SPEC-DOC-031, the BL-* codes, `public/scaffold/backlog/README.md` (left
deliberately untouched by v0.10.0 — rewriting it before the tooling changes would ship
consumers a README describing a model the CLI does not implement, SPEC §4 item 10), and
`public/data/CONSUMER_VALIDATION_RECIPE.md`.

Folded scope — **2-2, Consumes-checklist-without-consumer** (intake report #2, code-review
pre-PR `2026-08-15T145731Z`, LOW): `dd-release-definition/SKILL.md` §5 requires a
`**Consumes:**` declaration and checklist tick while nothing invokes
`features/backlog/removal_lifecycle.py` (former caller: the deleted workflow engine).
Until this release, the live mechanism is the manual disposition sweep documented in
`dd-release-closure`; this release closes the gap structurally.

## Motivation

R6 of the v0.10.0 SPEC named the risk explicitly: the doctrine outruns the tooling — the
law describes `BACKLOG.md` while the CLI writes and validates per-entry files. Every
release cycle that passes widens the drift and forces the PM to hand-maintain two shapes.
`software-engineer` surface (production Python + scaffolding), distinct from the PM
curation half tracked in `backlog-md-physical-consolidation`, which this entry unblocks
and sequences before.

## Acceptance criteria

- `dadaia backlog new` and `dadaia backlog doctor` operate on single-source `BACKLOG.md`
  (ACTIVE + LEDGER per `dd-backlog-definition` §2); `backlog doctor` is clean on the
  consolidated file and BL-SCHEMA fires on a malformed ACTIVE subsection.
- The `**Consumes:**` release-definition checklist item has a named, working executor:
  either a CLI verb wired to `BacklogRemovalLifecycle` or a rewritten checklist pointing
  at the manual sweep — no required step without an executor (2-2 closed).
- SPEC-DOC-031 (and sibling governance checks) validate the consolidated shape; zero
  stale checks against per-entry files remain.
- `public/scaffold/backlog/README.md` and `public/data/CONSUMER_VALIDATION_RECIPE.md`
  describe the shipped model; `dadaia public doctor` green including `[ok]
  public-privacy`.
- Full test suite green; tests over per-entry fixtures migrated, not deleted (test
  stewardship rules apply).

## Provenance

Pre-approved intake P-1 (operator ratification D-A at v0.10.0 approval, SPEC §4.5/§4.10)
+ item 2-2 approved as merge. Trace: operator-delegated adjudication, 2026-08-15 (goal
directive), verdicts per PM recommendation — intake report #2
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T152234Z-intake.html`).

## Ownership

`software-engineer` implements (its own release round per the D-A ratification);
`product-engineer` authors the release SPEC; PM sequences
`backlog-md-physical-consolidation` with/after this.

## Pick provenance (v0.12.0)

**picked — v0.12.0**, 2026-08-15. Delivered as **FR1–FR6 + FR8** of release `v0.12.0`
"backlog-tooling-single-source", together with `backlog-md-physical-consolidation` (FR7) in
**one** release and **one atomic cutover commit** (operator ruling **D1**). Provenance
record: `specs/releases/v0.12.0/SPEC.md` §7; grill: `specs/releases/v0.12.0/GRILL.md`.

**The 2-2 fold is resolved by RETIREMENT** (operator ruling **D2**, verdict from grill P1).
Inspection at `feature/v0.12.0` found `removal_lifecycle.py`, `removal.py`,
`ledger_writer.py`, `consumes.py` and `container.build_backlog_removal_lifecycle` with
**zero** production callers — the former caller was the workflow engine deleted in v0.3.0,
which explicitly kept the modules — and found `apply_removal`'s defined behaviour (rewrite
down to residual, or archive-then-unlink) to **contradict** the never-delete law it was built
to serve, since under the single-source model an item never leaves the file. The write side
is deleted with its four test modules (recorded supersessions, not silent pruning);
`ledger.py`'s `read_consumed` survives as a live BL-STALE input over the 18 historical
sidecars. `dd-release-definition` §5 is rewritten to the mechanism that runs: `**Consumes:**`
is SPEC provenance, executed by the PM's purge-on-pick and the `dd-release-closure`
disposition sweep, backstopped by `backlog doctor` BL-STALE and `specs doctor` SPEC-DOC-031.

Two grill decisions bind this entry beyond its own text: **D7** — `intents[]`/anchor binding
is **preserved** (this entry's own `preview.py` intent asked for it, while the ratified
`dd-backlog-definition` §2 schema has no intents key; the conservative option was taken and
flagged as **OD-1**), carried as one optional `**Intents:**` subsection key; and **D8** —
BL-STALE is re-defined as "an ACTIVE item already consumed or dispositioned". Terminal
disposition `DELIVERED — v0.12.0` lands at closure, as a `LEDGER` line in the consolidated
`BACKLOG.md`.
