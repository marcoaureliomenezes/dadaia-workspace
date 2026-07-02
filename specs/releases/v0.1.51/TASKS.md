# TASKS — v0.1.51 — E2E Journey Canon

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless write
sets are disjoint (PLAN §Write sets).

## W0 — definition

- [x] T-51-01 ACTIVE → v0.1.51 DEFINITION; SPEC/PLAN/TASKS authored (definition-time
  inspection resolved all grill questions from code); dual definition review:
  software-architect REJECT (BLOCKER: flat-tree→doctor-green unsatisfiable — upgrade
  is move+re-stamp only, atoms never auto-created ⇒ FR2 input redefined as
  below-canonical structurally-complete + `init` step restored; onboarding
  Assertion-4 rationale stated; bash-hook file carries TWO live invariants) +
  qa-engineer REJECT (BLOCKER: residue set is 5 files not 2 ⇒ discriminator stated,
  `test_session_bound_context_residue.py` added to the delete set, compliant files
  recorded; BLOCKER: mutation-sanity AC-7 added; ship-contract exactly-once made
  decidable with single home `test_public_source_hygiene.py`; AC-5 pair-set
  inventory; AC-4 post-push evidence path pinned). ALL amendments landed; all three
  `Aprovado`; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 master journey (write set: `tests/e2e/features/test_lifecycle_journey_e2e.py`, additive helpers in `tests/e2e/lease_rendezvous.py`)

- [x] T-51-10 Narrative lifecycle E2E landed
  (`test_master_lifecycle_journey_create_alive_bind_inject_gate`): create → alive
  (real clone from local bare remote) → fresh-session generic preflight (stamps the
  sentinel; DP-2 honored — a pre-existing marker never binds a fresh session, which
  the first draft got wrong and the run corrected) → bind (real subprocess) →
  ctx_inject (different sid) injects JOURNEY-MARKER via ancestry attribution →
  pre_gate MUTATING allow acquires the lease (record names journey/s-journey-hook) →
  foreign-sid attempt blocked, holder record survives. All actors bounded
  `subprocess.run`; zero sleeps. AC-7 mutation-sanity RECORDED: one-line sabotage
  `session_identity.write_bind_epoch` valid-chain filter → `valid = []` (empty
  marker ⇒ attribution dead) made the journey FAIL at the injection assertion
  (`assert "[journey]" in injected`, exit 1); reverted via git checkout; green again
  (1 passed, exit 0). No product defect found. Owner: software-engineer.

## W2 — FR2 upgrade E2E (write set: `tests/e2e/features/test_specs_upgrade_e2e.py`)

- [x] T-51-11 Upgrade E2E landed (`test_specs_upgrade_e2e.py`, 2 scenarios green):
  below-canonical structurally-complete tree (unstamped constitution ⇒ v0; the four
  memory atoms seeded from the package's OWN canonical scaffold stubs — LINT-1
  requires valid frontmatter, hand-rolled atoms fail the doctor; mandatory dirs;
  legacy `foundation/` + root `SPEC.md`; legacy bug markdown) → real
  `specs upgrade --yes` → `specs init` → `specs doctor` **0 errors**; asserted:
  backup created, re-stamp to `CANONICAL_SPECS_VERSION` (constant lives at
  `core/specs_version`, NOT `features/migrate/upgrade`), `foundation/`+`SPEC.md`
  relocated under `releases/legacy/` (doctor treats it as a WARN-only legacy name,
  no ERROR). Scenario 2: at-target rerun no-op (backup set unchanged). AC-7
  mutation-sanity RECORDED: one-line sabotage of `upgrade.py:85`
  (`write_pattern_version` → `pass`, re-stamp skipped) failed BOTH scenarios
  (exit 1); reverted; 2 passed exit 0. No product defect found.
  Owner: software-engineer.

## W3 — FR3 residue disposition (write set: three deletions + `tests/integration/test_onboarding_tree_v2_e2e.py` + `tests/contract/test_public_source_hygiene.py`)

- [x] T-51-12 DONE. Ship-contract decision RECORDED: the explicit presence assertion
  is kept as the single canonical home —
  `test_public_source_hygiene.py::test_pre_push_ci_gate_script_ships` (directory
  listing); exactly-once verified by grep: only 3 files suite-wide mention the
  script — the hygiene contract (presence) + `test_pre_push_gate_venv_probe.py` +
  `test_push_gate_check.py` (both execute it = behavior tests, excluded by
  definition). Bytecode invariant confirmed already covered by
  `test_no_bytecode_committed_under_public` (no move). DELETED the three
  law-violating files (`test_retired_model_id_residue.py`,
  `test_bash_hook_residue.py`, `test_session_bound_context_residue.py`); stripped
  ONLY Assertion 5 from the onboarding acceptance (Assertion 4 stays with the
  TREE-1/TREE-2 rationale inline). Also aligned `tests/contract/README.md`: its
  "residue grep is the canonical contract form" paragraph endorsed the outlawed
  pattern — rewritten to the discriminator; stale inventory rows removed; hygiene
  row added. Full suite after: **4,407 passed / 17 skipped, exit 0** (unpiped
  pipefail). Owner: software-engineer.

## W4 — FR4 panel journey (write set: `tests/e2e/panel/spec-context-operation-journey.spec.ts`)

- [x] T-51-13 DONE. Verification-first RECORDED: the tab is per-request fresh —
  `render_index._view` calls `list_active_contexts()` per GET, which reads the
  spec-context store per call (no startup cache; no bug to file). Pinned-delta
  ADJUSTMENT (mechanism verification, FR4 clause): `list_active_contexts()` filters
  `state == alive` BY DESIGN, so a DEAD context renders NO card — the delta is card
  PRESENCE→ABSENCE with an unrelated alive card asserted as the liveness control
  (strongest content assertion the surface exposes), not a badge-text change.
  Journey landed (`spec-context-operation-journey.spec.ts`): append ALIVE context
  in the registry → card renders (name + data-slug asserted) → flip to DEAD
  (state + dead_since, the exact `context dead` transition) → reload → card gone,
  control card present. Safety: mutates ONLY a checkout/sandbox registry — skips
  when `REPO_ROOT/.dadaia/states/spec_contexts.json` is absent (local live
  workspace never touched); `PANEL_TEST_REGISTRY` env enables a sandbox run.
  Verified LOCALLY against a scratchpad sandbox workspace (1 passed, 4.0s) — not
  CI-only after all. AC-7 mutation-sanity RECORDED: one-line sabotage of
  `panel/service.py:_active_contexts` (drop the ALIVE filter) failed the spec at
  the disappearance `toHaveCount(0)` assertion; reverted; 1 passed post-revert.
  Sessions specs untouched. Final AC-4 evidence: the PR's `e2e-panel` run.
  Owner: software-engineer.

## W5 — FR5 parametrization (write set: the 5 named unit files)

- [ ] T-51-14 Parametrize true shape-duplicates of the `assert … == []` pattern in
  `test_public_assets.py` (30), `test_doctor.py` (24), `test_scaffolder.py` (14),
  `test_doctor_taxonomy_disposition.py` (11), `test_session_identity.py` (8);
  before/after `(callable-under-test, fixture-state)` pair inventory recorded on
  this line at completion; the pair-set must be preserved (semantic diff, not
  node-id diff). Owner: software-engineer.

## W6 — gates + ship (flat release: single ship gate)

- [ ] T-51-20 QA review (ship gate): verify every AC live — incl. AC-3's per-surface
  decidable checks, AC-5's independent pair-set re-derivation, and AC-7's
  mutation-sanity evidence on T-51-10/11/13; suite run UNPIPED with the real exit
  code recorded. AC-4's evidence is the post-push green `e2e-panel` run URL — the
  AC-4 verdict is finalized against that run, not blocked on a local Playwright run.
  Verdict lands as a review commit. Owner: qa-engineer.
- [ ] T-51-21 Security review (push gate): APPROVE handoff with `metrics.commit_sha`
  = pushed sha; push; CI green (incl. `e2e-panel`); PR; merge.
  Owner: security-reviewer + orchestrator.

## W7 — closure (CLOSURE phase)

- [ ] T-51-30 CLOSURE.md (incl. `## Validations` + `## Drifts` — SPEC-DOC-006);
  consumed entry `e2e-journey-coverage-and-test-canon` removed with durable copy +
  `consumed_backlog.json`; memory: refresh `quality-assurance.md` coverage
  description ONLY if now understated (no law change; closure-phase MEMORY write);
  catalog + lint; archive; ACTIVE → none; candidates.md R3 row marked shipped.
  Owner: product-engineer.
