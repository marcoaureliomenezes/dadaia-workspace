# Closure: Release — v0.1.26 — `backlog_definition` workflow body + removal-on-release (R2 of FEAT-BACKLOG-DEFINITION-WORKFLOW-01)

> **Status:** Aprovado
> **Release ID:** v0.1.26
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-26

## Summary

R2 turned the R1 backlog-consistency **engine** into an **ORIENTED happy-path** plus the
**removal-on-release lifecycle**. It ships the `backlog_definition` dadaia-workflow — the
epic §4 seven-step sequence (`intake_grill → subject_bind → existing_backlog_review →
reconcile_decision → conflict_resolution_grill → backlog_author → backlog_review_gate`)
modelled field-for-field on `ReleaseDefinitionWorkflow`, with Python owning order and every
gate — wired behind `dadaia lifecycle backlog define`. The R1 deterministic classifier is
now fed live into the `existing_backlog_review` step (Python disposes every verdict; the
model is invoked only through the classifier's `downgrade` seam for a same-anchor
differing-change pair, fail-closed → `DIVERGENT_CONFLICT`), exercising end-to-end the seam
R1 shipped offline. A new `backlog_index` context selector returns every existing item's
bound intents + status for the review steps. The four real `backlog_definition/*.md`
fragments replace the scaffolded `_README.md` stub and are staged + installed to all
projections.

R2 also delivers the removal-on-release MECHANISM (epic §6): the R1-shaped
`consumed_backlog` ledger **writer** (`features/backlog/ledger_writer.py`), the
residual-aware closure removal hook (`features/backlog/removal.py` —
rewrite-down-to-residual by default; full removal only at zero residual, with the durable
archive copy preceding `unlink`), and the `BacklogRemovalLifecycle` orchestration facade
(`features/backlog/removal_lifecycle.py`) whose closure side (`remove_at_closure`) is wired
into `dadaia lifecycle close`. The BL-STALE loop is proven both directions at the
function/integration level (`tests/integration/test_backlog_removal_loop.py`).

The concrete value for the operator: a consistent backlog item is now produced **by
construction** through a sequenced, Python-gated workflow instead of being hand-written and
validated only after the fact by `backlog doctor`; and the staleness loop R1 left open now
has both its writer and its closure-side consumer in place. **One known residual remains**
— the producer half of removal-on-release is not yet wired into the real release-definition
surface (see `## Drifts` and the tracking pointer below); it is recorded honestly here and
does NOT undercut any of R2's 11 own acceptance criteria, none of which depended on it.

## Tasks completed

All 10 R2 tasks are `[x]` in `specs/releases/v0.1.26/TASKS.md`. Final commit SHAs are
assigned by the coordinator at commit time (this CLOSURE is authored before the coordinator's
closure commit; the implementation commits live on `feature/v0.1.26`).

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-26-01 | `backlog_index` context selector (bound intents + status; frontmatter-only; injected paths) | `feature/v0.1.26` |
| T-26-02 | Real `backlog_definition` step fragments (`intake_grill`, `conflict_scan`, `conflict_resolution_grill`, `backlog_authoring`); `_README.md` removed | `feature/v0.1.26` |
| T-26-03 | `consumed_backlog` ledger writer (`ledger_writer.py`, exact R1 reader shape, keyed on shipped anchors) | `feature/v0.1.26` |
| T-26-04 | Residual-aware closure removal hook (`removal.py`, copy-before-remove, ADR-C) | `feature/v0.1.26` |
| T-26-05 | `BacklogDefinitionWorkflow` body (§4 sequence, Python gates, mirrors `release_definition.py`); `_deferred` entry removed | `feature/v0.1.26` |
| T-26-06 | Feed R1 classifier into `existing_backlog_review` (model downgrade seam, fail-closed) | `feature/v0.1.26` |
| T-26-07 | CLI wiring + `build_backlog_definition_workflow` container factory (LAW 1/LAW 2; per-step overrides) | `feature/v0.1.26` |
| T-26-08 | Wire removal-on-release into the lifecycle (`removal_lifecycle.py`; closure side into `dadaia lifecycle close`) + BL-STALE loop | `feature/v0.1.26` |
| T-26-09 | Stage + install + doctor the new fragments (public propagation) | `feature/v0.1.26` |
| T-26-10 | Final live-tree verification (full pytest, ci preflight, 3 doctors) | `feature/v0.1.26` |
| Closure (this artifact + memory) | CLOSURE.md + architecture/tech-stack memory atoms | pending (coordinator) |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `pytest` | `3587 passed` (full suite, R2 alpha-1) |
| CI preflight clean | `dadaia ci preflight` | PASS (`ruff format --check` + `ruff check` + `mypy --strict` + `pytest`) |
| Backlog-consistency engine clean on live tree | `dadaia backlog doctor` | exit 0 (clean) on `specs/backlog/` |
| SDD structural health | `dadaia specs doctor` | green (structurally clean) |
| Projection consistency | `dadaia public doctor` | exit 0; `[ok] public-privacy` (new `backlog_definition/*.md` fragments present in projections, `_README.md` removed) |
| QA acceptance review (alpha-1) | qa-engineer handoff | verdict **APPROVED-WITH-FINDINGS** — all 11 R2 acceptance criteria (§3.7.1–§3.7.11) met; one **MEDIUM** residual (removal-on-release producer not wired at release-definition) deferred + tracked (see `## Drifts`) |

### Acceptance-criteria → proving-test map (SPEC §3.7, from the QA handoff)

| # | Criterion | Proving test |
|---|-----------|--------------|
| §3.7.1 | Workflow runs §4 sequence with Python-owned gates (stops at first blocked gate; advances only on success) | `tests/integration/test_backlog_definition_workflow.py` (end-to-end on `fake`) |
| §3.7.2 | Unresolved subject HALTs at `subject_bind` (no silent NEW) | `tests/integration/test_backlog_definition_workflow.py` (HALT case) |
| §3.7.3 | Classifier feeds `existing_backlog_review`; `C→D`-then-`C→E` divergence caught by Python with model OFFLINE, routes to grill | `tests/unit/test_backlog_review_step.py` (offline-default) + workflow step-matrix |
| §3.7.4 | `reconcile_decision` blocks NEW unless all-`UNRELATED` (both directions) | workflow step-matrix test (both branches) |
| §3.7.5 | `backlog_review_gate` re-validates authored result; blocks on `DUPLICATE`/`DIVERGENT_CONFLICT` | workflow step-matrix test (dirty-result case) |
| §3.7.6 | CLI wires the real workflow; `--harness claude` rejected (LAW 1); bad `--model` rejected (LAW 2) | `tests/integration/test_cli_backlog_define.py` |
| §3.7.7 | `backlog_index` returns bound intents + status per item; excludes `ideas.md`/`candidates.md`/catalog | `tests/unit/test_context_selector_backlog_index.py` |
| §3.7.8 | Ledger writer emits R1 reader shape keyed on shipped anchors; round-trips through `read_consumed` | `tests/unit/test_backlog_ledger_writer.py` |
| §3.7.9 | Residual-aware removal at closure (rewrite-and-keep; copy-then-remove at zero residual; copy precedes unlink) | `tests/unit/test_backlog_removal.py` (both branches) |
| §3.7.10 | BL-STALE loop closes (zero BL-STALE post-removal; BL-STALE on an artificially retained slug) | `tests/integration/test_backlog_removal_loop.py` |
| §3.7.11 | Test pyramid + parameterized step-matrix (no per-step copy-paste fan-out) | step-matrix parameterization in `tests/integration/test_backlog_definition_workflow.py` |

> **Note on the QA handoff path.** The dispatch briefing referenced
> `.dadaia/handoff/dadaia-workspace/2026-06-26T000000Z-qa-engineer-v0126-r2-alpha1.handoff.json`.
> That file is not present on disk at closure-authoring time (PE has no Bash and cannot
> re-emit it). The QA verdict recorded above (APPROVED-WITH-FINDINGS, one MEDIUM) is taken
> from the dispatch briefing facts; if the handoff is not on disk, the coordinator should
> confirm/emit it before archiving so the validation evidence has a durable sidecar.

## Drifts

### removal-on-release-producer-not-wired-at-release-definition

**Description:** R2 delivered the full removal-on-release **mechanism** — the R1-shaped
ledger writer (`consume_at_release_definition` / `BacklogRemovalLifecycle.consume`), the
residual-aware closure hook (`apply_removal` / `remove_at_closure` /
`BacklogRemovalLifecycle.remove`), and the closure-side invocation wired into
`dadaia lifecycle close`. However, the **producer half** (`consume_at_release_definition`)
is **NOT** wired into the real release-definition surface — only the closure consumer
(`remove_at_closure`) is. Consequently, in production **nothing writes the
`consumed_backlog.json` ledger**, so `remove_at_closure` reads an empty ledger and no-ops;
the BL-STALE loop is proven only at the function/integration level
(`tests/integration/test_backlog_removal_loop.py`), **not end-to-end on a real release**.

**Resolution:** Deferred deliberately, not invented under-spec. Deriving the **verified
shipped subject-anchor set** at release-definition time is genuinely underspecified: it
requires a convention for how a release *declares* which backlog items it consumed and which
of their bound anchors actually shipped (e.g. a `consumed_backlog` field in the release SPEC
frontmatter, a terminal release-definition step, or an operator declaration), then
bind+verify through the R1 registry before calling the existing
`consume_at_release_definition`. Inventing that derivation ad-hoc would have been theater.
Tracked as a HIGH backlog item:
`specs/backlog/wire-consumed-ledger-producer-at-release-definition.md`
(`FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`). This does not block
`workflow-model-governance`; it should land before relying on removal-on-release
operationally. The QA verdict (APPROVED-WITH-FINDINGS) accounts for this as the single
MEDIUM finding; all 11 of R2's own acceptance criteria are met (the producer wiring was not
among them).

**Memory updates:** `specs/memory/architecture.md` — the removal-on-release section is
recorded as **wired-at-closure-only** (producer pending the residual), explicitly NOT as a
fully-operational end-to-end loop.

## Memory updates

- `specs/memory/architecture.md` — (1) under the `features/` list, expanded the `lifecycle`
  + `backlog` feature descriptions to record the new `backlog_definition` workflow body, the
  `backlog_index` selector, the ledger writer + residual-aware removal hook + lifecycle
  facade; (2) rewrote the "Diferido para R2" paragraph of the Backlog-consistency subsystem
  to read as **delivered current-truth** (the workflow now EXISTS; the classifier feed runs
  live in `existing_backlog_review`; the ledger writer + removal hook exist) with the
  honest caveat that the removal producer is **wired-at-closure-only** pending
  `wire-consumed-ledger-producer-at-release-definition`; (3) noted the
  `consumed_backlog.json` writer in the runtime-state catalog (previously read-only).
- `specs/memory/tech-stack.md` — added the `dadaia lifecycle backlog define` verb to the
  canonical commands (drives the real `BacklogDefinitionWorkflow`, LAW 1/LAW 2). No new
  dependency — the dependency tables, runtimes, and approved-deps lists are unchanged.
- `specs/memory/product/*` — no change: R2 ships an internal lifecycle/governance surface,
  not a product feature page (consistent with R1's CLOSURE disposition).

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/backlog-definition-workflow-dedup-conflict-control.md` | backlog | `DELIVERED — v0.1.26` (R1 v0.1.25 + R2 v0.1.26 exhaust the epic's §11 R1+R2 scope) | this CLOSURE `## Summary` + `## Tasks completed` + SPEC §7 |
| `specs/backlog/wire-consumed-ledger-producer-at-release-definition.md` | backlog | `candidate` (R2 residual — NOT consumed by v0.1.26; carries the producer-wiring gap forward) | this CLOSURE `## Drifts` |

### Disposition sweep

This release picked exactly **one** backlog item: the epic
`FEAT-BACKLOG-DEFINITION-WORKFLOW-01`
(`backlog-definition-workflow-dedup-conflict-control.md`). R1 (v0.1.25) delivered the
engine slice; R2 (v0.1.26) delivers the workflow body, the live classifier feed, the real
fragments, the `backlog_index` selector, and the removal-on-release mechanism. With R1 + R2
both shipped, the epic's §11 R1+R2 scope is **exhausted** → the item is dispositioned
terminally **`DELIVERED — v0.1.26`** per the never-delete law (status set in the item's
frontmatter at the coordinator's closure commit).

The one piece of removal-on-release that is **not** operationally complete — the producer
wiring at release-definition — was **already split out** during this release into its own
HIGH backlog item (`wire-consumed-ledger-producer-at-release-definition.md`,
`FEAT-BACKLOG-CONSUME-PRODUCER-WIRING-01`), so the epic can disposition DELIVERED without
silently dropping the gap. That residual item stays `candidate` (it was not consumed by
v0.1.26).

No `consumed_backlog.json` removal entry is written for v0.1.26: per the known residual, the
producer is not yet wired, so nothing was mechanically recorded as fully-consumed this
release. (The epic's own disposition is a manual sweep entry above, not a ledger-driven
removal — fitting, since the ledger-driven path is exactly what the residual item will
complete.)

No bugs were picked into this release (`specs/bugs/` not consulted for scope — R2 is a
backlog-epic slice).

## Backlog returns

- `specs/backlog/wire-consumed-ledger-producer-at-release-definition.md` — **already filed**
  (HIGH, `candidate`) during implementation when QA surfaced the producer-wiring MEDIUM. It
  is the carried-forward residual of R2's §6 removal-on-release; not a new return at closure,
  recorded here for traceability.
- No other out-of-scope work was discovered that warranted a new backlog entry.

## Archive decision

**MOVE** — the release directory is ready to be moved to
`specs/_archive/releases/v0.1.26/` via `git mv` (run by the coordinator / a maintainer with
Bash; PE has no Bash tool). ACTIVE.md is updated by PE (Write tool) to point at
`release: none` with a one-line pointer to the archived v0.1.26 and the next step. The exact
archive command sequence is surfaced to the coordinator in the handoff.
