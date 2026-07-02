---
slug: quality-assurance
title: quality-assurance
category: core
tldr: 'Five-layer pytest architecture, multi-job CI (10 quality + 5 governance), no-slop policy — design-of-record for implementers and qa-engineer.'
summary: >-
  Enforced five-layer test architecture (unit/contract/integration/e2e/tmp) with
  machine-readable pytest markers, a CI split into 10 quality jobs (plus 5 governance
  jobs) with explicit timeouts, conftest safety guards, a CI-only 80% coverage gate,
  and a no-slop policy.
tags:
  - testing
  - pytest
  - ci
  - quality
  - test-architecture
agent_tier: self-pull
token_estimate: 1250
last_updated: '2026-07-02'
release_origin: v0.1.48
---

## Purpose

dadaia-workspace uses an enforced five-layer test architecture. The five layers
are: `unit` (pure or near-pure functions, fastest), `contract` (public CLI/API/
schema/security contracts), `integration` (multi-component with real filesystem or
CLI runner), `e2e` (named user journeys, browser or process-boundary), and `tmp`
(one-off debugging reproductions, quarantined and excluded from default collection).

Each layer has a machine-readable pytest marker declared in `pyproject.toml`; test
order is randomized per run by `pytest-randomly` (flushes inter-test order
dependencies). The default local invocation (`pytest`) does not run coverage; the
**only** coverage gate is CI's dedicated `contract-coverage` job
(`--cov-fail-under=80`, a hard gate; `COVERAGE_FILE` redirected to the runner temp
dir), keeping local runs fast and avoiding coverage inflation that hides weak
contracts.

**Live scale (honest bracket):** the suite collects ≈ 4.3k tests (4,300–4,400 as of
v0.1.47; grows with every release). Rough layer shape: unit is the large base,
contract and integration are the mid hundreds each, e2e is the small top. Budgets are
brackets, not pins — re-validate against `pytest --collect-only -q | tail -1` at
closure.

```mermaid
flowchart TB
    subgraph PYR["Test architecture — 5 layers (pytest markers)"]
        direction TB
        E["e2e — named user journeys · process boundary"]
        IT["integration — real fs · Typer CliRunner · multi-component"]
        CT["contract — CLI / API / schema / security / projection"]
        U["unit — pure / near-pure · fastest (base)"]
        E --> IT --> CT --> U
        TM["tmp — one-off repro · quarantined · excluded from default collection"]
    end
    PYR --> CI
    subgraph CI["CI — 10 quality jobs (+ 5 governance) · each with a timeout + marker filter"]
        direction LR
        J0["importability-smoke"]
        J1["lint<br/>ruff format --check + ruff check"]
        J2["typecheck<br/>mypy --strict"]
        J3["unit-fast<br/>(+ unit-fast-cross)"]
        J4["contract-coverage<br/>(+ contract-coverage-cross)"]
        J5["integration"]
        J6["e2e-python"]
        J7["e2e-panel<br/>(playwright/node)"]
    end
```

The three harness adapters (Codex/Claude-SDK/PI) follow the same taxonomy:
`unit` for command construction/parse/redaction/Ring-2, `integration` for the Layer-1
projection and the `--harness` CLI seam, and an **opt-in** `live` test
(`DADAIA_*_LIVE=1`, never CI-gated) for the real upstream binding.

The no-slop policy is the durable rule that prevents a test pile from accumulating:
no test may be named after a PR, release, or task id; no test may assert that
deleted code remains deleted; private constants must not be duplicated into test
code as the source of truth; one-off debugging tests go to `tests/tmp/` only with
an expiry note.

This atom is the design-of-record for implementers and qa-engineer. It is the
canonical path per constitution §13 (`specs/memory/quality-assurance.md`) and the
normative vision §6.

## Usage flow

1. Developer picks the test layer based on what the test exercises: pure function
   → `unit`; public CLI/schema/security → `contract`; multi-component with real
   filesystem or CLI runner → `integration`; user journey or browser → `e2e`.
2. Test receives the corresponding `@pytest.mark.<layer>` decorator. Any test over
   1 second or that starts a server or subprocess also receives
   `@pytest.mark.slow`.
3. Local fast path: `pytest -q -m "unit and not slow" tests/unit` — runs in under
   10 seconds without coverage instrumentation.
4. CI runs 10 quality jobs: importability-smoke, lint (ruff only — import-linter
   enforcement status stated once in [[architecture]] §Enforcement),
   typecheck, unit-fast, unit-fast-cross, contract-coverage, contract-coverage-cross,
   integration, e2e-python, e2e-panel — each with an explicit timeout and a targeted
   marker filter (the `-cross` jobs run the same markers on the Windows/macOS matrix;
   e2e-panel is a Playwright/Node job: `npm ci` + `npx playwright install chromium` +
   `npm run test:e2e` against a bootstrapped panel workspace). A further 5 governance
   jobs (pr-title, repo-hygiene, backlog-doctor, hotfix-branch-name, verdict-gate)
   gate PR shape, repo/backlog hygiene, and the security push verdict; a separate
   secret-scan workflow runs gitleaks.

## Typical trigger

Used when implementing a new feature, refactoring a public contract, or reproducing
a CI failure.

## Differentiator

Without the layer taxonomy there is no enforceable boundary between fast pure-unit
tests and slow process-boundary journeys: local runs become slow, coverage
instrumentation in default addopts inflates numbers and hides weak contracts, and
release-history tests accumulate protecting deleted code. The three failure modes
are closed simultaneously by: the layer taxonomy (boundary enforcement via markers),
the CI split into per-layer jobs (each job targets its layer, with its own timeout), and
the no-slop policy (prevents re-accumulation).

## Runtime state touched

Files the test suite reads or writes at runtime:

- `pyproject.toml` — pytest configuration (`-p no:cacheprovider`), marker
  declarations, `norecursedirs`, `tmp_path_retention_policy = "failed"`.
- `tests/unit/**` — pure or near-pure fast tests; forbidden: CLI runner,
  subprocess, server threads, public stage/install, full workspace init, sleeps.
- `tests/contract/**` — public CLI/API/schema/security/projection contracts;
  forbidden: browser, long journey setup, private implementation matrices.
- `tests/integration/**` — real tmp filesystem, Typer `CliRunner`, multi-component
  service wiring; forbidden: browser, real remotes, duplicate unit matrices.
- `tests/e2e/**` — named user journeys and process-boundary flows; forbidden:
  micro assertions, implementation internals, exhaustive branch matrices.
- `tests/tmp/**` — the `tmp`-layer quarantine (rules stated once in Purpose and
  the no-slop policy).
- `.github/workflows/ci.yml` — 10 quality jobs (importability-smoke, lint,
  typecheck, unit-fast(+cross), contract-coverage(+cross), integration, e2e-python,
  e2e-panel) consuming the layer-specific pytest commands with explicit timeouts,
  plus 5 governance jobs (pr-title, repo-hygiene, backlog-doctor,
  hotfix-branch-name, verdict-gate). `secret-scan.yml` (gitleaks) is a separate
  workflow.
- `tests/conftest.py` — the safety guards: `_no_real_venv_in_tests` (autouse; blocks
  real venv/pip provisioning inside tests — disk-exhaustion backstop),
  `_repo_root_write_guard` (autouse per-test repo-root file-set snapshot diff), and a
  session-level pre/post snapshot pollution guard (`pytest_sessionstart`/`finish`)
  that catches cache/artifact leaks the per-test guard cannot.

## Dependencies

- [[specs-doctor]] — `dadaia specs doctor` validates SDD structural invariants;
  the test layer and the specs gate are separate quality gates at different scopes.
- [[public-asset-distribution]] — `tests/contract/test_source_repo_hygiene.py` and
  `tests/unit/features/public/` hold contracts for the public asset pipeline.
- [[agent-comms]] — `tests/contract/test_handoff_schema_contract.py` protects the
  handoff-v1.1 JSON schema contract.
- [[sdd-gate-v3]] — `tests/unit/gate/` and `tests/integration/gate/` hold
  the unit and integration tests for the SDD enforcement gate.
