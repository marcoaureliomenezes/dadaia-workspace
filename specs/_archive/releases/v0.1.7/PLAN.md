# Plan: Release 0.1.7 — Implementation Rot Remediation

**Status:** Aprovado
**Release ID:** 0.1.7
**Owner:** product-engineer

---

## Strategy

15 tasks, grouped into 5 waves by dependency and risk. Each wave must reach
`pytest` green before the next wave starts. `dadaia public doctor` after any
change to `public_assets.py` or `sdd-spec-gate.sh`.

---

## Execution Order

### Wave 1 — Trivial / Safe (no design prerequisite)

These tasks are mechanical, narrow-blast, and can run in parallel (disjoint write sets).

| Task | Files | Estimated effort |
|------|-------|-----------------|
| T-017-01 | `features/reports_next/service.py` + its unit tests | 30 min |
| T-017-02 | `cli/main.py` + delete `repos/.dadaia/` residue | 1 hour |
| T-017-03 | `features/specs/doctor.py:266-350` | 30 min |
| T-017-04 | `cli/commands/context.py:428-469` + tests | 45 min |
| T-017-05 | `tests/unit/features/panel/test_contrast.py`, `tests/unit/test_dashboard.py`, `tests/test_orchestration_registry.py` | 45 min |
| T-017-14 | `pyproject.toml` | 10 min |

Precondition: none. All can start from HEAD of feature/0.1.7 simultaneously.
After wave: `pytest` must be green.

### Wave 2 — DI / Structural (architect-designed; sequential)

Must run in order because each task modifies the same DI graph.

| Task | Files | Estimated effort | Prerequisite |
|------|-------|-----------------|-------------|
| T-017-10 | `core/lock_liveness.py`, `panel/views/kanban.py`, `spec_context/locking.py` | 1 hour | Wave 1 green |
| T-017-06 | `panel/service.py:157`, `container.py:289` | 30 min | T-017-10 |
| T-017-07 | `core/protocols/` (3 new files), `panel/service.py:45-48`, `container.py` | 4 hours | T-017-06 |
| T-017-08 | `panel/views/api.py`, `panel/service.py` (add `ReportRetentionService` logic) | 4 hours | T-017-07 |

Note: T-017-06..08 require software-architect design input (AR-02, AR-01, AR-03 design
recommendations in the architect-review). SE should read the architect-review findings
before implementing. The recommended interface names are in AR-01:
`IServerRegistryProvider`, `ISpecContextProvider`, `IWorkflowSummaryProvider`.

After wave: `pytest` must be green; panel integration tests must pass.

### Wave 3 — Refactors (public_assets.py)

| Task | Files | Estimated effort | Prerequisite |
|------|-------|-----------------|-------------|
| T-017-09 | `infrastructure/public_assets.py` | 2 hours | Wave 2 green |
| T-017-11 | `infrastructure/public_assets.py` → sub-modules (staged) | 4+ hours or defer | T-017-09 green |

T-017-09 is the guardrail-pair collapse and consumer-repo deduplication. Behavior-preserving.
T-017-11 is the broader module split. Each extraction must: (a) maintain all exports at the
`infrastructure/` level via `__init__.py` re-exports, (b) pass `mypy --strict`, (c) pass
`pytest`, (d) exit `dadaia public doctor` 0.

If T-017-11 cannot safely complete in this release, SE records the explicit defer decision
in TASKS.md before marking T-017-11 `[x]`.

After wave: `dadaia public doctor` exit 0; `pytest` green.

### Wave 4 — Gate Fix

| Task | Files | Estimated effort | Prerequisite |
|------|-------|-----------------|-------------|
| T-017-15 | `dadaia_workspace/public/scripts/sdd-spec-gate.sh` | 1 hour | Wave 3 green (or concurrent) |

After fix: run `dadaia public stage && dadaia public install --target all`. Verify
`dadaia public doctor` exit 0. Manual smoke test: PM agent writes to `specs/backlog/`.

### Wave 5 — Memory (product-engineer, DEFINITION/CLOSURE phase)

| Task | Files | Prerequisite |
|------|-------|-------------|
| T-017-12 | `specs/memory/architecture.md` | DEFINITION phase (now) |
| T-017-13 | `specs/memory/quality-assurance.md` | DEFINITION phase (now) |

Memory fixes T-017-12 and T-017-13 are applied immediately (DEFINITION phase).
Post-implementation memory updates (e.g. adding `core/lock_liveness.py` to the
architecture state section, noting `core/protocols/` additions) are deferred to CLOSURE.

---

## Layers Affected

| Layer | Tasks | Notes |
|-------|-------|-------|
| `cli/` | T-017-02, T-017-04 | Thin commands only; no logic change |
| `core/` | T-017-07, T-017-10 | New `protocols/` + `lock_liveness.py` extension |
| `features/panel/` | T-017-06, T-017-07, T-017-08, T-017-10 | DI fixes; largest blast radius in this release |
| `features/reports_next/` | T-017-01 | One constant update |
| `features/specs/` | T-017-03 | Dead code deletion |
| `infrastructure/` | T-017-09, T-017-11 | public_assets.py refactor |
| `public/scripts/` | T-017-15 | Gate bug fix; requires re-projection |
| `tests/` | T-017-05 | Slop cleanup |
| `pyproject.toml` | T-017-14 | Version bump only |
| `specs/memory/` | T-017-12, T-017-13 | Memory atoms (PE-only) |

---

## Technical Risks

1. **Panel DI (T-017-06..08):** The panel feature has the most complex test suite (38 files).
   Protocol injection may require updating mocks. SE must verify panel unit + integration tests
   before advancing to T-017-08.

2. **public_assets.py collapse (T-017-09):** The hash-compare logic in each of the three
   guardrail-pair functions must be consolidated without behavioral divergence. The explicit test
   vector is `dadaia public install --target all` on a workspace where projected files have
   diverged.

3. **T-017-11 module split:** Breaking import paths is the highest risk. Mitigation: maintain
   re-exports at `infrastructure/__init__.py`, run `mypy --strict` before committing.

4. **T-017-15 gate fix:** The gate is a Bash script; persona resolution logic must preserve the
   existing fail-safe behavior (fail-open, not fail-closed).

---

## Validation Plan

1. After every wave: `pytest` from repo root, exit 0.
2. After T-017-09, T-017-11, T-017-15: `dadaia public doctor`, exit 0.
3. After T-017-07: `mypy --strict dadaia_workspace`, exit 0 (protocols must type-check).
4. Before CLOSURE: full suite `pytest`; `dadaia specs doctor`; `dadaia public doctor`.
5. CLOSURE evidence: commit SHAs + one `pytest` stdout snippet showing pass count.

---

## rc-3 plan — Unlock the Workflow

Three waves on `feature/0.1.7`. Deletion-dominant; the lease (sole concurrency control) is
untouched. Reproject + doctor after the gate edit; `pytest` green per wave; no push.

**Wave A — remove the lock (keystone):** T-017-21 (delete backlog persona block; re-justify
PROTECTED on lease `.ptr`) + T-017-22 (delete dormant RULE-D deny path). Both edit
`sdd-spec-gate.sh` — one cohesive rewrite, one review unit. After: reproject + replay REPRO 1
(expect ALLOW).

**Wave B — align law/docs/tests (parallel, disjoint write sets):** T-017-23 (reword
`backlog-ownership` rule), T-017-24 (AGENTS.md + gate-model memory: one lock), T-017-25
(rewrite gate tests — flip backlog to ALLOW incl. the rc-2 codex-path assertion added in
T-017-20; keep lease negative + protected-sessions tests).

**Wave C — use the unlocked flow + close (sequential; depends on Wave A reprojected):**
T-017-26 (reproject + full preflight), T-017-27 (register the previously-blocked backlog epic
via the unlocked flow — end-to-end proof), T-017-28 (close both persona bugs `resolved_in:
0.1.7`; flag stale v0.2.0 pick in candidates.md for a separate PM re-baseline).

**Sequencing rationale:** T-017-27 is itself gate-blocked until Wave A is reprojected into the
live instance — so its success without env var or pointer is the live acceptance proof of
FR-rc3-1/2. **Rollback:** each change is a `public/` source edit + reproject; `git revert` +
reproject restores the prior gate exactly.

## rc-3 validation additions

6. After T-017-21: replay REPRO 1 (`echo '{"tool_name":"Write",...backlog...}' | bash
   sdd-spec-gate.sh`) → exit 0, no `decision":"block"`.
7. After Wave B: `pytest tests/integration/gate/` green under the new contract.
8. CLOSURE: re-run full `dadaia ci preflight`; record the T-017-27 backlog write as proof.

---

## rc-4 plan — Bug root-cause sweep

Eight tasks, three waves. Architectural fixes (Wave A) implement the grill ADRs; local-logic
fixes (Wave B) are independent; Wave C is verification/cleanup + bug closure. Reproject after any
`public/` edit; `pytest` green per wave; ship-trio re-review before ship. No push.

**Wave A — architectural root cause (grill ADRs 1,2,4):**
- T-017-29 gate context-from-path (ADR-1) — fixes `gate-cross-context-lock-contamination` (+dup).
- T-017-30 ctx-inject harness-native session id + silent already-fired (ADR-2) — fixes
  `repeated-visible-userpromptsubmit-memory-injection`.
- T-017-31 single-source alignment + `specs doctor` lint (ADR-4) — fixes
  `constitution-persona-single-source-drift`.

**Wave B — local-logic fixes (no grill; parallel, disjoint write sets):**
- T-017-32 install/doctor prune completeness — fixes `install-does-not-prune-orphan-projections`
  + `agent-skill-surface-slop` (projection side).
- T-017-33 doctor/upgrade output reconciliation — fixes `specs-doctor-dual-error-counter` +
  `specs-upgrade-fails-on-preexisting-doctor-error`.
- T-017-34 ci-preflight robustness — fixes `ci-preflight-raw-traceback-when-poetry-absent`.

**Wave C — verify, cleanup, close:**
- T-017-35 panel verification follow-ups (container store injection; per-request slug; remove
  residual `_BEARER_AUTH_ROUTE_NAMES` tuple).
- T-017-36 persona dangling skill-ref cleanup (library side of `agent-skill-surface-slop`,
  ai-engineer scope) + file backlog item `lease-shell-write-coverage-gap` (ADR-3 deferral) +
  flip all targeted bugs to Closed `resolved_in: 0.1.7`.

**Sequencing:** T-017-29 is the keystone — it fixes the lock that is actively contaminating this
very release's writes. Land + reproject it first so the rest of rc-4 (and any concurrent
context) stops false-blocking. Reproject + full preflight before review.

## rc-4 validation additions
9. Two-session/two-repo no-cross-block integration test green; same-repo foreign-live still blocks.
10. ctx-inject hook test: single bootstrap injection + silent already-fired path.
11. `specs doctor` single-source lint catches a seeded drift; `public doctor` reports a seeded orphan.
