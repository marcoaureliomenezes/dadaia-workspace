# Closure: Release — v0.1.25 — Backlog-consistency foundation (R1 of FEAT-BACKLOG-DEFINITION-WORKFLOW-01)

> **Status:** Aprovado
> **Release ID:** v0.1.25
> **Segment:** alpha-1
> **Owner:** product-engineer
> **Closed:** 2026-06-26

## Summary

R1 shipped the backlog-consistency **ENGINE**: the backlog is now mechanically held as a
deduplicated, conflict-free, non-stale SET. Every backlog item carries typed `intents[]`
(`Subject{kind,ref} → change`); an **auto-derived canonical-subject registry** recomputes
the anchor set from live truth on every run (code AST/grep ∪ CLI ∪ catalog ∪ doc ∪
invariant anchors; `panel`/`api` bind alias-only in R1); a **deterministic fail-closed
conflict classifier** owns the UNRELATED/DUPLICATE/DIVERGENT_CONFLICT boundary by canonical
anchor set-intersection (same-anchor + differing-change defaults fail-closed to
DIVERGENT_CONFLICT; the model may only downgrade a proven-compatible merge, never miss a
conflict); and `dadaia backlog doctor` (BL-SCHEMA / BL-DUP / BL-CONFLICT / BL-STALE) is
wired into the **pre-commit chokepoint + CI** as the enforced backstop. The 16 surviving
backlog items were backfilled with bound `intents[]` against real registry anchors.

The concrete value: the **divergent-twin failure** that previously corrupted a project
(`C→D` filed day 1, then a forgotten `C→E` filed day 2, both touching subject C with
incompatible targets) is now caught **mechanically at the commit boundary** — by Python
set-intersection arithmetic, not model attention and not human vigilance, both of which had
already failed. The honest enforcement posture (ADR-D): `specs/backlog/` is gitignored +
ADDITIVE, so the PreToolUse/lease gate cannot classify a hand-written backlog file as
MUTATING; the doctor at the git chokepoint is therefore the real enforcement, and the R2
workflow will be the oriented happy-path on top of this already-consistent foundation.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-25-01 | `intents[]` typed `Subject`/`Intent` schema (per-kind ref validation, module-relative) | `f1f1d91` |
| T-25-02 | Canonical-subject registry (linchpin) + 5-kind auto-derivation | `f1f1d91` |
| T-25-03 | Resolve/preview surface (`backlog subjects`, `doctor --explain`) | `f1f1d91` |
| T-25-04 | Deterministic conflict classifier (Python disposes, fail-closed) | `f1f1d91` |
| T-25-05 | `consumed_backlog` ledger reader (sidecar JSON, BL-STALE feed) | `f1f1d91` |
| T-25-06 | `backlog doctor` (BL-SCHEMA/DUP/CONFLICT/STALE) + CLI + chokepoint + CI | `f1f1d91` |
| T-25-07 | Backfill bound `intents[]` onto the 16 survivors (via preview) | `f1f1d91` |
| T-25-08 | Final live-tree verification | `f1f1d91` |
| qa-finding e2e fix | LOW §3.7.9 git-hook coverage — all four BL-* now BLOCK at the hook | `591f2f4` |
| Closure (this artifact + memory) | CLOSURE.md + architecture/tech-stack memory atoms | pending |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Type check clean (strict) | `mypy --strict dadaia_workspace` | `0 errors in 265 files` |
| Full test suite green | `pytest` | `3551 passed, 14 skipped, 0 failed` |
| Lint + format clean | `ruff check . && ruff format --check .` | clean (exit 0) |
| `backlog doctor` exit 0 on live tree | `dadaia backlog doctor` | exit 0 on `specs/backlog/` after backfill |
| Projection consistency | `dadaia public doctor` | exit 0; `[ok] public-privacy` |
| SDD structural health | `dadaia specs doctor` | exit 0 (structurally green) |
| QA acceptance review | qa-engineer handoff | verdict **APPROVED-WITH-FINDINGS** — one LOW (§3.7.9 git-hook coverage) CLOSED in `591f2f4`; all four BL-* now block at the hook |
| Security review | security-reviewer handoff | verdict **APPROVED**@`f1f1d91` — no CRITICAL/HIGH; AST/grep paths safe, no path-traversal, no gate bypass; LOW optional starlette/cryptography bump deferred |
| Integration proof (live backfill) | `dadaia backlog subjects` + `dadaia backlog doctor` | 16 backlog items backfilled with **real** module-relative anchors; only **1 alias** needed (panel api — expected per ADR-A); classifier found **0 real dup/conflict** → clean SET not forced |

### Integration proof detail

The backfill of the 16 survivors is the live-tree proof that the foundation is sound. PE
ran the read-only preview surface (`backlog subjects` / `doctor --explain`) over each
survivor's true subjects, then authored bound `intents[]` against the real anchors the
preview surfaced — never a fabricated anchor. Of the 16, exactly **one** required an alias
map entry (a `panel`/`api` subject, which is alias-only in R1 by ADR-A, exactly as
expected); every other subject resolved through auto-derivation. The classifier, run over
the resulting set, reported **zero** real DUPLICATE or DIVERGENT_CONFLICT pairs — the
backlog was already a clean SET, so no merge/split was forced. `dadaia backlog doctor`
exits 0 on the live `specs/backlog/`.

## Drifts

No drift from PLAN.md. The seven-step execution order (schema → registry + preview →
classifier → ledger → doctor + chokepoint/CI wiring → backfill → final verification) was
implemented as planned, the module contracts in PLAN §4 held, and all paths stayed
injected (no `os.getcwd()` reads — SPEC §3.8 #6). The single qa finding was a coverage gap
(the git-hook-level e2e §3.7.9 initially exercised the divergent-twin BLOCK but not each of
the four BL-* checks individually); it was closed in `591f2f4` by extending the e2e so each
planted BL-SCHEMA/DUP/CONFLICT/STALE violation BLOCKS at the hook and a clean tree PASSES.
This was a test-completeness fix, not a plan-vs-reality divergence.

## Memory updates

- `specs/memory/architecture.md` — added the **backlog-consistency mechanism** section:
  the `features/backlog/` subsystem (`subject_registry.py`, `classifier.py`, `doctor.py`,
  `ledger.py`, `preview.py`), the auto-derived canonical-subject registry, the fail-closed
  classifier, `dadaia backlog doctor` (BL-*) wired into pre-commit + CI as the enforced
  backstop, the `consumed_backlog.json` sidecar read contract; added `backlog` to the
  features list and the `consumed_backlog.json` archive sidecar to the runtime-state catalog.
- `specs/memory/tech-stack.md` — noted the new `features/backlog/` subsystem and the
  `dadaia backlog {subjects,doctor}` CLI surface.
- `specs/memory/product/*` — no change: R1 ships no new product feature page; the backlog
  governance surface is an internal mechanism, not a product atom.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/backlog-definition-workflow-dedup-conflict-control.md` | backlog | retained as **R2 residual** (PARTIALLY consumed — not flipped to a terminal token) | this CLOSURE `## Disposition sweep` + SPEC §7 |

### Disposition sweep

This release picked exactly one backlog item: the epic
`FEAT-BACKLOG-DEFINITION-WORKFLOW-01`
(`backlog-definition-workflow-dedup-conflict-control.md`). R1 delivered the **engine slice**
(§11 of the epic): the `intents[]` schema, the canonical-subject registry, the deterministic
classifier, the enforced `backlog doctor`, and the 16-item backfill.

The epic is **PARTIALLY consumed → retained as the R2 residual**, NOT flipped to a terminal
DELIVERED/CONSUMED token, per the never-delete law and the epic's own OVERLAP→UPDATE
discipline. Its current `intents[]` already scope exactly the R2 surface — the
`backlog_definition` workflow body (`_deferred.py#backlog_definition`), the
`lifecycle backlog define` CLI wiring, the removal-on-release closure hook that **writes**
the `consumed_backlog` ledger, the real fragments, and the live model-adjudication
downgrade step — so **no rewrite of the item is needed**; it survives verbatim as the R2
(v0.1.26) scope.

**No `consumed_backlog.json` removal entry is written for v0.1.25.** Nothing was FULLY
consumed this release, and R1 explicitly does **not** write the ledger (the writer is R2 —
SPEC §3.6 / ADR-C; R1 only defines the format and reads it). BL-STALE therefore remains a
no-op over the absent-ledger live tree, exactly as designed.

Note: the operator-added candidate `workflow-step-handoff-data-plane-cleanup` is now in the
backlog (`specs/backlog/workflow-step-handoff-data-plane-cleanup.md`) and is **not** part of
v0.1.25 — it is a future candidate, untouched by this release.

## Backlog returns

- None new. No out-of-scope work was discovered during implementation that warranted a new
  backlog entry. The R2 surface is already captured in the retained epic above.

## Archive decision

**MOVE** — the release directory is ready to be moved to
`specs/_archive/releases/v0.1.25/` via `git mv` (run by a maintainer). ACTIVE.md will then
be updated to point at the next release or `release: none`. (A maintainer runs
`dadaia specs doctor` and the `git mv` archive after this closure.)
