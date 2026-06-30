---
slug: quality-assurance
title: quality-assurance
category: product
tldr: 'Behavior-first quality schema; the suite is ~1424 collected tests (budget 1000-1500).'
summary: >-
  The dadaia-workspace quality model is behavior-first. Tests are admitted only
  when they can fail for a meaningful regression in current product behavior,
  public contract, security boundary, data integrity, or a real operator journey.
  The suite is organized by layer, budgeted by cost, and optimized around the
  three critical product surfaces: Spec Context Projects, the Panel, and
  dadaia-workflows/lifecycle.
tags:
  - testing
  - pytest
  - ci
  - quality
  - test-architecture
agent_tier: self-pull
token_estimate: 1800
last_updated: '2026-06-30'
release_origin: v0.1.42
---

## Purpose

Quality assurance in dadaia-workspace is a product contract, not a coverage contest.
The test suite must prove that the current system works and remains safe to change. A
test is allowed only when it protects one of these things:

- current product behavior used by an operator or agent;
- public CLI/API/schema/projection contracts;
- security and workspace-boundary guarantees;
- data integrity for specs, sessions, handoffs, reports, run records, and policy stores;
- real end-to-end journeys for the product's critical surfaces.

Tests must not exist just because a release once had a bug, a folder was once deleted, a
private implementation string once drifted, or an old feature name might reappear. That
history belongs in bugs, release notes, and closure evidence unless it still protects a
named current boundary.

## Critical Surfaces

The suite is budgeted around the product's actual load-bearing surfaces.

1. **Spec Context Projects** — context binding, ALIVE/DEAD state, repo/workspace
   boundary detection, session identity, leases, SDD gate path classification, and
   chokepoint behavior.
2. **Dadaia Workspace Panel** — route dispatch, Host/security guards, active tab APIs,
   workflow policy mutation validation, telemetry/session rendering contracts, and a
   small set of browser journeys that click through real operator paths.
3. **dadaia-workflows/lifecycle** — run state transitions, handoff gates, runtime/model
   selection, prompt/context scoping, workflow-step handoff data, run-store safety, and
   retention/slop boundaries.

Secondary features still get coverage, but they do not get permanent matrix expansion
unless they own a current public contract or safety boundary.

## Layer Schema

**A test's directory IS its layer marker.** `conftest.pytest_collection_modifyitems`
auto-applies the layer marker (`unit`/`integration`/`contract`/`e2e`/`performance`) from
the test's top-level `tests/<layer>/` directory — tests are not individually decorated, so
a file placed in the wrong directory silently gets the wrong marker and CI profile. Place
each test in the directory that names its layer.

`tests/unit/**` is for compact public-service islands and pure rules that cannot be
tested more clearly at a higher layer. Unit tests may use `tmp_path` and small fakes, but
must not start real subprocesses, servers, browsers, public stage/install workflows, full
workspace initialization, or sleeps. Unit tests are not the default home for Panel view
strings, lifecycle prompt plumbing, hook parser permutations, infrastructure adapter
details, or specs-doctor implementation branches when those behaviors are already
protected by contract/integration/E2E tests.

`tests/contract/**` is for stable public contracts: CLI output shape, API/schema shape,
security boundaries, projection privacy, and governance invariants. Contract tests must
not become release-history pins. A residue grep is allowed only when it names the current
boundary being protected, the owner, and the condition under which the grep can retire.

`tests/integration/**` is the main behavior layer for dadaia-workspace. It owns
multi-component wiring: real temporary filesystem trees, Typer `CliRunner`, service
composition, stores, command paths, panel routes, lifecycle commands, public projection,
and gate behavior. Integration tests should prove one meaningful path through
collaborating components, not duplicate every unit matrix.

`tests/e2e/**` is for named user journeys. E2E tests must drive the behavior the user
depends on: click the tab, trigger the route, inspect the response, follow the iframe,
run the CLI command. Browser component harnesses with mocked APIs are allowed only when
the test is explicitly a browser-component test and cannot masquerade as full E2E.

`tests/performance/**` is explicit and opt-in. Performance tests may enforce operation
count, scan bounds, or wall-clock budgets, but they are not part of the blocking local
pre-push profile unless the measurement is robust under ordinary developer-machine
contention.

`tests/tmp/**` is for short-lived reproductions only. It is excluded from default
collection and must be deleted or promoted before release closure.

## Budgets

The target suite size is **1000-1500 collected tests** for the source repo; the suite is
behavior-layer-centered and currently collects **~1424** tests. A healthy split (current
live counts in parentheses) is:

- 450-650 unit tests for compact public-service islands and pure rules (currently ~622);
- 100-170 contract tests (currently ~163);
- 450-560 integration tests (currently ~555);
- 70-100 Python E2E and browser journey tests (currently ~83); the Node/Playwright panel
  journeys (~13 specs) run as a separate CI job (see Profiles);
- opt-in performance tests outside the default count (currently 1).

These are budgets, not quotas. Adding a test above budget requires either deleting lower
value coverage or documenting why the new behavior is more important than the cost.

## Profiles

The local developer loop is the smallest behavior suite that should catch ordinary
regressions:

```bash
.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider -m "unit and not slow" tests/unit
```

The pre-push/default quality gate should run lint, typecheck, contracts, and the curated
behavior suite, excluding E2E and performance unless explicitly requested:

```bash
.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider --ignore=tests/e2e -m "not performance"
```

The full release validation adds integration, E2E, and selected browser journeys while
still excluding opt-in performance checks:

```bash
.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider -m "not performance"
```

Performance validation is explicit:

```bash
.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider -m performance tests/performance
```

**Coverage gate.** Coverage is a diagnostic for the local loop — but CI **hard-gates 80%**
on the unit + contract suites (the contract-coverage job fails under `--cov-fail-under=80`).
Use coverage on curated unit/contract suites; do not write padding tests to lift a percentage.

**CI topology.** Beyond the Python profiles above, CI runs: lint (`ruff`), `mypy --strict`,
the unit / contract / integration / Python-E2E jobs, a **separate Node "E2E panel
(Playwright)" job** (`npm run test:e2e`, ~13 specs, driving the real panel in a browser),
and a **cross-platform matrix** (ubuntu + windows + macOS). Local pre-push runs lint +
`pytest -m "not performance"`; it does not run the Node panel job.

## Coverage by surface

Each surface is covered at the cheapest layer that proves its product behavior:

- **Spec Context Projects** — contract CLI tests, integration gate/classifier tests,
  context CLI flows, and E2E lease/chokepoint journeys.
- **Panel** — integration panel route/API tests plus the Playwright panel journey.
- **dadaia-workflows/lifecycle** — integration lifecycle CLI/pipeline/workflow tests,
  live-harness contracts (opt-in), and E2E lifecycle smoke.
- **Public projection and source hygiene** — contract and integration projection tests
  (privacy + drift).
- **Telemetry, reports, server registry, academy, workflows, backlog** — smaller unit or
  integration islands where each owns a current service/API behavior.

Coverage favors the layer that catches a regression most cheaply; low-level
implementation-shape matrices are not retained once the public behavior is covered at a
higher layer. Reintroducing a removed test requires naming the current behavior boundary
and explaining why a retained layer cannot catch the regression.

## No-Slop Law

Every test must have a purpose sentence that can be read as a current regression risk.
Delete or rewrite tests that primarily do any of the following:

- prove deleted code, retired command names, or old file paths remain absent;
- duplicate private constants as a second source of truth;
- assert release/task/PR history instead of current behavior;
- snapshot internal text with no public contract;
- repeat the same matrix at unit, integration, and E2E layers;
- test private helper branches after the public behavior is already protected elsewhere;
- mock every dependency and then call the result "E2E";
- gate pre-push on host-load-sensitive wall-clock performance.

Residue checks are exceptional. They are allowed only for a named current boundary such
as credential leakage, unsupported public CLI resurrection, projected privacy, or
backward compatibility. Each residue check must state the protected boundary and its
retirement condition.

## Ownership

Implementers own focused unit and integration tests for their change. `qa-engineer` owns
journey selection, test-value review, and deletion pressure. `security-reviewer` owns
security-boundary tests. `product-engineer` owns this memory atom and decides when a
historical test should become release evidence instead of permanent suite cost.

When a bug escapes, the fix is not automatically "add one permanent test." First identify
the missed behavior boundary. Then choose the cheapest layer that would have caught it.
Only add an E2E test when the failure truly required a journey-level signal.

## Runtime State Touched

- `pyproject.toml` declares pytest markers and collection policy.
- `tests/conftest.py` applies the **auto-marker-by-directory** hook and the suite safety
  guards: `_no_real_venv` (blocks real venv/pip builds inside tests), the repo-root-write
  guard, the snapshot guard (fails a test that writes the repo tree unexpectedly — which is
  why parallel writers must not run pytest mid-edit), and `tests/tmp` retention control.
- `tests/AGENTS.md` is the scoped operational rule for all test files.
- `tests/contract/README.md` inventories public contracts and must not contradict the
  no-slop law.
- `tests/e2e/` also hosts the Node/Playwright panel suite (`npm run test:e2e`); its
  `node_modules/` is gitignored and never committed, and the job runs separately from the
  Python pytest jobs.
- `dadaia_workspace/features/ci_preflight/service.py` defines the local/pre-push gate.
- `.github/workflows/*.yml` runs the broader CI profiles (lint, mypy, the pytest jobs, the
  Node panel job, and the cross-platform matrix); local hooks stay deterministic and useful.

## Dependencies

- [[spec-context-project]] — the central product surface that test architecture must keep
  safe.
- [[panel]] — the primary local operator UI; browser tests must cover real interactions,
  not only labels.
- [[lifecycle-foundation]] — the deterministic workflow engine; tests must protect Python
  gates and runtime boundaries without overfitting to prompt history.
- [[public-asset-distribution]] — projection privacy and drift checks remain legitimate
  contract coverage when they protect shipped runtime surfaces.
