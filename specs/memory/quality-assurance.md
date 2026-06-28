---
slug: quality-assurance
title: quality-assurance
category: product
tldr: 'Behavior-first quality schema; current suite budget is 1000-1500 tests.'
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
last_updated: '2026-06-28'
release_origin: v0.1.34
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

The target suite size is **1000-1500 collected tests** for the source repo. The v0.1.34
architecture keeps the suite centered on behavior layers; collected count after the
collapse is expected to stay near 1350 tests. A healthy split is:

- 450-650 unit tests for compact public-service islands and pure rules;
- 100-150 contract tests;
- 450-550 integration tests;
- 70-100 E2E and browser journey tests;
- opt-in performance tests outside the default count.

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

Coverage is a diagnostic, not the default local loop. Use coverage on curated
unit/contract suites only; do not write padding tests to lift a percentage.

## Retained Feature Coverage

The retained suite evaluates features by the cheapest layer that proves product behavior:

- **Spec Context Projects** — contract CLI tests, integration gate/classifier tests,
  context CLI flows, and E2E lease/chokepoint journeys. Deleted private unit matrices for
  lease states, hook path parsing, and doctor cleanup branches were duplicate
  implementation-shape coverage.
- **Panel** — integration panel route/API tests plus the panel E2E journey. Deleted unit
  view-string tests, CSS/token assertions, and handler fragment checks duplicated route
  and browser behavior while failing on private markup churn.
- **dadaia-workflows/lifecycle** — integration lifecycle CLI/pipeline/workflow tests,
  live harness contracts, and E2E lifecycle smoke. Deleted unit prompt/fragment/policy
  micro-tests duplicated command-path and workflow behavior or pinned prompt assembly
  internals.
- **Public projection and source hygiene** — contract and integration projection tests
  remain. Deleted infrastructure public-assets helper matrices that retested private TOML,
  hashing, and parsing helpers after the public install/doctor behavior was covered.
- **Telemetry, reports, server registry, academy, workflows, backlog** — kept as smaller
  unit or integration islands where they own a current service/API behavior; removed
  low-level infrastructure and adapter permutations.

Deleted tests are release evidence, not product truth. Reintroducing a removed file
requires naming the current behavior boundary and explaining why a retained layer cannot
catch the regression.

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
- `tests/AGENTS.md` is the scoped operational rule for all test files.
- `tests/contract/README.md` inventories public contracts and must not contradict the
  no-slop law.
- `dadaia_workspace/features/ci_preflight/service.py` defines the local/pre-push gate.
- `.github/workflows/*.yml` may run broader CI profiles, but local hooks must stay
  deterministic and useful.

## Dependencies

- [[spec-context-project]] — the central product surface that test architecture must keep
  safe.
- [[panel]] — the primary local operator UI; browser tests must cover real interactions,
  not only labels.
- [[lifecycle-foundation]] — the deterministic workflow engine; tests must protect Python
  gates and runtime boundaries without overfitting to prompt history.
- [[public-asset-distribution]] — projection privacy and drift checks remain legitimate
  contract coverage when they protect shipped runtime surfaces.
