# SPEC — v0.1.51 — E2E Journey Canon

**Status:** Aprovado
**Branch:** `feature/v0.1.51` (base: `c3c90890`, v0.1.50 closure)
**Origin:** operator-approved release sequence R3 (grill 2026-07-02; definition-time
inspection 2026-07-02 resolved all questions from code — no operator items). Dual
definition review 2026-07-02: software-architect REJECT (FR2 flat-tree→doctor-green
unsatisfiable; dropped `init` step) + qa-engineer REJECT (residue disposition
incomplete across 5 `*_residue.py` files; no mutation-sanity discipline) — ALL
amendments folded in below.
**Consumes:** e2e-journey-coverage-and-test-canon

## 1. Problem

The 2026-07-02 test-architecture review found the pyramid healthy (≈25:4:1,
live-harness suites env-gated, no unbounded timing patterns) but with four gaps that
must close BEFORE the R5–R9 refactor chain leans on the suite as its safety net:

1. **No master lifecycle journey.** `context create`/`alive`/`dead` are proven only
   in in-process CliRunner contract tests, while bind/lease/gate E2E exist as
   isolated probes (`tests/e2e/test_two_actor_lease.py` — real-subprocess lease
   scenarios; `tests/e2e/features/test_ctx_inject_bind_boundary.py` — the bind→inject
   cross-sid boundary). NOTHING chains create → alive → real-subprocess bind →
   cross-process ctx-inject injection → lease/gate assertion as ONE narrative
   scenario, so a regression that breaks the *composition* (e.g. bind attribution
   feeding injection feeding the gate) is invisible to every existing test.
2. **The consumer upgrade path has zero E2E.** `dadaia specs upgrade`
   (`features/migrate/upgrade.py`) detects the tree version from `constitution.md`
   frontmatter, plans a registry chain, backs up, applies, and re-stamps. The chain
   is MOVE + CONVERT only (`tree-v2`: `foundation/` + root `SPEC.md` →
   `releases/legacy/`; `bugs-jsonl`: legacy bug markdown → JSONL) — it NEVER
   scaffolds v2 structure, and the required memory atoms are operator-authored by
   design (never auto-created by upgrade, `init`, or `doctor --fix`). The only test
   is a unit assertion on the doctor's staleness WARN
   (`tests/unit/features/migrate/test_specs_evolution.py:193`). No test runs the real
   command on a below-canonical tree and proves the result is doctor-green.
3. **Residue tests contradict the written no-slop law.**
   `specs/memory/quality-assurance.md` §Purpose: *"no test may assert that deleted
   code remains deleted."* The suite has five `*_residue.py` files. Under the
   discriminator this release adopts (§FR3), three are law-violating —
   `tests/contract/test_retired_model_id_residue.py`,
   `tests/contract/test_bash_hook_residue.py`, and
   `tests/contract/test_session_bound_context_residue.py` (added by the definition
   review: its sole subject is greps proving the retired primary-context concept
   stays absent) — and `tests/integration/test_onboarding_tree_v2_e2e.py` embeds a
   legacy-YAML/HTML absence group inside an otherwise-live acceptance test. The code
   and the law contradict each other; the law wins.
4. **Panel E2E asserts rendering and API 200s only.** The 10 Playwright specs cover
   tab rendering, API contracts, a11y, and theme — no spec drives a real context
   OPERATION and observes the panel reflect it across the store→panel boundary.
5. **(LOW) ~294 near-duplicate `assert … == []` occurrences** ("returns empty when
   missing") across `tests/` (244 of them under `tests/unit/`); the top-5 files
   concentrate 87.

## 2. Goals (what done means)

1. One narrative E2E proves the full lifecycle chain end to end with real
   subprocesses and bounded rendezvous (no blind sleeps), reusing the existing
   two-actor/bind-boundary fixture patterns.
2. One sandboxed E2E proves the consumer upgrade path on a **below-canonical but
   structurally-complete** tree: `dadaia specs upgrade` → `dadaia init` → doctor
   reports 0 errors at `CANONICAL_SPECS_VERSION`, plus no-op idempotence at target.
3. The four dispositioned residue surfaces comply with the no-slop law; the remaining
   `*_residue.py` files are recorded compliant under the stated discriminator; every
   live positive contract carried by a deleted file survives in exactly one home.
   No carve-out is claimed, so the quality-assurance atom needs NO amendment.
4. The panel Playwright suite gains one real operation journey on a surface that
   survives R4 (`panel-sessions-cost-dashboard-only`): a store-level context mutation
   observed as a pinned DOM delta.
5. The top-5 duplicate-assertion files are parametrized with zero behavior-coverage
   loss, evidenced by a re-derivable inventory.
6. Every NEW E2E is demonstrated falsifiable (mutation-sanity) — this release is the
   refactor chain's safety net and must be shown able to catch a break.

## 3. Functional requirements

### FR1 — Master lifecycle journey E2E

New `tests/e2e/features/test_lifecycle_journey_e2e.py`, ONE narrative scenario in a
sandboxed workspace (pytest `tmp_path`; no live-workspace state):

- `dadaia context create <name> --repo <slug> --url <local bare fixture repo>` →
  `dadaia context alive <name>` (real clone from the local fixture remote) →
  `dadaia context bind <name> --mode implementation --release <id>` as a REAL
  subprocess (own minted sid; the pattern of `test_ctx_inject_bind_boundary.py`) →
  invoke the `ctx_inject` hook as a second subprocess with a DIFFERENT harness sid
  whose ancestry attributes the bind-epoch marker → assert the injected payload
  carries the bound context's memory marker → drive the SDD gate (`pre_gate`
  subprocess with a MUTATING write payload) → assert the lease record exists, names
  the journey's context, and a foreign-sid MUTATING attempt is blocked (no-steal).
- Rendezvous via the existing `tests/e2e/lease_rendezvous.py` helpers (`wait_for_file`,
  `wait_until`) — bounded deadlines, zero `sleep`-and-hope.
- The journey asserts COMPOSITION, not new mechanics: any step failure is a product
  bug to register via `dadaia bugs append` (test-only release — see Non-goals).

### FR2 — specs-upgrade E2E

New `tests/e2e/features/test_specs_upgrade_e2e.py`, sandboxed. Input: a
**below-canonical, structurally-complete** specs tree — `constitution.md` unstamped
(⇒ version 0) or stamped `< 2`, PLUS all required memory atoms (`architecture.md`,
`tech-stack.md`, `quality-assurance.md`, `product/index.md`), PLUS the mandatory dirs
(`backlog/`, `bugs/`, `releases/` with `README.md` + `.gitkeep`), PLUS legacy
`foundation/` + root `SPEC.md` and one legacy bug markdown (exercising both registry
steps). Rationale (from code, not a bug): upgrade migrates and re-stamps, it never
scaffolds; memory atoms are operator-authored by design.

- Scenario 1: real `dadaia specs upgrade --specs-dir <tree>` → `dadaia init` (the
  backlog-owned step, restored) → assert: backup dir `specs_bkp/<from>→<to>-<UTC>/`
  created; frontmatter re-stamped to `CANONICAL_SPECS_VERSION`; `foundation/` + root
  `SPEC.md` relocated under `releases/legacy/` AND that relocation trips no doctor
  ERROR; legacy bug markdown converted; `dadaia specs doctor` reports 0 errors.
- Scenario 2: rerunning upgrade at target is a no-op (no new backup, exit 0).

### FR3 — Residue-test disposition (law compliance)

**Discriminator (the rule this release applies):** a law-violating residue test's
SOLE subject is the absence of a specifically deleted/retired name; a `*_residue.py`
file that asserts a positive live invariant (a required kwarg threaded at every call
site, a governance contract over public assets) is a compliant guard despite its name.

- DELETE `tests/contract/test_retired_model_id_residue.py` — both tests are
  deleted-stays-deleted; no live positive contract (verified: the registry test
  asserts only a retired id's absence); nothing imports it.
- DELETE `tests/contract/test_bash_hook_residue.py`. It carries TWO live invariants,
  each verified already covered or relocated to exactly one home:
  (a) `pre-push-ci-gate.sh` ships — the ship contract is defined as **the explicit
  presence assertion via a `public/scripts/` directory listing**; its single
  canonical home becomes `tests/contract/test_public_source_hygiene.py`.
  `tests/unit/public/test_pre_push_gate_venv_probe.py` executes the script (implicit
  coverage) but is a behavior test, NOT a ship assertion — it does not count toward
  the exactly-once rule. (b) no committed bytecode under `public/scripts/` — already
  covered more broadly by
  `test_public_source_hygiene.py::test_no_bytecode_committed_under_public`; no move.
- DELETE `tests/contract/test_session_bound_context_residue.py` (definition-review
  extension under the discriminator): its sole subject is that the retired
  primary-context concept stays absent from active surfaces; the classification
  machinery (`ALLOWED_LEGACY_RESIDUE`, `classify_residue_hit`) exists only to serve
  that scan and carries no independent live contract.
- `tests/integration/test_onboarding_tree_v2_e2e.py`: strip ONLY the legacy-YAML/HTML
  absence group (Assertion 5, lines 82–95) from
  `test_ac_o1_copytree_scaffold_produces_valid_v2_tree`. **Assertion 4 (`foundation/`
  + root `SPEC.md` absent) stays, with rationale:** it is the positive v2 tree-shape
  contract backed by live doctor checks (TREE-1/TREE-2), whereas Assertion 5
  references the fully-retired YAML/HTML render pipeline with no doctor backing and
  is redundant with the `.md`-only copytree source.
- Recorded compliant under the discriminator (no action):
  `tests/contract/test_lease_probe_residue.py` (live invariant — every
  `lease.acquire/steal` call site threads `pid_probe=`) and
  `tests/contract/test_plugin_install_residue.py` (positive governance guard over
  public assets tied to the `plugin-scope` rule; guards a never-existed surface, not
  a deleted one).
- No kept law-violating test ⇒ NO quality-assurance atom amendment.

### FR4 — Panel operation journey (Playwright)

New `tests/e2e/panel/spec-context-operation-journey.spec.ts`:

- **Verification-first step (W4 opens with it):** confirm the Spec Context Projects
  tab re-reads `spec_contexts.json` per request (the provider chain suggests
  per-request freshness; if the tab proves startup-cached, register the finding via
  `dadaia bugs append` and fall back to the documented server-restart mechanism —
  the spec then asserts across the restart).
- **Pinned journey:** seed the fixture workspace's `spec_contexts.json` with contexts
  `X` (ALIVE) and `Y` (DEAD) → load the Spec Context Projects tab → assert `X`'s
  card/state badge shows ALIVE → rewrite `spec_contexts.json` flipping `X` to DEAD
  (the exact store the CLI writes) → reload/re-poll → **pinned DOM delta:** `X`'s
  state badge text changes ALIVE→DEAD (content assertion, not just 200).
- Surface choice is the Spec Context Projects tab — independent of the Sessions tab
  that R4 removes; the Sessions specs are NOT touched here.

### FR5 — Store-assertion parametrization (LOW)

- Parametrize the near-duplicate `assert … == []` cases within each of the top-5
  files (`test_public_assets.py` 30, `test_doctor.py` 24, `test_scaffolder.py` 14,
  `test_doctor_taxonomy_disposition.py` 11, `test_session_identity.py` 8) where the
  cases are true shape-duplicates; keep distinct behaviors as distinct tests.
- **Inventory contract:** an explicit per-file list of
  `(callable-under-test, fixture-state)` pairs, recorded on the task line
  before/after; zero loss means the pair-set is preserved (a semantic diff of pairs —
  NOT a node-id diff, which parametrization changes by construction).

## 4. Non-goals

- NO production-code changes. This is a test-only release; any product defect the new
  journeys expose is registered via `dadaia bugs append` (ADDITIVE) and dispositioned
  by a later release — not fixed inline here.
- NO sessions-tab work (R4 owns `panel-sessions-cost-dashboard-only`).
- NO per-harness-profile scaffold E2E (acceptance bar of `harness-isolation-profiles`).
- NO suite-wide `== []` rewrite beyond the top-5 files.
- NO quality-assurance memory amendment (nothing law-violating is kept).
- NO renaming of the compliant `*_residue.py` files (cosmetic; not owned here).

## 5. Acceptance criteria

- **AC-1 (journey):** `pytest tests/e2e/features/test_lifecycle_journey_e2e.py` green;
  the scenario chains create→alive→bind→inject→gate in ONE test path with real
  subprocesses for bind, ctx_inject, and pre_gate; no `time.sleep` calls outside the
  bounded rendezvous helpers; foreign-sid MUTATING attempt observed blocked.
- **AC-2 (upgrade):** `pytest tests/e2e/features/test_specs_upgrade_e2e.py` green:
  below-canonical structurally-complete tree → upgrade → init → backup + re-stamp +
  `releases/legacy/` relocation with no doctor ERROR + doctor 0 errors; at-target
  rerun is a no-op (no new backup).
- **AC-3 (law), per-surface decidable checks:**
  (a) the three deleted files absent:
  `test -e tests/contract/test_retired_model_id_residue.py` etc. all fail;
  (b) onboarding acceptance keeps Assertion 4 + the doctor check and the Assertion-5
  group is gone;
  (c) exactly ONE explicit ship assertion for `pre-push-ci-gate.sh` suite-wide —
  decidable as: the only test asserting its presence via a directory listing lives in
  `test_public_source_hygiene.py`; execution-based tests are excluded by definition;
  (d) `test_lease_probe_residue.py` + `test_plugin_install_residue.py` recorded
  compliant in this SPEC (§FR3) — no disposition entries left open.
- **AC-4 (panel):** the new spec passes in the `e2e-panel` CI job; it asserts the
  pinned ALIVE→DEAD badge delta caused by the store mutation; Sessions specs
  untouched (`git diff --stat` clean for `test_panel_sessions_tab.spec.ts`).
- **AC-5 (parametrization):** in the 5 named files the duplicate pattern is
  parametrized; the before/after `(callable, fixture-state)` pair inventory is on the
  task line and the pair-set is preserved; full suite green.
- **AC-6 (gates):** `ruff format --check`, `ruff check`, `mypy --strict`, full
  `pytest` (unpiped, real exit code) all pass locally and in CI.
- **AC-7 (mutation-sanity):** each NEW E2E (FR1 journey, FR2 upgrade, FR4 panel) was
  demonstrated to FAIL under a deliberate one-line sabotage of the behavior it guards
  (bind attribution / upgrade re-stamp / panel state rendering) during development;
  the sabotage description + observed failure is recorded on the task line; the
  sabotage is reverted before commit. The QA ship gate verifies the evidence exists.

## 6. Risks

- **Journey flakiness (subprocess timing).** Mitigation: bounded rendezvous helpers
  only; deadline failures print the captured stdout/stderr of every actor.
- **`alive` needs a clonable remote.** Mitigation: local bare fixture repo
  (`git init --bare` in `tmp_path`) as the context URL — no network.
- **Projects tab could be startup-cached.** Mitigation: FR4's verification-first
  step; documented fallback (restart-based assertion + bug registration) keeps the
  release test-only.
- **Playwright job is GH-CI-only locally-optional.** Mitigation: AC-4 verified in the
  PR's `e2e-panel` job; the QA verdict for AC-4 is finalized against that run's URL.
- **Parametrization churn hides coverage loss.** Mitigation: AC-5's pair-set
  inventory; QA ship gate re-derives it independently via semantic diff.
