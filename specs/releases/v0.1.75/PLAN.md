# PLAN — Release v0.1.75

**Status:** Aprovado

## Approach

Cluster-by-cluster, each cluster gated by its own plan file and a green targeted run
before the next starts — never a single big-bang delete. Order picks the least-coupled
clusters first and the frozen-suite-adjacent cluster last (with FR2 adjudication):

1. **T-1 panel** (plan-panel.md, 496→81) — most mechanical; establishes the golden/API
   pattern + tab-list fixture (FR4).
2. **T-2 infrastructure** (plan-infrastructure.md, 622→~150) — mega-file split + the two
   parametrized sweeps.
3. **T-3 contract+e2e** (plan-contract-e2e.md, 294→~120).
4. **T-4 core+hooks+cli + unit-root adjacency** (plan-core-hooks-cli.md, ~854→~324).
5. **T-5 lifecycle** (plan-lifecycle.md, 515→~185).
6. **T-6 unit-features-rest incl. spec_context** (plan-unit-features-rest.md,
   1,035→250) — carries FR2 (frozen-suite re-baseline; QA adjudication artifact).
7. **T-7 integration** (plan-integration.md, 574→~145) — shared fixtures (FR4),
   relocations to unit, dead-live-file deletions.
8. **T-8 speed wiring** (FR3: --quick hook, xdist, tests/tmp gitignore) + final count
   reconciliation to the 1,000–1,200 window (secondary-squeeze lists if over).

Each task: implement per plan file → targeted cluster run green → coverage spot-check
on touched production modules → next. Full suite + collect-only count at T-8.

## Risks

- Coverage gate dips below 80% after deletes → each cluster verifies coverage on its
  owned production packages; goldens/param tables preserve line coverage.
- Hidden only-coverage loss → the plans name only-coverage behaviors; each task's
  checklist verifies them present.
- xdist × pytest-randomly interplay → T-8 proves 3 consecutive green randomized runs.
- Frozen-suite law → FR2 explicit adjudication, never silent (grill CRITICAL).
