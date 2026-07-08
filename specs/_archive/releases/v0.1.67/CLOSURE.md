# Closure: Release — v0.1.67 — Test-Infra Executed-Path Integrity

> **Status:** Aprovado
> **Release ID:** v0.1.67
> **Owner:** product-engineer
> **Closed:** 2026-07-08
> **Branch:** `feature/v0.1.67` · **Merged:** `08703384` (PR #128, squash, all CI green incl. post-merge `main`) · **Closure branch:** `chore/v0.1.67-closure`
> **Ship gates:** software-architect definition-review **REVISE** (F1..F7, folded same session into SPEC/PLAN/TASKS before implementation) · qa-engineer **APPROVED** (full suite 4978 passed/0 failed across 3 independent runs; FR1/FR2/FR3 each independently re-verified RED→GREEN; reintroducing the old broken pattern trips the FR3 guard; guard proven non-interfering across all 4 live flags against real binaries; exemption scoped to exactly 2 mechanism-proof tests; no-workaround audit clean) · security-reviewer **APPROVED** (push-gate keyed to `18a4d459`, 0 findings; FR1 confirmed pure indirection, guard test-only) · CI **all checks green**.
> **Mandate:** bug-driven release (no backlog consumption) — 2 open bugs, ONE shared root cause, both next-pick debt carried over from v0.1.66. Operator hard mandate: RED-first reproduction + root-cause fix only, no workarounds — see SPEC.md "Reproduction & TDD mandate".

## Summary

v0.1.67 fixes the shared root cause behind the two open test-infrastructure bugs
discovered mid-v0.1.66: `PiHeadlessAdapter.__init__` and `CodexExecAdapter.__init__`
bound their subprocess runner (`runner: Runner = subprocess.run`) as a keyword default
evaluated once at class-definition time, so a later `monkeypatch.setattr` on the module
attribute never reached an already-constructed adapter — the real local `pi`/`codex`
binary ran end-to-end inside a test that believed itself hermetic. A pre-existing
truthy-only assertion on the block reason masked this for years: the real binary's own
unrelated auth-failure text happened to satisfy `assert payload["blocked"]["reason"]`.

Three functional requirements closed the defect class rather than patching one symptom.
FR1 restructured both adapters to resolve their subprocess runner via a live, call-time
indirection (`runner: Runner | None = None` + a `_resolve_runner()` lookup performed on
every `.run()` call) — behaviorally identical in production, since the same
`subprocess.run` function is ultimately invoked when no `runner=` is injected; only the
WHEN of the lookup changes. FR2 rewrote the false-positive test and its two sibling
broken-pattern sites onto the already-established constructor-injection pattern, with a
call-recorder (`calls` list, `len(calls) == 1`) plus a structural-field assertion as the
genuine fake-derivation proof — never a bare truthy check. FR3 added a suite-wide
`autouse` guard in `tests/conftest.py` that fails loud with `RuntimeError` if either
adapter would reach the real, un-faked `subprocess.run` during a test that has not
explicitly opted into one of the four established live-test flags
(`DADAIA_E2E_REAL_WORKER`, `DADAIA_PI_LIVE`, `DADAIA_CODEX_LIVE`, `DADAIA_CLAUDE_LIVE`) —
a durable, suite-wide protection so this defect class cannot silently recur, proven
non-interfering against all four flags with real binaries.

A software-architect definition-review round (verdict REVISE, 7 findings F1..F7) folded
into SPEC/PLAN/TASKS before any implementation began: it corrected the FR3 guard's
opt-in surface from one flag to the real four-flag union, widened FR2's scope to cover a
previously-unacknowledged sibling broken-pattern site with an explicit documented-debt
decision on a third site, replaced an unsatisfiable fake-content assertion example with
the call-recorder idiom, corrected an import-linter contract count (8→9), and pinned
`xfail(strict=True)` as the only sanctioned way to demonstrate the guard's RED state in
CI. One instance of the old `__kwdefaults__`-setitem idiom
(`test_lifecycle_pipeline_v0166_repro.py`) was deliberately left unmigrated — explicit,
documented debt, not silent debt — because it is not itself a false positive and
survives FR1 unmodified.

## Tasks completed

All implementation landed on `feature/v0.1.67` and merged as squash `08703384`
(PR #128). Per-task RED-first evidence and root-cause description are in TASKS.md
completion notes.

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-67-01 | RED — pi call-time-interception proof (FAILING on current code) | `08703384` |
| T-67-02 | GREEN — pi mechanism fix (FR1, live runner indirection) | `08703384` |
| T-67-03 | RED — codex call-time-interception proof (FAILING on current code) | `08703384` |
| T-67-04 | GREEN — codex mechanism fix (FR1, mirrored) | `08703384` |
| T-67-05 | Rewrite the pre-existing false-positive pi executed-path test (FR2, call-recorder + structural-field idiom) | `08703384` |
| T-67-06 | Migrate the entry-pin echo test to the same pattern (FR2, hardening) | `08703384` |
| T-67-07 | Migrate the `test_lifecycle_cli.py` sibling broken-pattern site (FR2, F2 new) | `08703384` |
| T-67-08 | Add the autouse real-binary guard (4-flag union) + permanent guard-proof tests, xfail-first (FR3) | `08703384` |
| T-67-09 | Per-flag guard non-interference proofs (FR3, F1 new) | `08703384` |
| T-67-10 | qa-engineer — full non-live suite + import-linter (9 kept, 0 broken) | (verification only, no source write) |
| T-67-11 | qa-engineer — live-suite non-interference matrix + regression re-run + mutation-sanity | (verification only, no source write) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff
path).

| Description | Command | Evidence |
|-------------|---------|----------|
| Full suite green, 3 independent runs | `pytest -p no:cacheprovider -q` (unpiped, real exit) | **4978 passed, 0 failed**, reproduced across 3 separate runs — T-67-10/T-67-11 |
| Format clean | `ruff format --check .` | clean — T-67-10 |
| Lint clean | `ruff check --no-cache .` | all checks passed — T-67-10 |
| Types clean | `mypy --strict dadaia_workspace/` | 0 issues — T-67-10 |
| Import contracts (F4-corrected expectation) | `lint-imports --config setup.cfg --no-cache` | **9 kept, 0 broken** — T-67-10 |
| AC1(repro) — pi call-time interception (FR1) | `test_pi_runtime.py::test_default_runner_resolves_subprocess_run_at_call_time_not_construction_time` | RED (real `subprocess.run` already bound) → GREEN (fake reached) independently re-verified — T-67-01/02, T-67-11 |
| AC1(repro) — codex call-time interception (FR1) | mirrored in `test_codex_exec_runtime.py` | RED → GREEN independently re-verified — T-67-03/04, T-67-11 |
| AC1.3 — explicit `runner=fake_runner` injection unaffected | full `test_pi_runtime.py` + `test_codex_exec_runtime.py` suites | 100% green, 0 modifications to the ~30 pre-existing unit tests — T-67-02/04 |
| AC2.1/AC2.2 — false-positive test rewritten, fake-derivation proven | `test_pipeline_runs_first_step_on_pi_harness_end_to_end` | constructor injection + `calls` call-recorder (`len(calls) == 1`) + structural-field assertions (`runtime`, `accepted`, verified fixed `blocked.reason` constant) — GREEN — T-67-05 |
| AC2.3 — entry-pin echo test migrated | `test_pipeline_auto_defaults_pi_from_entry_pin_with_loud_echo` | constructor injection + `calls` recorder added; all pre-existing assertions unchanged and green — T-67-06 |
| AC2.4 — `test_lifecycle_cli.py` sibling site migrated | `_inject_pi_stream` / `test_implement_auto_defaults_pi_from_entry_pin_with_loud_echo` | constructor injection + `calls` recorder; existing `payload["runtime"] == "pi_headless"` assertion preserved and green — T-67-07 |
| AC2.5 — `test_lifecycle_pipeline_v0166_repro.py` explicitly NOT migrated, confirmed non-regressed | full file re-run | all 5 `_patch_pi_runner`-based tests 100% green after FR1 shipped — T-67-11 |
| AC3.1/AC3.2 — guard fires on un-opted-in real-binary invocation | dedicated permanent guard-proof tests (pi + codex), xfail-first then `pytest.raises(RuntimeError)` | xfail honored pre-guard; `RuntimeError` raised deterministically post-guard — T-67-08 |
| AC3.3 — per-flag guard non-interference matrix (F1-corrected) | `DADAIA_E2E_REAL_WORKER=1`, `DADAIA_PI_LIVE=1`, `DADAIA_CODEX_LIVE=1`, `DADAIA_CLAUDE_LIVE=1`, each run independently against real binaries; each `*_live/` dir also run flag-unset | guard never fires under any of the 4 flags (including the `DADAIA_CODEX_LIVE` check F1 required as its own named proof, not inferred); pre-existing `skipif` skip-reason text unchanged when flags are unset — T-67-09/T-67-11 |
| AC3.4 — existing explicit-injection unit tests unaffected by the guard | full `test_pi_runtime.py` + `test_codex_exec_runtime.py` | 0 regressions — T-67-08 |
| AC-MUT (FR1) — mutation-sanity: revert to class-def-time default | local uncommitted revert → re-run AC1(repro) | AC1(repro) tests FAIL as expected; reverted before continuing — T-67-11 |
| AC-MUT (FR2) — mutation-sanity: old monkeypatch mechanism reintroduced | local uncommitted revert (remove constructor injection + `calls`) | the `calls`-based assertion fails (empty list) as expected; truthy-only reversion alone does not fail (expected — weaker assertion, not a mutation-sanity failure); reverted before continuing — T-67-11 |
| AC-MUT (FR3) — mutation-sanity: guard fixture's `monkeypatch.setattr` commented out | local uncommitted edit → re-run guard-proof tests | both guard-proof tests FAIL as expected (no `RuntimeError` raised); reverted before continuing — T-67-11 |
| No-workaround audit | full `git diff` against the forbidden-shape list (try/except swallow, config band-aid, PATH shim, alias file, wrapper script) | zero violations — T-67-10/11 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — full suite 4978/0, all AC RED→GREEN, guard-matrix + reinforcing-guard evidence, no-workaround audit clean |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — sha `18a4d459`, 0 findings; FR1 confirmed pure indirection, guard confirmed test-only |
| CI (PR #128) | GitHub Actions | all checks green on `08703384` incl. post-merge `main` |

### Reproduction & no-workaround compliance

Per the operator's hard mandate (SPEC.md "Reproduction & TDD mandate"): FR1 was proven
RED-first at the unit level for both adapters (T-67-01/03 confirmed FAILING on current
code before T-67-02/04 implemented the fix and re-confirmed GREEN). FR2's rewrite
replaced the unsatisfiable original assertion example with the call-recorder +
structural-field idiom per the architect's F3 finding, and its fake-derivation proof
(the `calls` list) is what the mutation-sanity pass in T-67-11 exercises directly — the
`calls`-based assertion fails exactly when the fake is not what drove the outcome, which
is the correctness property FR2 exists to guarantee. FR3's two guard-proof tests were
authored FIRST as `xfail(strict=True)` (never a live, un-wrapped real-binary spawn in
CI, per the architect's F6 finding) and only flipped to a deterministic
`pytest.raises(RuntimeError)` assertion after the guard fixture existed. QA (T-67-10/11)
independently re-verified every AC RED→GREEN, ran the full per-flag guard
non-interference matrix against real binaries, re-ran all three mutation-sanity passes
(FR1/FR2/FR3), and audited the full diff against the forbidden-shape list — zero
violations. This was the operator's explicit hard mandate, not a discretionary practice,
and is recorded here as closure evidence per that mandate.

## Drifts

### architect-definition-review-revise-f1-f7 (folded before implementation)

**Description:** the software-architect definition-review (2026-07-08) returned verdict
REVISE with 7 findings against the original SPEC/PLAN/TASKS draft: F1 (HIGH) — the FR3
guard's opt-in surface was incorrectly claimed to be a single flag
(`DADAIA_E2E_REAL_WORKER`) when the real `*_live/` suites gate on four distinct flags,
which would have broken legitimate `DADAIA_CODEX_LIVE=1` runs; F2 (HIGH) — FR2's scope
missed a second broken-pattern site (`test_lifecycle_cli.py`'s `_inject_pi_stream`) and
left a third site (`test_lifecycle_pipeline_v0166_repro.py`) unaddressed with no
explicit decision; F3 (MEDIUM) — the original FR2 assertion example anchored on
`blocked.reason` containing fake-unique text, which is unsatisfiable because that field
is a fixed constant for the target test's shape; F4 (MEDIUM) — the import-linter
contract count was stated as 8 when `setup.cfg` defines 9; F6 (LOW) — the SPEC did not
explicitly forbid a live, un-wrapped real-binary spawn in CI to prove the FR3 guard's RED
state; F7 (LOW) — the FR2 mutation-sanity check was sequenced before F3's correction
existed, which would have proven nothing.

**Resolution:** all 7 findings were folded into SPEC.md/PLAN.md/TASKS.md in the same
review session, before any implementation task started. F1 widened the guard mechanism
to a single named union predicate over all four flags with explicit per-flag AC3.3
sub-checks (including a dedicated `DADAIA_CODEX_LIVE` check, never inferred from another
flag's run). F2 added T-67-07 (the `test_lifecycle_cli.py` migration) and an explicit,
justified, documented-debt decision for `test_lifecycle_pipeline_v0166_repro.py`'s
`__kwdefaults__`-setitem idiom (recorded in SPEC "Out of scope", not silently dropped).
F3 replaced the unsatisfiable assertion example with the call-recorder +
structural-field idiom already correct elsewhere in the suite. F4 corrected "8 kept" to
"9 kept, 0 broken" throughout SPEC/PLAN/TASKS. F6 pinned `xfail(strict=True)` as the
only sanctioned way to demonstrate AC3(repro)'s RED state. F7 re-sequenced AC-MUT for
FR2 to depend on F3's correction landing first. No SPEC finding required operator
escalation — all were resolved by direct source verification against the files the
architect cited.

**Memory updates:** none from this drift specifically — the fold changed only spec text
before implementation; the shipped mechanism (4-flag guard union, call-recorder idiom)
is what `quality-assurance.md` documents below.

### documented-debt-v0166-repro-kwdefaults-idiom-not-migrated

**Description:** `tests/integration/cli/test_lifecycle_pipeline_v0166_repro.py`'s
`_patch_pi_runner` helper (5 call sites) patches
`PiHeadlessAdapter.__init__.__kwdefaults__["runner"]` directly — a second, competing
idiom for the same subprocess-runner seam FR1 restructures. SPEC FR2's F2 correction
made an explicit, justified decision to NOT migrate this file in this release: it is not
itself a false positive (every assertion in it is already exact-content, never
truthy-only), and it survives FR1 unmodified (`__kwdefaults__["runner"]` remains a valid
key regardless of whether its bound default value is `subprocess.run` or `None`).

**Resolution:** left as-is, by design. T-67-11 re-ran this file's full suite explicitly
as a regression check post-FR1 — all 5 tests remain 100% green. The suite now carries
two idioms for this one seam (constructor-injection and `__kwdefaults__` setitem)
instead of one; this is accepted stylistic debt, not correctness-bearing debt, and is
recorded as a candidate for a future convergence release.

**Memory updates:** none — this is test-infra-internal debt, not product behavior; no
`specs/memory/**` atom describes this level of test-double wiring detail.

### spec-doc-nit-flagged-by-qa

**Description:** QA's ship-gate review flagged a minor documentation nit in SPEC.md: a
passage referred to "5 tests" being migrated/added where the actual count across
FR2/FR3's scope was 4 (T-67-05, T-67-06, T-67-07 test migrations plus the guard-proof
test pair counted differently depending on how the passage enumerated them). This did
not affect any acceptance criterion, task, or shipped behavior.

**Resolution:** noted as a documentation nit only; no SPEC/PLAN/TASKS edit was required
to ship (all ACs, tasks, and evidence are keyed by name/id, not by the passage's summary
count). Recorded here for the archive record rather than silently dropped.

**Memory updates:** none.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. This is a **test-infra-only** release — no product behavior, CLI surface,
or memory-documented adapter capability changed (FR1's runner-resolution mechanism is
behaviorally identical to the prior default from the caller's perspective; SPEC.md
"Memory files affected at closure" stated this explicitly upfront). One atom carries a
durable rule addition from what this release proved.

- `specs/memory/quality-assurance.md` — **primary, edited.** Extended the v0.1.66
  "Executed-path law extension" passage with the durable rule this release's fix
  established: a subprocess-runner keyword default bound at class-definition time is not
  merely a gotcha to route around per-test (as v0.1.66 did) but has a concrete, shipped
  fix — adapters resolve the runner via a live, call-time indirection instead; the
  protection against recurrence is a suite-wide autouse guard (4-flag opt-in union +
  per-test exemption for exactly the mechanism-proof tests), and the correct
  fake-derivation idiom is a call-recorder plus a structural field the fake's own
  behaviour drives, never a loose truthy assertion or an unsatisfiable fixed-constant
  claim. Refreshed the live-scale bracket: suite collects 4978 passed + 0 failed as of
  v0.1.67 (up from 4970 passed/18 skipped at v0.1.66). Updated `last_updated` and
  `release_origin` frontmatter. `tldr` unchanged (the five-layer/CI-shape summary still
  holds; the new rule is a Purpose-section addition, not a `tldr`-level change) — no
  catalog regen required for this atom.
- `specs/memory/product/harness/harness-pi.md` — **no change: assessed.** Read in full.
  Documents production adapter behavior (model set, result classification, telemetry) at
  the level an operator or implementer needs; the call-time-vs-construction-time
  subprocess-runner resolution mechanism is an internal implementation detail with zero
  observable behavior delta (same `subprocess.run` ultimately invoked when no `runner=`
  is passed) and is not the kind of fact this atom's sections (Purpose/Usage
  flow/Differentiator/Runtime state) exist to carry. No edit made.
- `specs/memory/product/harness/harness-codex.md` — **no change: assessed.** Same
  reasoning as `harness-pi.md` — read in full, confirmed the mirrored FR1 fix has no
  documented-behavior surface here either.
- `specs/memory/architecture.md` — **no change: assessed.** No new cross-layer import
  edge (import-linter confirmed 9 kept / 0 broken, unchanged contract count); every
  touched module (`pi_runtime.py`, `codex_runtime.py`, `tests/conftest.py`, test files)
  stayed within its existing layer. No structural design change to record.
- `specs/memory/tech-stack.md` — **no change: assessed.** No new dependency, no
  language/runtime version change, no new env var (FR3's guard reuses the four
  already-documented live-test opt-in flag names verbatim — no new flag introduced).
- `specs/memory/product/catalog.json` — **no regen required.** No atom's `tldr` changed
  (only `quality-assurance.md`'s body and frontmatter dates were edited).
- `specs/memory/AGENTS.md` — **not touched.** The tri-copy contract does not require an
  update for this release (no new memory-write mechanic, no new agent-facing memory
  policy introduced).

## Dispositions

Disposition sweep per the ADR-11 vocabulary. This is a **bug-driven** release — no
backlog item was picked or superseded, so there is no consumed-backlog ledger. Both
target bugs already carry `resolved --release v0.1.67` terminal events (appended
2026-07-08T21:32Z), confirmed present in `specs/bugs/20260708T21Z-00.jsonl`.

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `pi-executed-path-cli-tests-invoke-real-pi-binary` (`specs/bugs/20260708T15Z-00.jsonl`, terminal event in `specs/bugs/20260708T21Z-00.jsonl`) | bug MEDIUM | `resolved --release v0.1.67` | FR1, T-67-02/04, AC1(repro) |
| `pi-e2e-test-false-positive-loose-blocked-reason-assertion` (`specs/bugs/20260708T15Z-00.jsonl`, terminal event in `specs/bugs/20260708T21Z-00.jsonl`) | bug HIGH | `resolved --release v0.1.67` | FR1 (load-bearing) + FR2, T-67-05/06/07, AC2(repro) |

Bug ledger: 0 open after this release (both remaining next-pick items from v0.1.66 are
closed here; no new bug discovered mid-release).

No consumed-backlog ledger — this release consumed no backlog item. Live backlog items
(`panel-tab-reorg-agentic-layers`, `dispatch-band-legacy-fallback-removal`,
`platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`) are untouched
by this release, per SPEC.md "Out of scope".

## Backlog returns

None filed by this closure. The `test_lifecycle_pipeline_v0166_repro.py` idiom
convergence (documented debt above) is a future-release candidate but is not filed as a
formal backlog entry by this closure — it is tracked via this CLOSURE.md's Drifts
section and may be picked up opportunistically alongside other test-infra work.

## Deviations

**None.** This release touched no plugin-domain surface and required no uninstalled
plugin pack.

## Archive decision

**MOVE** — `specs/releases/v0.1.67/` moves to `specs/_archive/releases/v0.1.67/` via
`git mv` (PM/operator; PE issues no git mutations and runs no shell). PM then executes,
in order:

1. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0). No
   `dadaia memory catalog generate` is required — no atom `tldr` changed.
2. the release-dir `git mv specs/releases/v0.1.67 specs/_archive/releases/v0.1.67`.
3. advance `ACTIVE.md` → `release: none`, `phase: none`, noting the bug ledger is now 0
   open, and the unchanged live backlog carried forward from v0.1.66
   (`panel-tab-reorg-agentic-layers`, `dispatch-band-legacy-fallback-removal`,
   `platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`), plus the
   operator-pending optional PyPI deploy (v0.1.61–67 unpublished).

**Order law honored:** the memory edit landed in this CLOSURE phase, BEFORE `ACTIVE.md`
leaves CLOSURE.
