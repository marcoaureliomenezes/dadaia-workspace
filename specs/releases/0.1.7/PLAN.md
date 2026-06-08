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
