# Tasks: Supported agent consumer certification - v0.2.5

> **Status:** Aprovado
> **Release ID:** v0.2.5
> **Owner:** product-engineer
> **Created:** 2026-07-15

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

## T1 - Enforce caller-owned context contracts

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** audit and refinement accepted; v0.2.5 active.
- **Files modified:** context CLI/resolution services and focused tests.
- **Changes:** implement `context list --json`; resolve heartbeat from caller-owned persisted session; remove first-ALIVE fallback; return actionable errors.
- **Acceptance:** focused unit/integration tests cover multi-context, persisted bind without manual env, and unbound failure.

## T2 - Publish machine-readable capabilities

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** T1 complete.
- **Files modified:** capability feature, CLI adapter, package data, schema, docs, tests.
- **Changes:** define and expose the versioned public feature/workflow/projection/compatibility contract.
- **Acceptance:** built wheel returns schema-valid capability JSON and tests reject unknown contract versions.

## T3 - Make upgrades transactional

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** T2 complete.
- **Files modified:** workspace reconciliation service/CLI, public projection integration, tests.
- **Changes:** reconcile exact candidate version, state, projections, doctors, and canary; preserve failure diagnosis and rollback boundary.
- **Acceptance:** clean and stale-workspace journeys prove convergence; injected failure never reports promotion success.

## T4 - Support explicit empty-repository baselines

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** T1 complete.
- **Files modified:** context onboarding service/CLI, Git adapter, tests, docs.
- **Changes:** add operator-consented scaffold baseline creation while preserving non-committing `alive` behavior.
- **Acceptance:** unborn remote journey passes through baseline, bind, dead, and alive without hidden commits.

## T5 - Preflight lifecycle workers and retain diagnostics

- [x] **Status:** DONE
- **Owner:** software-engineer
- **Preconditions:** T2 complete; bug `lifecycle-codex-worker-readonly-sandbox` reported.
- **Files modified:** worker dispatch/runtime adapters, lifecycle state diagnostics, tests.
- **Changes:** preflight writable artifact path and harness launch; classify infrastructure failure distinctly; emit operator command and complete diagnostic.
- **Acceptance:** read-only/bubblewrap failure is caught before semantic work; healthy Codex and PI canaries materialize evidence.

## T6 - Certify every public feature family

- [x] **Status:** DONE
- **Owner:** qa-engineer
- **Preconditions:** T1-T5 complete.
- **Files modified:** certification CLI/script, feature journeys, fixtures, panel/server checks.
- **Changes:** implement disposable deterministic certification for init, scaffold/specs, contexts, projections, four workflows, reports/handoffs, panel/server, capabilities, and upgrades.
- **Acceptance:** one documented command emits stable JSON plus a nonzero exit on any failed capability; built-wheel clean-room run is green.

## T7 - Project version-matched agent mastery

- [x] **Status:** DONE
- **Owner:** ai-engineer
- **Preconditions:** T2 and T6 complete.
- **Files modified:** public skill source/projections, operational docs, compatibility contract tests.
- **Changes:** provide concise skill instructions that discover capabilities, bind explicitly, self-pull scoped context, run certification, and preserve full evidence.
- **Acceptance:** public doctor proves projections match; no removed lifecycle syntax remains in provider agent guidance.

## T8 - Prove Hermes compatibility and close

- [x] **Status:** DONE
- **Owner:** product-engineer
- **Preconditions:** T1-T7 complete and consumer release ready.
- **Files modified:** bug ledger, closure/evidence artifacts, ACTIVE and memory only where current truth changed.
- **Changes:** build candidate, run full provider ladder, run Hermes assembled script, run real Codex/PI canaries, resolve all bugs, review security/QA, and archive.
- **Acceptance:** zero failed certification checks, zero open release bugs, zero doctor errors, validated handoffs, immutable evidence commit.
