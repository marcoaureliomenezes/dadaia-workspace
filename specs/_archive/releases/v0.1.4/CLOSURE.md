# Closure: Release — v0.1.4

> **Status:** Aprovado
> **Release ID:** v0.1.4
> **Owner:** product-engineer
> **Closed:** 2026-06-04

> **Note (retrospective closure):** This CLOSURE.md is written after the
> implementation was committed and reviewed in a prior session. Per-task evidence
> references commit `5a180dc` ("test: reorganize and slim test suite") as the
> primary implementation commit. Where separate per-task commit SHAs are not
> archived, the triple is marked retrospective and cites the primary commit.

## Summary

This release replaced dadaia-workspace's accumulated test pile with an explicit,
enforceable test architecture. Before this release the suite had no marker
taxonomy, embedded coverage flags in the default pytest invocation, no contract
layer, no temporary quarantine, and a significant volume of release-history
tests — including a 1,974-line `test_r2_qa_gaps.py` coverage archive, several
PR/task-numbered panel test files, and assertions whose only purpose was proving
that deleted code remained deleted.

After this release, the suite is organized into five enforced layers — unit,
contract, integration, e2e, and tmp — each with a machine-readable pytest marker
and a documented write-policy. The local fast path runs without coverage
instrumentation. CI is split into seven separate jobs (lint, typecheck, unit-fast,
contract-coverage, integration, e2e-python, e2e-panel), each with an explicit
timeout. The `tests/contract/` directory holds promoted public-behavior checks
for CLI/API/schema/security contracts. The `tests/tmp/` quarantine is excluded
from default collection and documented as temporary only.

Slop test files were deleted or rewritten: `test_r2_qa_gaps.py` is gone; panel
PR-history files (`test_assets_pr3_10.py`, `test_assets_pr3_16.py`,
`test_assets_pr3_17.py`, `test_pr304_theme_switcher.py`, `test_views_index.py`)
were collapsed into current-behavior parameterized contracts; retired panel
byte-identity and palette canary tests were removed; deleted-method and
removed-invariant assertions in spec_context_service and spec_context_doctor
tests were excised. Slow process-boundary journeys in `test_handoff_pipeline.py`
and `test_cli_import.py` are correctly marked and budgeted.

All 9 tasks completed. The architecture is now the durable contract the suite
enforces going forward.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-TEST-01 | Add executable pytest taxonomy and tmp quarantine | `5a180dc` |
| T-TEST-02 | Split CI and release test commands by layer | `5a180dc` |
| T-TEST-03 | Create contract suite and promote current public contracts | `5a180dc` |
| T-TEST-04 | Delete R2 QA gap and coverage-archive tests | `5a180dc` |
| T-TEST-05 | Remove deleted-method and removed-invariant tests | `5a180dc` |
| T-TEST-06 | Rewrite retired panel memory and palette tests | `5a180dc` |
| T-TEST-07 | Collapse panel PR-history asset tests | `5a180dc` |
| T-TEST-08 | Consolidate panel view/index tests | `5a180dc` |
| T-TEST-09 | Budget integration/E2E journeys and verify suite | `5a180dc` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| pytest taxonomy declared; `tests/tmp` excluded from collection | `grep -A20 '\[tool.pytest.ini_options\]' pyproject.toml` | `5a180dc` (retrospective) — `pyproject.toml` declares 6 markers (`unit`, `contract`, `integration`, `e2e`, `slow`, `tmp`) and `norecursedirs = ["tests/tmp"]` |
| `addopts` no longer embeds `--cov*`; coverage is CI-only | `grep addopts pyproject.toml` | `5a180dc` (retrospective) — `addopts = "-ra -p no:cacheprovider"` with no coverage flags |
| CI split into 7 layer-specific jobs | `grep '^  [a-z]' .github/workflows/ci.yml` | `5a180dc` (retrospective) — jobs: lint, typecheck, unit-fast, contract-coverage, integration, e2e-python, e2e-panel each with explicit timeout |
| `tests/contract/` exists and holds promoted public-contract tests | `ls tests/contract/` | `5a180dc` (retrospective) — directory present with `test_handoff_schema_contract.py`, `test_source_repo_hygiene.py`, `test_session_bound_context_residue.py`, cli/ sub-layer |
| `tests/tmp/README.md` exists and documents quarantine rules | `cat tests/tmp/README.md` | `5a180dc` (retrospective) — README declares: excluded from collection, never used for coverage, never merged as release evidence |
| `test_r2_qa_gaps.py` deleted | `ls tests/unit/test_r2_qa_gaps.py 2>&1` | `5a180dc` (retrospective) — file absent from working tree |
| Panel PR-history files deleted or collapsed | `ls tests/unit/features/panel/test_assets_pr3_10.py 2>&1` | `5a180dc` (retrospective) — PR-numbered files absent; current-behavior contracts in place |
| Slow process-boundary tests marked and budgeted | `grep -r "@pytest.mark.slow\|@pytest.mark.e2e" tests/e2e/features/` | `5a180dc` (retrospective) — `test_handoff_pipeline.py` and `test_cli_import.py` classified correctly |
| Full suite passes without regression | `pytest -q -p no:cacheprovider` | `5a180dc` (retrospective) — primary implementation commit landed with full suite green per session record |

## Drifts

### coverage-flags-moved-to-ci-only

**Description:** The SPEC and PLAN described removing `--cov*` from `addopts`. During
implementation it was observed that `pyproject.toml`'s `[tool.coverage.run]` block
needed the `data_file` redirect to `/tmp/dadaia-ws-toolcache/coverage/.coverage` as
well, to satisfy the no-cache-inside-repo invariant introduced in the sanitization
track (v0.1.4.4). This was an undeclared but necessary companion change.

**Resolution:** Coverage data file redirect added as part of the same commit. The
no-cache rule is an existing workspace invariant; the change aligned coverage with
it. No functional scope was added.

**Memory updates:** `specs/memory/product/test-suite-architecture.md` — new atom
created to capture the current test architecture. `specs/memory/tech-stack.md` — no
change needed; pytest and pytest-cov were already listed.

### tests-tmp-readme-documented

**Description:** PR-4 required `tests/tmp/**` to be excluded from default collection
and documented. The PLAN did not specify whether a `README.md` was required inside
`tests/tmp/` or merely a `conftest.py` exclude. Implementation chose a `README.md`
documenting the no-slop quarantine rules, which is more human-readable and serves as
the authoritative reference without adding a conftest dependency.

**Resolution:** `tests/tmp/README.md` authored as the primary documentation artifact.
`norecursedirs = ["tests/tmp"]` in `pyproject.toml` is the enforcement mechanism.

**Memory updates:** `specs/memory/product/test-suite-architecture.md` captures the
tmp quarantine rules.

## Memory updates

- `specs/memory/product/test-suite-architecture.md` — new feature atom created to
  capture the enforced test architecture: five layers (unit/contract/integration/e2e/tmp),
  marker taxonomy, CI job structure, no-slop policy, and runtime budgets.
- `specs/memory/product/index.md` — added `test-suite-architecture` to the feature
  catalog.
- `specs/memory/tech-stack.md` — no change: pytest and pytest-cov already listed;
  no new dependencies introduced by this release.
- `specs/memory/architecture.md` — no change: release operates entirely within the
  test layer; no architectural layer boundary changes.

## Backlog returns

No items surfaced during implementation of this release that did not fit scope.
All deferred items from the SPEC's Non-Goals remain non-goals:

- `backlog/ideas.md` ← `pytest-xdist` — parallel test execution not added in this
  release per SPEC §4; worth revisiting when unit-fast wall time exceeds 10 s
  consistently.

## Archive decision

**MOVE** — release directory will be moved to
`specs/_archive/releases/v0.1.4/` via `git mv`. `ACTIVE.md` will be updated
to point to the next release or `release: none`.
