---
slug: quality-assurance
title: quality-assurance
category: product
tldr: 'Five-layer pytest architecture, CI 7-job split, no-slop policy — design-of-record for implementers and qa-engineer.'
summary: >-
  Enforced five-layer test architecture (unit/contract/integration/e2e/tmp) with
  machine-readable pytest markers, a CI split into 7 jobs with explicit timeouts,
  and a no-slop policy. This atom is the single source of truth for test design,
  absorbing test-suite-architecture.md (v0.1.7).
tags:
  - testing
  - pytest
  - ci
  - quality
  - test-architecture
agent_tier: self-pull
token_estimate: 900
last_updated: '2026-06-07'
release_origin: v0.2.1
---

## Propósito

dadaia-workspace uses an enforced five-layer test architecture. The five layers
are: `unit` (pure or near-pure functions, fastest), `contract` (public CLI/API/
schema/security contracts), `integration` (multi-component with real filesystem or
CLI runner), `e2e` (named user journeys, browser or process-boundary), and `tmp`
(one-off debugging reproductions, quarantined and excluded from default collection).

Each layer has a machine-readable pytest marker declared in `pyproject.toml`. The
default local invocation (`pytest`) does not run coverage; coverage is measured only
in CI's dedicated `contract-coverage` job, keeping local runs fast and avoiding
coverage inflation that hides weak contracts.

The no-slop policy is the durable rule that prevents a test pile from accumulating:
no test may be named after a PR, release, or task id; no test may assert that
deleted code remains deleted; private constants must not be duplicated into test
code as the source of truth; one-off debugging tests go to `tests/tmp/` only with
an expiry note.

This atom is the design-of-record for implementers and qa-engineer. It is the
canonical path per constitution §13 (`specs/memory/quality-assurance.md`) and the
normative vision §6. The former location `specs/memory/product/sdd/quality-assurance.md`
is non-conformant and staged for deletion at v0.2.1 CLOSURE.

## Fluxo de uso

1. Developer picks the test layer based on what the test exercises: pure function
   → `unit`; public CLI/schema/security → `contract`; multi-component with real
   filesystem or CLI runner → `integration`; user journey or browser → `e2e`.
2. Test receives the corresponding `@pytest.mark.<layer>` decorator. Any test over
   1 second or that starts a server or subprocess also receives
   `@pytest.mark.slow`.
3. Local fast path: `pytest -q -m "unit and not slow" tests/unit` — runs in under
   10 seconds without coverage instrumentation.
4. CI runs 7 jobs: lint, typecheck, unit-fast, contract-coverage, integration,
   e2e-python, e2e-panel — each with an explicit timeout and a targeted marker
   filter.
5. One-off debugging reproductions go to `tests/tmp/` with an expiry note; they
   are never counted toward coverage or release closure and are excluded from
   default collection.

## Trigger típico

Used when implementing a new feature, refactoring a public contract, or reproducing
a CI failure.

## Diferencial

Without the layer taxonomy there is no enforceable boundary between fast pure-unit
tests and slow process-boundary journeys: local runs become slow, coverage
instrumentation in default addopts inflates numbers and hides weak contracts, and
release-history tests accumulate protecting deleted code. The three failure modes
are closed simultaneously by: the layer taxonomy (boundary enforcement via markers),
the CI split into 7 jobs (each job targets its layer, with its own timeout), and
the no-slop policy (prevents re-accumulation).

## Estado runtime tocado

Files the test suite reads or writes at runtime:

- `pyproject.toml` — pytest configuration, marker declarations, `norecursedirs`,
  coverage data redirect to `/tmp/dadaia-ws-toolcache/coverage/.coverage`.
- `tests/unit/**` — pure or near-pure fast tests; forbidden: CLI runner,
  subprocess, server threads, public stage/install, full workspace init, sleeps.
- `tests/contract/**` — public CLI/API/schema/security/projection contracts;
  forbidden: browser, long journey setup, private implementation matrices.
- `tests/integration/**` — real tmp filesystem, Typer `CliRunner`, multi-component
  service wiring; forbidden: browser, real remotes, duplicate unit matrices.
- `tests/e2e/**` — named user journeys and process-boundary flows; forbidden:
  micro assertions, implementation internals, exhaustive branch matrices.
- `tests/tmp/**` — one-off debugging reproductions only; excluded from default
  collection, CI, and coverage. Each subdirectory must include an expiry note.
- `.github/workflows/ci.yml` — seven CI jobs consuming the layer-specific pytest
  commands with explicit timeouts.
- `tests/conftest.py` — backstop guard preventing real venv creation inside test
  runs; `tmp_path_retention_policy = "failed"`.

## Dependências

- [[specs-doctor]] — `dadaia specs doctor` validates SDD structural invariants;
  the test layer and the specs gate are separate quality gates at different scopes.
- [[public-asset-distribution]] — `tests/contract/test_source_repo_hygiene.py` and
  `tests/unit/features/public/` hold contracts for the public asset pipeline.
- [[agent-comms]] — `tests/contract/test_handoff_schema_contract.py` protects the
  handoff-v1.1 JSON schema contract.
- [[sdd-gate-v3]] — `tests/unit/gate/` and `tests/integration/gate/` hold
  the unit and integration tests for the SDD enforcement gate.
