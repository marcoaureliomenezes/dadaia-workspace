# PLAN: v0.1.34 alpha-1 - behavior-first test architecture

**Status:** Aprovado
**Release ID:** v0.1.34
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Approach

Start with governance and the highest-confidence slop removals, then collapse redundant
test clusters until the collected suite lands in the 1000-1500 range. Tests must be
justified by current behavior, not by release history.

## Implementation Plan

### 1. Rewrite the QA schema

Update `specs/memory/quality-assurance.md` to define:

- behavior-first test law;
- layer taxonomy and allowed dependencies;
- explicit suite budgets;
- local/pre-push/full profiles;
- residue-test exception rule;
- ownership for Spec Context Project, Panel, and lifecycle workflow tests.

### 2. Fix governance contradiction

Update `tests/contract/README.md` so contract tests are for public APIs, schemas,
security boundaries, projection privacy, and governance invariants. Remove the lifecycle
asymmetry coverage map and its completeness requirement.

Delete `tests/contract/test_lifecycle_asymmetry_map.py`.

### 3. Remove obvious residue-only tests

Delete or convert tests whose only assertion is the absence of retired implementation
history. Initial high-confidence deletion set:

- `tests/contract/test_plugin_install_residue.py`
- `tests/contract/test_bash_hook_residue.py`
- the residue-grep half of `tests/contract/test_retired_model_id_residue.py`

Keep behavior checks when they protect current behavior, such as "retired model ids do
not resolve through the model registry".

### 4. Move performance out of default gate

Introduce a `performance` pytest marker and mark
`tests/performance/test_lifecycle_hygiene_scan.py` so default preflight can deselect it.
Update `dadaia_workspace/features/ci_preflight/service.py` and tests so pre-push uses
the behavior suite, not synthetic wall-clock performance.

### 5. Collapse redundant clusters to budget

Use collection data to identify high-count clusters. For each cluster, keep tests that
protect distinct current behavior and delete tests that only restate helper mechanics,
deleted implementation history, fixture plumbing, or duplicate permutations already
covered at a better layer.

Primary reduction order:

- redundant unit tests around internal helper branches when an integration or contract
  test already proves the public behavior;
- generated/schema round-trip permutations that do not add boundary coverage;
- panel view string-shape tests that duplicate route/API tests;
- lifecycle workflow micro-tests that duplicate the state-machine, pipeline, or real
  workflow-path tests;
- E2E/browser scenarios that are not real operator journeys.

### 6. Validate and count

Run collection before/after and focused suites:

```bash
.dadaia/.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider
.dadaia/.venv/bin/python -m pytest -q -p no:cacheprovider \
  tests/contract \
  tests/unit/features/spec_context \
  tests/unit/features/panel \
  tests/unit/features/lifecycle
.dadaia/.venv/bin/dadaia specs doctor --specs-dir repos/dadaia-workspace/specs
```

Record remaining count and any deferred cleanup in the closure evidence.

## Risk Controls

- Do not delete tests that are the only guard for a security boundary.
- Prefer converting a residue test into a current behavior test when the boundary still
  matters.
- Keep at least one behavior guard per critical public boundary before deleting a cluster.
