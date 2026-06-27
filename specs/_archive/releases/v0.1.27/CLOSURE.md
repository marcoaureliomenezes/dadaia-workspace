# Closure: Release — v0.1.27 — wire the consumed_backlog PRODUCER at release-definition

> **Status:** Aprovado
> **Release ID:** v0.1.27
> **Owner:** product-engineer
> **Closed:** 2026-06-26

## Summary

v0.1.27 wires the consumed_backlog **producer** into the real `dadaia lifecycle release
define` surface, resolving the residual left by v0.1.26 R2. R2 had shipped the entire
removal-on-release *mechanism* (the R1-shaped ledger writer, the residual-aware closure
hook, the `BacklogRemovalLifecycle` facade, and the closure-side `remove(...)` invocation
on `dadaia lifecycle close`), but nothing wrote the `consumed_backlog.json` ledger in
production — so `remove_at_closure` always read an empty ledger and no-opped, and the
BL-STALE loop could only be proven at the function/integration level, never end-to-end on
a real release.

This release closes that gap with the operator-resolved declaration convention: a release
declares the backlog items it fully consumes via a machine-readable `**Consumes:** slug1,
slug2` bold-key line in its SPEC — the same convention SPEC.md already uses for
`**Status:**` / `**Release ID:**` / `**Owner:**` / `**Branch:**`. At `release define`, a
guarded post-step (symmetric with `close`'s `_apply_closure_removal`) parses that line,
binds each declared slug's `intents[]` through the R1 canonical-subject registry to its
verified shipped-anchor set (the union over declared slugs), and calls
`BacklogRemovalLifecycle.consume(...)` to write the ledger. The producer fails loud — a
declared slug that does not resolve, or whose intents bind to zero/unresolvable anchors,
raises an actionable error and writes no partial ledger.

The full define→close loop now fires end-to-end on a real release, proven by an
integration test that drives the real CLI verbs (`lifecycle release define` then
`lifecycle close`) over a temp workspace and asserts the consumed item is removed from the
live backlog SET, an archive copy precedes the unlink, and `backlog doctor` reports zero
BL-STALE. Partial consumption remains explicitly out of scope (full-slug granularity
only); partial items stay in the live SET and are hand-rewritten as today.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-1 | Parser `parse_consumes_line` (bold-key extraction, dedup, `.md`-strip, absent → empty) | `feature/v0.1.27` |
| T-2 | Binder `shipped_anchors_for` happy path (union of bound anchors of declared slugs) | `feature/v0.1.27` |
| T-3 | Binder fail-loud: unknown slug raises `ConsumesBindError` naming the slug | `feature/v0.1.27` |
| T-4 | Binder fail-loud: unbindable intents raise `ConsumesBindError` naming the ref | `feature/v0.1.27` |
| T-5 | Producer post-step on `release define` (A1, end-to-end via real CLI verb) | `feature/v0.1.27` |
| T-6 | Define→close loop (A2, end-to-end: live SET removal + archive copy + zero BL-STALE) | `feature/v0.1.27` |
| T-7 | Document the `**Consumes:**` convention in the dadaia-release-definition skill (A3) | `feature/v0.1.27` |
| T-8 | Full lint/type/test gate + working-tree hygiene | `feature/v0.1.27` |

> Per-task commit SHAs are on branch `feature/v0.1.27` (alpha-1, unpushed at closure
> time). The QA verdict below is keyed to the alpha-1 head; the coordinator records the
> exact SHAs at ship time per the release-governance rc cadence.

## Validations

Each validation is a triple: description, command, evidence.

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `pytest -p no:cacheprovider` | `3602 passed, 14 skipped, 0 failed` (QA handoff `metrics.pytest_total_passed=3602`) |
| Targeted consumes coverage | `pytest tests/unit/backlog/test_consumes.py tests/integration/test_release_consume_producer.py` | `15 passed` (QA `metrics.targeted_consumes_tests_passed=15`) |
| CI preflight all-green | `dadaia ci preflight` | `4 checks passed` — `ruff format --check`, `ruff check`, `mypy --strict`, `pytest` (QA `metrics.ci_preflight_checks_passed=4`) |
| Backlog doctor clean | `dadaia backlog doctor` | zero BL-SCHEMA/BL-DUP/BL-CONFLICT/BL-STALE (QA verdict_reason: "backlog doctor clean") |
| Specs doctor clean | `dadaia specs doctor` | clean (per dispatch briefing) |
| Public doctor clean (SKILL.md projected) | `dadaia public doctor` | exit 0 with `[ok] public-privacy`; SKILL.md staged + projected to all targets (QA A3 finding) |
| Clean working tree, no in-repo cache pollution | `git status --short` | empty on `feature/v0.1.27`; no `.dadaia/`/`.pytest_cache/`/`.mypy_cache/`/`.ruff_cache/`/coverage (QA finding) |
| QA alpha-1 verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T192059Z-qa-engineer-v0127-alpha1-consumes-producer.handoff.json` (0 CRITICAL/HIGH/MEDIUM/LOW findings) |

### Acceptance criteria → test map (from the QA handoff)

| # | Criterion | Test(s) | Result |
|---|-----------|---------|--------|
| A1 | Real `release define` with `**Consumes:** <slug>` writes `specs/_archive/<release-id>/consumed_backlog.json` keyed on the verified shipped-anchor set, decoupled from the live release dir | `test_define_writes_ledger` (drives the real `lifecycle release define --json` CLI verb) | PASS — genuinely end-to-end |
| A2 | Define→close cycle removes a fully-consumed item from the live SET (archive copy precedes unlink) and `backlog doctor` reports zero BL-STALE | `test_define_close_loop` (real `lifecycle release define` then real `lifecycle close`) | PASS — the headline loop, both CLI verbs unstubbed |
| A3 | The `**Consumes:**` convention is documented in exactly one canonical home | T-7 doc in `public/skills/dadaia-release-definition/SKILL.md §6`; `dadaia public doctor` exit 0 | PASS |
| A4 | A `**Consumes:**` slug that does not resolve / has unbindable anchors fails loud (no silent skip, no partial ledger) | `test_bad_consumes_fails_loud` (integration boundary) + `test_unknown_slug_fails_loud`, `test_slug_with_unresolved_intent_fails_loud`, `test_slug_with_zero_intents_fails_loud` (unit) | PASS — fail-loud at both layers |

## Drifts

No drifts. Implementation followed PLAN.md and SPEC.md without bending: the producer was
added as the guarded post-step inline after `workflow.run(...)` returns `completed`
(exactly as PLAN §1 / SPEC §3.2 resolved the `release_define` post-step seam asymmetry vs
`close`), the binder returns the union over declared slugs (PLAN §4), and fail-loud raises
before any write. No closure-path code changed.

### partial-consumption-out-of-scope

**Description:** This release records only fully-consumed backlog items (full-slug
granularity). A backlog item only *partially* shipped by a release is not recorded by the
producer.

**Resolution:** This is **intentionally out of scope per SPEC §4**, not a drift. Partial
items stay in the live SET and are hand-rewritten to their residual exactly as today. The
R2 closure-side `apply_removal` already rewrites-down-to-residual when a ledger lists a
partial, but this producer never *writes* a partial entry; `consume_at_release_definition`
itself already drops non-fully-consumed items. The boundary is a documentation+test line,
not missing code. It is recorded here only to make the scope boundary explicit — it does
**not** represent a deviation from plan.

**Memory updates:** none required for this item (the producer behavior memory describes is
full-slug-only, which is current truth).

## Memory updates

- `specs/memory/architecture.md` — updated the runtime-state bullet for
  `specs/_archive/<release-id>/consumed_backlog.json` (was: "producer wiring na superfície
  real é resíduo R2 — em produção o sidecar ainda não é emitido"; now: producer is wired
  at `dadaia lifecycle release define` via the `**Consumes:**` SPEC line, so the sidecar
  is emitted in production). Also rewrote the removal-on-release narrative in the
  "Backlog-consistency subsystem" section: both halves are now wired (producer at `release
  define`, consumer at `close`), the BL-STALE loop fires end-to-end on a real release, and
  the `**Consumes:**` declaration convention is documented. Bumped `last_updated`. The R2
  residual backlog reference was removed (it is now delivered).
- `specs/memory/tech-stack.md` — no change: this release added no dependency and changed
  no approved technology; the `dadaia lifecycle release define` verb and its harness/model
  catalog are unchanged (the producer is a behavior-only post-step, already covered by the
  lifecycle CLI surface already documented).

## Dispositions

Disposition-sweep ledger. v0.1.27 consumes one backlog item (declared via the SPEC
`**Consumes:**` line); no bugs were picked into this release.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/wire-consumed-ledger-producer-at-release-definition.md` | backlog | `status: delivered` + `delivered_in: v0.1.27` | this CLOSURE `## Summary` + `## Validations` A1/A2; QA APPROVED handoff |

**Note on the mechanical removal.** The define→close removal mechanism is proven by the
e2e test `test_define_close_loop` (real CLI verbs over a temp workspace). For v0.1.27
itself the lifecycle was run **via agents** (PM dispatch + sub-agent authoring), not via
the `dadaia lifecycle release define` CLI verb, so **no live `consumed_backlog.json`
ledger was written for v0.1.27's own archive** — this is expected, not a gap. The consumed
backlog item file is gitignored in this source repo (privacy backstop), so the
frontmatter disposition above (`status: delivered`, `delivered_in: v0.1.27`) is the
live-SET removal equivalent and the authoritative record of consumption. The terminal
status uses the BL-SCHEMA-valid form (`status: delivered` + `delivered_in: v0.1.27`) — NOT
a free-text `DELIVERED — v0.1.27` status line, which BL-SCHEMA rejects (see bug
`backlog-doctor-bl-schema-vs-spec-doc-031-terminal-status-format-conflict`).

## Backlog returns

None. No new candidates or ideas were discovered during implementation that fell outside
this release's scope. Partial consumption was already an out-of-scope boundary declared in
the SPEC (not a newly-discovered return); the next planned release is
`workflow-model-governance-panel-control-plane`.

## Archive decision

**MOVE** — the release directory will be moved to
`specs/_archive/releases/v0.1.27/` via `git mv` (run by the coordinator;
product-engineer has no Bash). `specs/releases/ACTIVE.md` is updated to `release: none`
with a pointer to the archived release and the next step.
