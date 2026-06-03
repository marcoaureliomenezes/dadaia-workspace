# Test Architecture

Tests must protect current product behavior, public contracts, security
boundaries, data integrity, and real user journeys. They must not preserve
release history or implementation residue.

## Layers

- `tests/unit/**`: pure or near-pure behavior. No `CliRunner`, real subprocess
  execution, real server, public stage/install, full workspace init, network, or
  sleeps. Process-boundary units may patch the runner; they must not spawn a
  process.
- `tests/contract/**`: public API, CLI output/status, schema, security,
  projection, and gate/doctor contracts. In-process `CliRunner` tests belong
  here when they assert public command behavior.
- `tests/integration/**`: multi-component tests with real tmp filesystem,
  service wiring, and CLI runner.
- `tests/e2e/**`: named process-boundary journeys.
- `tests/tmp/**`: temporary debugging reproductions only. Excluded from
  default collection and never used for coverage or release closure.

## No Slop Policy

- Do not write tests that only prove deleted code remains deleted.
- Do not duplicate private constants in tests and call that a contract.
- Do not name test files after PR, release, task, or QA-gap identifiers.
- Do not add line-coverage padding tests.
- Move one-off debugging tests to `tests/tmp/**` with an expiry note, then
  delete or promote them before release closure.
- Mark any test over 1 second with `@pytest.mark.slow` and keep it out of the
  local unit loop.

## Commands

```bash
pytest -q -m "unit and not slow" tests/unit
pytest -q -m "contract and not slow" tests/contract
pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
pytest -q -m integration tests/integration --durations=30
pytest -q -m e2e tests/e2e/features --durations=30
npm run test:e2e
```
