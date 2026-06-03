# Test Rules — dadaia-workspace

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them.

## Architecture

- `tests/unit/**`: pure or near-pure tests only. No `CliRunner`, real subprocess
  execution, server threads, public stage/install, full workspace init, network,
  sleeps, or real git remotes. Process-boundary units may patch the runner; they
  must not spawn a process.
- `tests/contract/**`: public CLI/API/schema/security/projection/gate contracts.
- `tests/integration/**`: multi-component tests using tmp filesystem, service
  wiring, or CLI runner.
- `tests/e2e/**`: named end-to-end journeys only.
- `tests/tmp/**`: temporary debugging reproductions only; excluded from default
  collection and deleted or promoted before closure.

## No Slop

- Do not add tests that only prove deleted code remains deleted.
- Do not add tests for retired invariants, old aliases, migration residue, or
  private implementation strings unless they protect a documented security or
  compatibility contract.
- Do not duplicate private constants in tests as the source of truth.
- Do not write coverage-padding tests.
- Do not name test files after PRs, tasks, releases, or QA gaps. Name current
  behavior instead.

## Markers And Cost

- Layer markers are applied automatically by directory via `tests/conftest.py`.
- Add `@pytest.mark.slow(reason="...")` to any test over 1 second or any test
  that starts a subprocess/server.
- The local loop is:

```bash
pytest -q -m "unit and not slow" tests/unit
```

Coverage is not the default loop. Use explicit coverage only for curated
unit/contract runs:

```bash
pytest -q -m "unit or contract" --cov=dadaia_workspace --cov-report=term-missing --cov-fail-under=80
```

## Good Test Standard

A test is allowed only if it can fail for a meaningful regression in current
product behavior, public contract, security boundary, data integrity, or a real
user journey. If it mainly records implementation history, put it in release
notes or delete it.
