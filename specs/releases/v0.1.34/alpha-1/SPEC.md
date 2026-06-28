# SPEC: v0.1.34 alpha-1 - behavior-first test architecture

**Status:** Aprovado
**Release ID:** v0.1.34
**Segment:** alpha-1
**Owner:** product-engineer
**Created:** 2026-06-28

---

## Objective

Reduce the dadaia-workspace test suite from accumulated historical coverage into a
behavior-first suite of **1000-1500 collected tests** that protects current product
value: Spec Context Projects, the Dadaia Workspace Panel, and dadaia-workflows/lifecycle.

The release must update `quality-assurance.md` so it becomes the canonical quality
schema for the project, not an aspirational description contradicted by the current
tests.

## Picked Bugs

- `test-governance-conflict-normalizes-residue-slop` — test governance contradicts
  itself: `tests/AGENTS.md` bans deleted-code residue tests while
  `tests/contract/README.md` blesses residue grep and a feature-wide lifecycle
  asymmetry map.
- `prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound` — a synthetic
  performance test with a wall-clock bound is part of the blocking pre-push path.

## Scope

### FR-1 — Quality-assurance memory is the schema of record

Rewrite `specs/memory/quality-assurance.md` around the current target quality model:

- tests protect current behavior, public contracts, security boundaries, data integrity,
  and real operator journeys;
- test layers are defined by what the test exercises, not by historical placement;
- residue tests are exceptional and require a named current boundary plus retirement
  condition;
- the suite has an explicit budget and a curated local/pre-push profile.

### FR-2 — Remove the residue-map ratchet

Remove the lifecycle-asymmetry coverage-map policy and the meta-test that mechanically
forces every `features/` subpackage into the map. Replace it with behavior-owned
contract guidance for the current critical flows.

### FR-3 — Delete or narrow dead-history tests

Remove tests whose primary purpose is to prove retired implementation details remain
deleted, unless they are protecting a named current security, compatibility, or public
contract boundary.

### FR-4 — Keep valuable coverage for the three critical product areas

Do not blindly delete tests. Preserve or consolidate tests that protect:

- Spec Context Projects: binding, lease/gate safety, context state integrity, and
  workspace/repo boundary behavior.
- Dadaia Workspace Panel: route/security boundaries, API shape for active tabs,
  workflow-policy mutation guards, and a small number of real browser journeys.
- dadaia-workflows/lifecycle: state transitions, handoff gates, runtime selection,
  prompt/context scoping, and run-store safety.

### FR-5 — Make the pre-push/default test profile sane

The blocking local gate must not include synthetic wall-clock performance tests or the
entire historical suite by default. Performance tests must be explicitly marked and
kept out of default preflight.

## Non-Goals

- Rewriting production feature behavior solely to fit existing tests.
- Removing legitimate security or compatibility contracts.
- Solving every open panel or lifecycle bug unrelated to test architecture.
- Replacing deleted low-value tests with equally low-value renamed tests.

## Acceptance Criteria

1. `quality-assurance.md` describes the actual target test schema, budgets, allowed
   test types, residue exception rule, and validation profiles.
2. `tests/contract/README.md` no longer declares residue grep as the canonical
   delete/orphan contract and no longer requires a per-feature lifecycle-asymmetry map.
3. `tests/contract/test_lifecycle_asymmetry_map.py` is removed.
4. At least the obvious residue-only contract tests are deleted or converted into
   behavior tests with a current boundary.
5. The synthetic performance test is marked so default pytest/preflight can exclude it.
6. Python test collection count is between 1000 and 1500 and recorded in release
   evidence.
7. Focused tests for retained Spec Context Project, Panel, and lifecycle behavior pass.
8. `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs` reports 0 errors.
9. The final test architecture is compactly documented: each retained layer explains
   what behavior it protects and which feature families it evaluates.
