# Test Rules — dadaia-workspace

These rules override general workspace guidance for everything under `tests/`.
Agents creating or editing tests must follow them. Full protocol: skill
`dd-test-stewardship`.

- Intent, admission, deletion, tombstone: `dd-test-stewardship`; slop: `DADAIA.md` §7.6 and `specs/memory/QUALITY.md` fixed section.

## Architecture

- `tests/unit/**`: pure or near-pure tests only. No real subprocess execution,
  server threads, CLI runners, full workspace init, network, sleeps, or real git
  remotes. Process-boundary units may patch the runner; they must not spawn a
  process.
- `tests/contract/**`: public CLI/API/schema/security/projection/gate contracts.
- `tests/integration/**`: multi-component tests using tmp filesystem, service
  wiring, or CLI runner.
- `tests/e2e/**`: named end-to-end journeys only. Every file names an owner.
- `tests/tmp/**`: temporary debugging reproductions only; excluded from default
  collection and deleted or promoted before closure.

## Size tiers and cost

| Tier (marker) | Directory | Timeout default | Owner rule |
|---|---|---|---|
| `unit` | `tests/unit/**` | 10 s | — |
| `contract` | `tests/contract/**` | 30 s | — |
| `integration` | `tests/integration/**` | 60 s | — |
| `e2e` (LARGE) | `tests/e2e/**` | 120 s | every file names an owner |

A test that needs more time than its tier's default is **mis-tiered** — fix the
tier, never raise the default. The LARGE-tier census cap lives in exactly one
place — `dd-test-stewardship/PARAMETERS.md`'s "LARGE (E2E) cap" row — measured
as a WARN by V29 (`tests/contract/test_test_suite_ratchets.py`); this file does
not restate the number.

`flaky` and `quarantine` markers are registered in `pyproject.toml`; a
`quarantine` marker without `bug="<bug-slug>"` refuses collection, and every
gating selector (CI jobs, release jobs, the pre-push preflight) excludes the
quarantine lane. Diagnosis runs use `-m quarantine` explicitly.

## Markers and cost

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
