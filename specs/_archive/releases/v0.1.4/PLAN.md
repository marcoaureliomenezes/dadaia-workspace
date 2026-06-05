# PLAN: v0.1.4 - test-suite-architecture

**Status:** Aprovado
**Release ID:** v0.1.4
**Owner:** product-engineer
**Created:** 2026-06-03

---

## 1. Strategy

Do the cleanup in enforceable layers, not by random deletion.

First stop new slop from entering the suite by adding taxonomy, commands,
`tests/tmp`, and CI split. Then delete or rewrite stale release-history tests.
Finally consolidate high-volume panel assertions and budget true integration/E2E
journeys.

## 2. Execution Order

```text
T-TEST-01 -> T-TEST-02 -> T-TEST-03 -> T-TEST-04 -> T-TEST-05
          -> T-TEST-06 -> T-TEST-07 -> T-TEST-08 -> T-TEST-09
```

## 3. Design

### Test Layers

Layer | Directory | Allowed | Forbidden
---|---|---|---
Unit | `tests/unit/**` | pure functions, small services with in-memory fakes, validators, deterministic parsers | CLI runner, subprocess, server threads, public install/stage, full workspace init, sleeps
Contract | `tests/contract/**` | public CLI/API/schema/security/projection contracts | browser, long journey setup, private implementation matrices
Integration | `tests/integration/**` | real tmp filesystem, Typer `CliRunner`, multi-component service wiring | browser, real remotes, duplicate unit matrices
E2E | `tests/e2e/**` | named user journeys and process-boundary flows | micro assertions, implementation internals, exhaustive branch matrices
Temporary | `tests/tmp/**` | one-off debugging reproductions | default collection, CI, coverage, release closure

### Pytest Policy

Target `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"
markers = [
  "unit: pure or near-pure fast tests",
  "contract: public API/schema/security contracts",
  "integration: multi-component tests using real tmp filesystem or CLI runner",
  "e2e: full user journeys and browser-backed flows",
  "slow: any test over 1s or any test that starts a server/subprocess",
  "tmp: temporary debugging tests excluded from default runs",
]
norecursedirs = ["tests/tmp"]
tmp_path_retention_policy = "failed"
```

### CI Shape

Use explicit commands:

```bash
pytest -q -m "unit and not slow" tests/unit
pytest -q -m "contract and not slow" tests/contract
pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
pytest -q -m integration tests/integration --durations=30
pytest -q -m e2e tests/e2e/features --durations=30
npm run test:e2e
```

### Deletion/Rewriting Rules

Delete without replacement when a test only proves:

- a removed method does not exist;
- an old alias is absent;
- a retired pipeline does not generate old artifacts;
- a file contains or does not contain one private implementation string;
- a branch is covered only to satisfy an old `AC-COV` target.

Rewrite when the same file also contains current contracts:

- security/path traversal;
- content type and API envelope;
- current schema validation;
- current CLI status/output;
- current public projection manifest;
- current gate/doctor invariant.

## 4. Candidate Files

Path | Action
---|---
`tests/unit/test_r2_qa_gaps.py` | Delete as release/coverage archive after moving any still-current lock/doctor contracts to named contract/unit files.
`tests/unit/test_spec_context_service.py` | Delete `activate/deactivate/promote does not exist` tests; keep alive/dead/delete behavior tests.
`tests/unit/test_spec_context_doctor.py` | Delete removed invariant tests; keep current INV-4/INV-5 behavior.
`tests/unit/features/panel/test_memory_byte_identity.py` | Keep traversal/content-type contracts; remove retired byte-identity canaries.
`tests/unit/features/panel/test_palette.py` | Delete exact duplicated hex tests or rewrite as token source-of-truth contract.
`tests/unit/features/panel/test_assets_pr3_10.py` | Rename/consolidate into current agents asset contract; delete negative IIFE-deletion assertions.
`tests/unit/features/panel/test_assets_pr3_16.py` | Rename/consolidate into current workflows list asset contract; delete negative extraction assertions.
`tests/unit/features/panel/test_assets_pr3_17.py` | Collapse string-presence checks into parameterized workflow detail contract.
`tests/unit/features/panel/test_pr304_theme_switcher.py` | Rename/consolidate into current theme switcher contract; parameterize ARIA/static assertions.
`tests/unit/features/panel/test_views_index.py` | Collapse per-element checks into parameterized navigation/project-shell contract; keep XSS/order tests.
`tests/e2e/features/test_handoff_pipeline.py` | Keep one full emit/validate/install journey; move invalid strict schema checks to contract validator tests where possible.
`tests/integration/test_cli_import.py` | Keep import journey; move tar/archive parser edge cases to unit/contract.

## 5. Validation

Run focused tests after each deletion/consolidation wave, then run the full
layered validation commands from SPEC AC-10.

If coverage falls below 80%, add real contract/unit tests for current behavior.
Do not add line-coverage padding tests.
