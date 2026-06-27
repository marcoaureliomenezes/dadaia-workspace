# Closure: Release — v0.1.29 — Harness as a governed dimension + catalog completion

> **Status:** Aprovado
> **Release ID:** v0.1.29
> **Owner:** product-engineer
> **Closed:** 2026-06-27

## Summary

v0.1.29 makes the **worker harness a first-class governed dimension** of the
dadaia-workflows model-governance layer. Before this release v0.1.28 governed *which model*
a step runs but never *which harness* runs it: every governed step defaulted to codex, the
resolver rejected any profile whose harness differed from the catalog default, and the
pipeline CLI swapped the execution adapter *after* resolution — so `--harness pi` ran the
PI adapter while the persisted snapshot still recorded `codex` with a codex model id. The
net effect was that PI-as-Layer-2-worker, the whole capability the model layer was built to
govern, could not be selected through governance at all.

After this release an operator can select PI as a governed worker through three paths that
all flow through the one shared `WorkflowExecutionPolicyResolver`: a CLI flag
(`--harness pi` / `--step-harness <step>=pi`), a persisted overlay (`default_harness: pi`
or a per-step `harnesses` entry), and the panel codex/pi toggle. The effective harness per
step resolves with a total five-rung precedence
(`CLI --step-harness > CLI --harness > overlay step harness > overlay default_harness >
catalog step default`); the profile is validated against the **effective** harness, not the
catalog default; and when a harness is overridden with no explicit profile the resolver
auto-selects that harness's default profile for the step's purpose (producing step → the
harness's standard profile, review/gate step → its deep/reasoning profile). The executed
adapter and the recorded snapshot are now a **single source of truth**:
`apply_resolved_policy` is the sole author of each `PipelineStep.runtime_kind`, derived from
the resolved harness — fixing the v0.1.28 codex-recorded-while-pi-ran divergence — while
`--harness fake` still preserves the FAKE dry-run adapter.

The release also **completes the governed catalog to all 7 workflows**: `closure` is added
as its real single `close` worker step (resolvable, plus the Python `closure_removal_gate`
modeled as a gate), and `audit` / `research` / `bug_report` are enumerated honestly as
`deferred` with zero governed steps — no invented model-step ladders, no second drifting
source. The doctor (`WMP-*`) and the overlay schema both learn the harness dimension, with
the Layer-2 = codex|pi law enforced at write time and at resolve time. This release resolves
the explicit v0.1.28 residual and the v0.1.28 code-reviewer MEDIUM in one pass.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-29-A-01 | Per-harness default profiles on the resolver `CatalogStep` (`default_profiles`) | `feature/v0.1.29` |
| T-29-A-02 | Resolver: effective-harness precedence (`_resolve_harness`, 5-rung chain) | `feature/v0.1.29` |
| T-29-A-03 | Resolver: auto-profile-on-harness-override + validate against effective harness (fixes `:288`) | `feature/v0.1.29` |
| T-29-A-04 | Overlay store: optional `default_harness`/`harnesses` + `step_harness`/`workflow_default_harness` accessors + round-trip | `feature/v0.1.29` |
| T-29-A-05 | Overlay schema: optional `default_harness`/`harnesses` enum codex|pi, `additionalProperties:false` kept | `feature/v0.1.29` |
| T-29-A-06 | `pipeline.apply_resolved_policy` sets `runtime_kind` from the resolved harness (FAKE preserved) | `feature/v0.1.29` |
| T-29-A-07 | CLI `pipeline` verb threads `--harness`/`--step-harness` into `resolve`; removes the post-resolve swap | `feature/v0.1.29` |
| T-29-A-08 | Wave A green checkpoint | `feature/v0.1.29` |
| T-29-B-01 | Catalog: `closure` added as its real single `close` worker step + `closure_removal_gate` | `feature/v0.1.29` |
| T-29-B-02 | Catalog: `audit`/`research`/`bug_report` confirmed enumerated as deferred, zero governed steps | `feature/v0.1.29` |
| T-29-B-03 | CLI `policy show` + container reach the completed catalog | `feature/v0.1.29` |
| T-29-B-04 | Wave B green checkpoint | `feature/v0.1.29` |
| T-29-C-01 | Panel view: harness flag in catalog diff + harness-only overlay accepted | `feature/v0.1.29` |
| T-29-C-02 | Panel JS: codex/pi toggle persists harness into the PUT body | `feature/v0.1.29` |
| T-29-C-03 | E2E: CLI `--harness pi` proof via `FakeAgentRuntime` | `feature/v0.1.29` |
| T-29-C-04 | E2E: overlay `default_harness: pi` proof (no CLI flag) | `feature/v0.1.29` |
| T-29-C-05 | Wave C green checkpoint | `feature/v0.1.29` |
| T-29-D-01 | Doctor: validate the harness dimension (overlay harness mismatch / Layer-2 residue) | `feature/v0.1.29` |
| T-29-D-02 | Projection + full-suite final checkpoint | `feature/v0.1.29` |
| T-29-D-03 | Re-assert carried-forward laws (§3.7) | `feature/v0.1.29` |

> Per-task commit SHAs are on branch `feature/v0.1.29` (diff base `bd710c57`). The review
> trio below is keyed to the rc-ship HEAD `feature/v0.1.29 @6e211e0b`; the coordinator
> records the exact final pushed SHA at ship time per the release-governance rc cadence.
> Security review runs after this CLOSURE, on the final HEAD.

## Validations

Each validation is a triple: description, command, evidence.

| Description | Command | Evidence |
|-------------|---------|----------|
| Ruff format clean | `ruff format --check` | `pass` (qa-impl handoff `metrics.ruff_format`) |
| Ruff lint clean | `ruff check --no-cache` | `pass` (qa-impl `metrics.ruff_check`) |
| Mypy strict clean | `mypy --strict` | `pass` (qa-impl `metrics.mypy_strict`) |
| Full functional suite green | `pytest -p no:cacheprovider` | `3764 passed, 13 skipped, 1 deselected, 0 failed` (qa-impl `metrics.full_suite_passed=3764`, `full_suite_failed=0`; the 1 deselected is the load-sensitive perf test — see Drifts) |
| Targeted governance suites | `pytest tests/.../policy_resolver tests/.../pipeline_harness_governance_e2e ...` | `153 passed` (qa-impl `metrics.targeted_tests_passed=153`; code-reviewer ran 76 targeted, all pass) |
| CLI PI-proof (D-5 CLI path) | `dadaia lifecycle pipeline --release-id v0.1.29 --harness pi --show-policy` | resolves `implement: pi-implementation-standard / pi / gpt-5.3-codex`, `review_qa\|review_security\|review_code: pi-reasoning-high / pi / gpt-5.5`; 8/8 live CLI PI proofs pass (qa-impl `metrics.cli_pi_proofs_passed=8`) |
| Default-first (no flags) | `dadaia lifecycle pipeline --release-id v0.1.29 --show-policy` | all steps resolve harness=codex (AC-10 back-compat; qa-impl INFO finding) |
| `--harness pi` + codex `--step-model` rejected | `dadaia lifecycle pipeline ... --harness pi --step-model implement=codex-implementation-standard` | exit 2, actionable message ("override profile ... runs on harness codex, but step ... resolves to harness pi") (qa-impl INFO finding) |
| Overlay-default_harness=pi drives execution (D-5 overlay path) | `pytest ...::test_overlay_default_harness_pi_resolves_pi_end_to_end` + `::test_panel_put_default_harness_pi_overlay_drives_execution` | PASS — `received_models[i].harness == "pi"`, `.model` ∈ {gpt-5.3-codex, gpt-5.5}, persisted snapshot records `harness=pi` per step; panel-PUT path goes through real PUT → atomic write → fresh resolver reading the persisted overlay (no CLI flag) (qa-impl INFO finding) |
| Single-source runtime_kind + FAKE preserved (AC-3) | `pytest ...::test_apply_resolved_policy_sets_runtime_kind_from_resolved_harness` + `::test_apply_resolved_policy_preserves_fake_for_dry_run` | PASS — `apply_resolved_policy` sets runtime_kind (codex→CODEX_EXEC, pi→PI_HEADLESS) and keeps FAKE when the base step was FAKE (qa-impl INFO finding) |
| `workflow doctor` exit 0 over completed catalog | `dadaia lifecycle workflow doctor` | exit 0, `[ok] workflow-model-policy (no governance issues)` (qa-impl `metrics.workflow_doctor=exit-0`) |
| Public projection clean (schema projected) | `dadaia public doctor` | exit 0 with `[ok] public-privacy` and `[ok] workflow-policy`; the `default_harness`/`harnesses` schema fields staged + installed to all targets (qa-impl `metrics.public_doctor=exit-0`) |
| Panel harness-toggle E2E (Playwright) | `npm run test:e2e -- workflow-policy-harness-toggle` | **spec written, not run locally** — `tests/e2e/panel/workflow-policy-harness-toggle.spec.ts` is well-formed with real round-trip assertions (toggle→PUT→GET round-trips harness; `/api/workflow-catalog` reflects harness=pi + `harness_overridden` + pi effective_profile). NOT executed: no `package.json`/`playwright.config.ts` in the source working tree (repo-hygiene forbids it at root) and host load was 16.9/8-cores at review. Server-side contract independently proven by passing Python tests (`test_put_harness_only_overlay_round_trips_and_flags_catalog`, `test_catalog_row_flags_harness_override_from_overlay`, `test_panel_put_default_harness_pi_overlay_drives_execution`). **GH `e2e-panel` job is authoritative for the JS-UI layer.** |
| QA rc-ship verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T204500Z-qa-engineer-v0129-impl-review.handoff.json` (AC-1..AC-11 all verified; 0 HIGH/CRITICAL; 8 INFO) |
| Code-review rc-ship verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T000000Z-code-reviewer-v0129.handoff.json` (0 CRITICAL/HIGH/MEDIUM; 2 LOW, 1 INFO; 76/76 targeted tests) |
| Architect DEFINITION sanity verdict | (review) | **APPROVED** — `.dadaia/handoff/dadaia-workspace/2026-06-26T000000Z-software-architect-v0129-spec-sanity.handoff.json` (both gates pass; 1 MEDIUM `fake`-dry-run-must-be-explicit-AC → addressed: AC-3 / qa proof; 2 LOW) |

### Acceptance criteria → result

All AC-1..AC-11 (SPEC §"Acceptance criteria") have concrete, falsifiable backing per the
qa-impl handoff. Highlights: AC-1 precedence table (5-rung chain, per-step mixing); AC-2
auto-profile (PI default auto-selected, `:288` mismatch removed); AC-3 single-source
runtime_kind + FAKE preserved; AC-4/AC-5 PI proof via CLI flag and via persisted overlay
(both assert `harness=pi`, PI model, and snapshot record); AC-6 panel PUT→GET→catalog
harness round-trip (server-side proven; JS layer via the GH `e2e-panel` job); AC-7 all 7
workflows enumerated, `closure` resolvable via its real `close` step, deferred trio honest;
AC-8 doctor 0-ERROR over the good catalog + actionable findings on broken overlays;
AC-9 no Layer-2 `claude`/`opencode` residue accepted anywhere; AC-10 default-first
byte-identical + a v0.1.28 overlay loads unchanged; AC-11 full suite + projection green.

## Drifts

Implementation followed PLAN.md and SPEC.md across all four waves; no plan was bent. The
architect's one DEFINITION-time MEDIUM (the `--harness fake` dry-run must NOT be swallowed
by "runtime_kind from resolved harness") was addressed in the implementation exactly as
recommended — `apply_resolved_policy` preserves FAKE so runtime_kind keeps a single author,
proven by `test_apply_resolved_policy_preserves_fake_for_dry_run` — and is therefore not a
post-hoc drift. The items below are recorded to make the residual surface explicit.

### load-sensitive-perf-test-deselected-from-full-suite

**Description:** `tests/performance/test_lifecycle_hygiene_scan.py` (437k synthetic files,
90s wall-clock bound) was deselected from the rc-ship full-suite run. It is the subject of
bug `prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound` (MEDIUM, Open). It is
a wall-clock-bound assertion that fails only under concurrent machine load (host was at load
16.9 on 8 cores at review time); run standalone under low load it **passed in 68s**.
v0.1.29 touches **no** hygiene/anti-slop code, so this is a pre-existing environment
artifact, not a v0.1.29 regression.

**Resolution:** Not a ship-blocker for v0.1.29 code. Tracked by the existing filed bug; the
pre-push gate clears when machine load drops. Re-run the perf test standalone (or in CI on a
quiet runner) before final ship.

**Memory updates:** none — hygiene behavior is unchanged; current memory truth (the
performance guard over the synthetic baseline) already describes it correctly.

### code-reviewer-low-nits-deferred-as-minor-follow-ups

**Description:** the v0.1.29 code-reviewer raised 3 non-blocking maintainability findings
(2 LOW, 1 INFO): (1) the panel `_semantic_check` covers harness-only overlays today only via
a parse implementation-detail (empty-steps side effect) rather than mirroring the doctor's
explicit 3-map union (`contexts | default_harness_overlay | step_harness_overlay`); (2)
`_DEFAULT_PROFILE_BY_HARNESS_PURPOSE` is duplicated verbatim in `policy_resolver.py` and
`dadaia_catalog.py` (identical now; could drift — the resolver-local copy serves only the
Wave-A demo `library_workflow_catalog`); (3) the `policy_resolver.py` module docstring
describes the resolver source as `library_workflow_catalog`/`model_profiles` whereas the
**production** resolver is fed `governed_workflow_catalog()` via the container.

**Resolution:** All three are defensive/clarity nits with no behavior change today (the
empty-steps coverage is verified empirically; the duplicated map is data guarded by import-
time `_assert_catalog_defaults_resolve`; the docstring is factually scoped, just narrow).
Noted here as minor follow-ups for a future hygiene pass — not picked into v0.1.29.

**Memory updates:** none — current product truth is unaffected.

### v0.1.28-d-2-deferrals-still-deferred

**Description:** the two v0.1.28 D-2 scope deferrals remain deferred after v0.1.29:
**operator-added PI profiles** (`.dadaia/states/workflow_model_profiles.local.json`, not
loaded/validated — built-in recommended profiles only) and **per-context overlays +
`extends` inheritance** (only the `default` context is honored; a non-`default` key is
inert). v0.1.29 governs *which built-in profile / which harness* a step selects; it does not
add new profiles or per-context breadth.

**Resolution:** Intentional scope boundaries (SPEC §4 "Out of scope"), not deviations. The
built-in profiles cover every governed step's default for both supported harnesses, so the
release is fully runnable. Deferred to a future release; see the follow-up flagged for PM
below (the v0.1.28 CLOSURE already recorded a candidate covering these — v0.1.29 confirms
the snapshot-vs-adapter divergence sub-item of that candidate is now **resolved** by D-2,
while the operator-profiles + per-context-overlay sub-items remain open).

**Memory updates:** memory describes current truth (built-in profiles only, `default`-context
overlay only); no changelog of the deferral is written into memory.

## Memory updates

Memory files written during this CLOSURE phase to reflect current product truth (harness as
a governed dimension as it now is — no changelog):

- `specs/memory/product/sdd/lifecycle-foundation.md` — updated the **workflow model
  governance** section to current truth: harness is now a first-class governed dimension
  (the effective-harness precedence chain, auto-profile-on-harness-override, profile
  validated against the *effective* harness), `apply_resolved_policy` as the single author
  of `runtime_kind` from the resolved harness (FAKE preserved for dry-run), the overlay's
  optional `default_harness`/`harnesses` fields, and the completed governed catalog (all 7
  workflows: 3 fully runnable + `closure` resolvable via its real `close` step + 3 deferred
  zero-step). Replaced the v0.1.28 "Known limit" note (the harness/runtime_kind divergence
  it described is now fixed). Bumped `last_updated` + `release_origin` to v0.1.29.
- `specs/memory/product/panel/panel.md` — updated the **Workflows control plane** section:
  the codex/pi segmented toggle now persists a real harness change through
  `PUT /api/workflow-model-policy`; the catalog diff carries the per-row `harness_overridden`
  flag + `default_harness`; the resolver honors the persisted harness. Bumped `last_updated`.
- `specs/memory/architecture.md` — updated the **Workflow control plane subsystem** section:
  the resolver now resolves an effective harness per step (precedence) and validates the
  profile against it; the overlay store/schema carry optional `default_harness`/`harnesses`
  (Layer-2 enum codex|pi, `additionalProperties:false` kept); `apply_resolved_policy` is the
  single `runtime_kind` author; the governed catalog is complete to 7 workflows; the doctor
  validates the harness dimension (overlay harness mismatch / Layer-2 residue). Bumped
  `last_updated` + `release_origin` to v0.1.29.
- `specs/memory/tech-stack.md` — no change: this release added no dependency and changed no
  approved technology. The harness governance is stdlib-only Python over the existing seams.
- `specs/memory/product/index.md` + `catalog.json` — no catalog change: harness governance
  is captured by updating the existing `lifecycle-foundation`, `panel`, and `architecture`
  atoms (a governance dimension over the lifecycle engine, not a new standalone feature). No
  feature atom added or removed; daily-relevance order unchanged.

## Dispositions

Disposition-sweep ledger. v0.1.29 declares `**Consumes:** none` — the model-governance
backlog epic was consumed by v0.1.28. No backlog item and no bug were picked into v0.1.29.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| (none) | — | — | `**Consumes:** none` in SPEC §header; no bug/backlog picked |

> No disposition flips are required: this release consumes no backlog item and fixes no
> registered bug (it resolves the v0.1.28 *residual* + code-reviewer MEDIUM, both tracked in
> the v0.1.28 CLOSURE, not as standalone `specs/bugs/` files). The load-sensitive perf-test
> bug `prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound` remains `Open` — it
> is not a v0.1.29 defect and is not closed by this release.

## Backlog returns

No new backlog items are produced by v0.1.29 implementation. One follow-up is flagged for
`project-manager` to curate (per the `backlog-ownership` rule, PE does not author backlog):

- **Update the existing v0.1.28 candidate
  `workflow-model-governance-operator-profiles-and-context-overlays`** to record that its
  third sub-item (reconcile snapshot `harness`/`runtime_kind` under a `--harness` override
  so run-history inspection distinguishes the governed harness from the adapter that ran) is
  now **DELIVERED by v0.1.29 (D-2)**; the remaining two sub-items — (1) operator-added PI
  profiles via `.dadaia/states/workflow_model_profiles.local.json`; (2) per-context overlays
  + `extends` inheritance honoring non-`default` context keys — **stay open**. Optionally add
  the 3 v0.1.29 code-reviewer LOW/INFO nits (panel `_semantic_check` 3-map union;
  de-duplicate `_DEFAULT_PROFILE_BY_HARNESS_PURPOSE`; resolver docstring clarification) as a
  small hygiene follow-up, and confirm the perf-gate bug
  `prepush-gate-blocked-by-loadsensitive-perf-test-wallclock-bound` is tracked.

> These are backlog mutations; the coordinator (`project-manager`) curates the actual
> `candidates.md` entry. This CLOSURE records the required follow-up; PM files it.

## Archive decision

**MOVE** — the release directory will be moved to `specs/_archive/releases/v0.1.29/` via
`git mv` (run by the coordinator; product-engineer has no Bash). `specs/releases/ACTIVE.md`
is then updated to `release: none` with a pointer to the archived release. The coordinator
also performs the commit + push and runs the post-CLOSURE security review on the final HEAD.
