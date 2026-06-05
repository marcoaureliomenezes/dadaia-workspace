---
slug: test-suite-architecture
title: test-suite-architecture
category: product
tldr: 'Five-layer pytest architecture: unit/contract/integration/e2e/tmp with marker taxonomy, CI split into 7 jobs, no-slop policy, coverage CI-only.'
summary: >
  Enforced test architecture for dadaia-workspace: five layers (unit, contract,
  integration, e2e, tmp) each with a machine-readable pytest marker and a documented
  write-policy. CI runs seven separate jobs with explicit timeouts. Coverage is
  CI-only (not in local addopts). tests/tmp is quarantined from default collection.
  No-slop policy documented in CONTRIBUTING.md and tests/tmp/README.md.
tags:
  - testing
  - test-architecture
  - pytest
  - ci
  - quality
agent_tier: self-pull
token_estimate: 810
last_updated: '2026-06-04'
release_origin: v0.1.4
---

## Propósito

dadaia-workspace has an enforced five-layer test architecture introduced in release
v0.1.4. The architecture replaced an accumulated test pile that had no marker taxonomy,
embedded coverage flags in the default pytest invocation, no contract layer, no
temporary quarantine, and a significant volume of release-history tests that protected
deleted code rather than current behavior.

Each layer has a machine-readable pytest marker declared in `pyproject.toml`. The
default local invocation (`pytest`) does not run coverage; coverage is measured only in
CI's dedicated `contract-coverage` job. The `tests/tmp/` directory is excluded from
default collection and serves only as a debugging quarantine.

The no-slop policy is the durable rule that prevents the pile from re-accumulating:
no test may be named after a PR, release, or task id; no test may assert that deleted
code remains deleted; private constants must not be duplicated into test code as the
source of truth; one-off debugging tests go to `tests/tmp/` only.

## Fluxo de uso

1. A developer writes a new test. They pick the correct layer based on what the test
   exercises (pure function → `unit`, public CLI/schema/security → `contract`,
   multi-component with real filesystem or CLI runner → `integration`, user journey or
   browser → `e2e`).
2. The test receives the corresponding `@pytest.mark.<layer>` decorator. Any test over
   1 second or that starts a server/subprocess also receives `@pytest.mark.slow`.
3. Local fast path: `pytest -q -m "unit and not slow" tests/unit` — runs in under
   10 seconds without coverage instrumentation.
4. CI runs all seven jobs: lint, typecheck, unit-fast, contract-coverage, integration,
   e2e-python, e2e-panel — each with an explicit timeout and a targeted marker filter.
5. A one-off debugging reproduction goes into `tests/tmp/` with an expiry note; it is
   never counted toward coverage or release closure.

## Trigger típico

Used whenever a new feature is implemented, a refactor changes a public contract, or a
CI job fails and the developer needs to reproduce the failure locally in the fast path.

## Diferencial

Without this architecture the suite has no enforceable boundary between fast pure-unit
tests and slow process-boundary journeys: local runs become slow, coverage inflation
hides weak contracts, and release-history tests keep accumulating. The layer taxonomy
plus the CI split plus the no-slop policy close all three failure modes simultaneously.

## Estado runtime tocado

Files the test suite reads or writes at runtime:

- `pyproject.toml` — pytest configuration, marker declarations, `norecursedirs`, coverage
  data redirect (`/tmp/dadaia-ws-toolcache/coverage/.coverage`).
- `tests/unit/**` — pure or near-pure fast tests; forbidden: CLI runner, subprocess,
  server threads, public stage/install, full workspace init, sleeps.
- `tests/contract/**` — public CLI/API/schema/security/projection contracts; forbidden:
  browser, long journey setup, private implementation matrices.
- `tests/integration/**` — real tmp filesystem, Typer `CliRunner`, multi-component
  service wiring; forbidden: browser, real remotes, duplicate unit matrices.
- `tests/e2e/**` — named user journeys and process-boundary flows; forbidden: micro
  assertions, implementation internals, exhaustive branch matrices.
- `tests/tmp/**` — one-off debugging reproductions only; excluded from default collection,
  CI, and coverage. Each subdirectory must include an expiry note.
- `.github/workflows/ci.yml` — seven CI jobs consuming the layer-specific pytest commands.
- `tests/conftest.py` — backstop guard preventing real venv creation inside test runs
  (`_no_real_venv_in_tests`); `tmp_path_retention_policy = "failed"`.

## Dependências

- [[specs-doctor]] — `dadaia specs doctor` validates SDD structural invariants; the test
  layer is separate but both enforce quality gates at different scopes.
- [[public-asset-distribution]] — `tests/contract/test_source_repo_hygiene.py` and
  `tests/unit/features/public/` hold contracts for the public asset pipeline.
- [[agent-comms]] — `tests/contract/test_handoff_schema_contract.py` protects the
  handoff-v1.1 JSON schema contract.
- [[sdd-gate-v3]] — `tests/integration/test_gate_session_locks.py` holds integration
  tests for the SDD enforcement gate (added in v0.1.4.5).
