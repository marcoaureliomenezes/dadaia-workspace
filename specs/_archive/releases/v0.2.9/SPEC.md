# SPEC — Release v0.2.9 — Consumer real-use convergence (zero-bug gate)

> **Status:** Aprovado

**Release ID:** v0.2.9
**Owner:** product-engineer
**Source:** operator demand + sample-crawler discovery task tg-1784485392
**Workflow:** release-definition / spec_create

## 1. Problem

The consumer validation recipe certifies point checks and fake-harness flows, but the
consumer agent — the canonical consumer and release gate — finds real-use bugs on the
first round of every version. The declared gate for the NEXT package version (0.4.1):
**the consumer agent operates 100% of its real activities with dadaia-workspace, zero
bugs.** Only then does "Consumer agent" enter the docs as a supported environment.

Consumer' real-usage inventory (discovery task tg-1784485392): certify candidate
wheels; create/alive/baseline/bind/inspect Spec Contexts; make specs valid
(init/scaffold/upgrade/doctor/catalog); run the REAL lifecycle chain with Codex
(backlog → release → implementation-reviews → audit) — never once completed
reliably to closure; fake-chain gate checks; panel/server-registry/projections/
doctors; real backlog use (demanda B3/CVM); define releases and verify
SPEC/PLAN/TASKS; register bugs and retest fixes.

Its three stated priorities: (P1) an end-to-end Codex worker contract for artifact
authoring — path, existence, and change proven before a step is accepted; (P2) the
full live chain as the release gate, with deterministic certification explicitly
insufficient alone; (P3) autoconsistent scaffold+repair — a fresh context reaches
`specs doctor` 0/0 without manual edits.

## 2. Objective

Converge the consumer × dadaia-workspace loop to **zero failures on a full real-use
round** by fixing the root-cause classes consumer already proved (materialization,
placeholder repair, live-chain gate coverage) instead of patching instances.

## 3. Scope

### FR1 — backlog_author materialization proves a delta (P1)

The `backlog_author` step acceptance must prove the authored artifact EXISTS and
CHANGED: the same disk snapshot diff the `backlog_review_gate` applies
(`_backlog_snapshot()` before/after — `_authored_backlog_paths()` non-empty). A
worker that produces no new/changed item blocks AT THE STEP with the worker
diagnostic and the bounded structural-correction retry, instead of being accepted
and failing later at the review gate. Root cause: `deliverable_globs` zone check
(`agent_runner.py`) proves existence, not delta.

Bug: `codex-backlog-author-no-materialization-regression-040`.

Acceptance / verification:

- Unit + integration tests: a fake/worker that writes nothing blocks at the step
  (with retry diagnostics); a worker that writes/edits an item is accepted.
- Consumer live backlog-definition with Codex materializes and the chain proceeds.

### FR2 — Scaffold and placeholder-atom repair (P3)

`specs init` must not ship an atom that fails its own linter: the placeholder
`memory/product/feature.md` is emitted only when there is real content, replaced by
a valid empty catalog state otherwise. `specs upgrade` / `specs doctor --fix` gain a
repair that detects unsubmitted placeholder atoms (`*_PLACEHOLDER` markers) and
removes/replaces them so old contexts reach `specs doctor` 0 errors / 0 warnings.

Bug: `scaffold-repair-cannot-remediate-invalid-placeholder-atom` (open).

Acceptance / verification:

- Fresh `specs init` tree is doctor-clean with no manual edit.
- A tree seeded with the raw placeholder atom is repaired by `upgrade` AND by
  `doctor --fix`; both are covered by tests and help text documents the repair.

### FR3 — Pain-sweep fixes from the consumer inventory (root cause each)

- release-definition stalling after writing only SPEC.md (no terminal
  state/diagnostic) — investigate and fix the honest-terminal-state class.
- implementation-reviews retry prompt exceeding the Codex context window —
  bound/compact the rejection-correction digest.
- release-id canon: workflows must reject release ids that `specs doctor` rejects
  (single canon).
- projected skill syntax divergence from the CLI — audit skills vs CLI help, align.
- reconcile/doctor vs operator loose root files — the error text must point at
  `root_exceptions.txt` as the supported escape.

Acceptance / verification: each item lands as a registered bug with a root-cause
note, a fix (or an evidence-backed refutation), and tests where behavior changed.

### FR4 — Recipe v2: the real-use matrix (P2)

`public/data/CONSUMER_VALIDATION_RECIPE.md` gains a real-use section: the full live
Codex chain (clean context → backlog → release → implementation/review →
audit/closure) with per-link artifact+handoff assertions; the backlog
materialization canary; fresh/old-context doctor-clean statements; a B3/CVM-style
real-demand backlog statement; bug register→fix→retest. The recipe states
explicitly: deterministic certification alone NEVER approves a release.

Bug: `certification-misses-live-codex-backlog-regression-040`.

Acceptance / verification: consumer runs the expanded matrix end to end.

### FR5 — Convergence protocol and documentation

Iterate candidate → consumer full real-use round → root-cause all findings → fix
classes → re-certify, until one complete round reports zero failures. Only then:
docs page/memory atom declaring Consumer a supported environment; package 0.4.1 with
the standard gates (security review, consumer certification, CI, release-gate).

## 4. Out of scope

- Changes to the consumer runtime itself (sample-consumer) — consumption/feedback only.
- New harnesses; Layer-2 stays codex/pi.
- Consumer-side housekeeping of operator files (it keeps its own authorship rules).

## 5. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Live Codex runs are model-nondeterministic — a fix may pass while the class persists. | Fix classes not instances; recipe requires the live chain every round; regression tests pin the deterministic seams (disk-diff gate, scaffold repair). |
| FR3 items may split into product bugs vs docs gaps vs false positives. | Each is investigated and dispositioned with evidence before any fix. |
| Scope creep (the whole lifecycle surface). | The inventory bounds the contract; anything outside it defers to backlog. |
