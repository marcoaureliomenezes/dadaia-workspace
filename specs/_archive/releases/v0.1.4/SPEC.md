# SPEC: v0.1.4 - test-suite-architecture

**Status:** Aprovado
**Release ID:** v0.1.4
**Owner:** product-engineer
**Created:** 2026-06-03

---

## 1. Objective

Replace the current accumulated test pile with an explicit, enforceable test
architecture for `dadaia-workspace`.

The suite must stop accepting tests whose only value is preserving release
history, implementation accidents, deleted-code assertions, line-coverage
padding, or one-off agent debugging. Tests must protect current product
behavior, public contracts, security boundaries, data integrity, and real user
journeys.

## 2. Evidence

This release is grounded in two reports:

- `.dadaia/reports/dadaia-workspace/qa-engineer/2026-06-03T120000Z-test-suite-audit.html`
- `.dadaia/reports/dadaia-workspace/code-reviewer/2026-06-03T132243Z-test-suite-architecture-review.html`

Confirmed current-state evidence:

- `pyproject.toml` embeds coverage in default pytest `addopts`.
- No pytest marker taxonomy exists for `unit`, `contract`, `integration`,
  `e2e`, `slow`, or `tmp`.
- `tests/tmp/` is not an enforced temporary quarantine.
- CI and release workflows run one giant `poetry run pytest -q`.
- Targeted collection over known bad candidates collected 499 tests.
- `tests/unit/test_r2_qa_gaps.py` is a 1,974-line release/coverage archive with
  `AC-COV`, `R-2`, deleted-method, and line-coverage tests.
- Panel PR-history files such as `test_assets_pr3_10.py`,
  `test_assets_pr3_16.py`, `test_assets_pr3_17.py`,
  `test_pr304_theme_switcher.py`, and `test_views_index.py` contain many
  string-presence, negative deleted-code, and per-element UI structure tests.
- `tests/e2e/features/test_handoff_pipeline.py` and
  `tests/integration/test_cli_import.py` are legitimately slow process-boundary
  tests and must be budgeted outside the local unit loop.

## 3. Product Requirements

### PR-1: Executable Test Taxonomy

`pytest` must expose machine-readable markers:

- `unit`
- `contract`
- `integration`
- `e2e`
- `slow`
- `tmp`

Directory placement alone is not enough. The default collection policy must
exclude temporary tests.

### PR-2: Fast Local Default

Default pytest invocation must not run coverage instrumentation. Coverage must
remain enforced by an explicit CI command or job.

The local fast path must be:

```bash
pytest -q -m "unit and not slow" tests/unit
```

### PR-3: Contract Layer

Add `tests/contract/**` for public behavior that is not pure unit and not a full
journey:

- CLI output/status contracts.
- JSON schema and report handoff contracts.
- Public asset manifest/projection contracts.
- SDD doctor invariants.
- Gate policy contracts.
- Panel API envelope/security contracts.

### PR-4: Temporary Test Quarantine

Create `tests/tmp/**` as the only allowed location for one-off reproduction
tests created during debugging. It must be excluded from default pytest
collection. Temporary tests must not satisfy coverage, CI, or release closure.

### PR-5: Slop/Dead Test Removal

Delete or rewrite tests whose primary assertion is one of:

- Deleted code remains deleted.
- A retired invariant remains retired.
- A legacy alias or old implementation detail is absent.
- A private constant equals a duplicated literal in test code.
- A test exists only to touch uncovered lines.
- A test file is named after a PR, task, release, or QA gap instead of current
  behavior.

Preserve current security, schema, data-integrity, public API, and user-journey
contracts.

### PR-6: CI Layer Split

CI must stop running the suite as one undifferentiated command. Required jobs:

- lint
- typecheck
- unit-fast
- contract-coverage
- integration
- e2e-python
- e2e-panel

### PR-7: Runtime Budgets

Budgets:

- Unit fast path: under 10 seconds locally without coverage.
- Contract suite: under 30 seconds.
- Integration suite: under 90 seconds in CI.
- Python E2E suite: under 120 seconds in CI.
- Any test over 1 second must be marked `slow` with a reason.

### PR-8: No New Slop Policy

The repo must contain documented rules that reject new slop tests:

- No tests named after PR/release/task ids.
- No deleted-code tests unless the behavior is a documented security or
  compatibility contract.
- No private constants duplicated into tests as the source of truth.
- No CLI runner, subprocess, real server, public stage/install, or full
  workspace init in `tests/unit/**`.
- One-off tests go to `tests/tmp/**`.

## 4. Non-Goals

- Do not lower the 80% coverage floor.
- Do not remove security/path traversal tests.
- Do not remove schema validator tests that protect current public contracts.
- Do not remove true process-boundary E2E journeys just because they are slow.
- Do not add `pytest-xdist` in this release unless explicitly amended.

## 5. Acceptance Criteria

### AC-1: Taxonomy Exists

`pyproject.toml` declares the required markers and excludes `tests/tmp`.

### AC-2: Default Pytest Is Fast-Path Friendly

`pyproject.toml` no longer embeds `--cov*` in `addopts`; coverage is run only by
explicit CI command/job.

### AC-3: CI Is Split By Layer

`.github/workflows/ci.yml` and release workflow run separate layer commands
instead of a single giant `poetry run pytest -q`.

### AC-4: Contract Layer Exists

`tests/contract/` exists and holds promoted public-contract tests from current
unit/integration piles.

### AC-5: Temporary Quarantine Exists

`tests/tmp/` exists, is excluded from collection, and is documented as temporary
only.

### AC-6: R2 Coverage Archive Removed

`tests/unit/test_r2_qa_gaps.py` is deleted or split into current behavior tests
with no `AC-COV`, line-number coverage, or deleted-method assertions remaining.

### AC-7: Panel PR-History Tests Collapsed

Panel PR/task history files are deleted, renamed around current behavior, or
collapsed into meaningful parameterized contracts. Current observable behavior
remains covered.

### AC-8: Retired/Deleted Invariant Tests Removed

Known stale examples are removed or rewritten:

- `tests/unit/features/panel/test_memory_byte_identity.py`
- `tests/unit/features/panel/test_palette.py`
- deleted-method tests in `tests/unit/test_spec_context_service.py`
- removed-invariant tests in `tests/unit/test_spec_context_doctor.py`

### AC-9: Slow Journey Tests Budgeted

`tests/e2e/features/test_handoff_pipeline.py` and
`tests/integration/test_cli_import.py` are marked/classified correctly. Full
handoff happy path remains; strict invalid-schema checks move to contract/unit
where possible.

### AC-10: Verification

Required validation:

```bash
poetry run python -m pytest -q -m "unit and not slow" tests/unit
poetry run python -m pytest -q -m "contract and not slow" tests/contract
poetry run python -m pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
poetry run python -m pytest -q -m integration tests/integration --durations=30
poetry run python -m pytest -q -m e2e tests/e2e/features --durations=30
npm run test:e2e
```
