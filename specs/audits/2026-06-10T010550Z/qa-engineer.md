# Test-Architecture Audit — dadaia-workspace source library

- **Auditor:** qa-engineer (5-agent full-workspace audit; project-auditor synthesizes)
- **Date:** 2026-06-10T010550Z
- **Scope:** `tests/` (250 files, ~48.5k LOC, 2,378 test functions) vs `dadaia_workspace/` (215 files, ~33.7k LOC); all 32 bugs in `specs/bugs/`
- **Mode:** AUDIT ONLY — no fixes, no test edits

---

## Verdict in one paragraph

The operator hypothesis — "lots and lots of tests, but no quality; someone is lying" — is
**half right, and the half that is right is precise**. This suite is NOT classic slop: mock
density is low (most unit files use zero mocks), gate tests invoke the real bash script as a
black-box subprocess, there is a genuine two-OS-process lease denial e2e, and conftest carries
exemplary pollution guards. The craft is good. What is systematically wrong is the **strategy**:
the suite tests a *fictional environment* — one context, one session, env vars hand-planted that
the real harness never provides, fixtures that are always fresh/clean/happy — and it **ratifies
implementation behavior instead of contracts** (the pre-fix install-skip behavior, the diverged
pricing/model tables, the stale bash-script assertion). Of 32 escaped bugs, **16 escaped past
tests that existed and were green** — not because the tests were fake, but because they were
blind along exactly the axes the product lives on: multi-context, multi-session, multi-process,
real harness env, time, deletion, and error paths. The tests are not lying maliciously; they are
*answering a different question* than "does the product work where it runs".

**Test-quality score: 5/10** (rubric at end).

---

## 1. Escape matrix — all 32 bugs

Legend for column (c) "why blind":
- **ENV** = environment never exercised (multi-session / multi-context / missing harness env / nested cwd / Windows)
- **RATIFY** = drift-ratifying / over-fitted: test asserts current implementation, not the contract
- **HAPPY** = happy-path-only; error/edge/delete path absent
- **LABEL** = asserts labels/structure, not observable behavior
- **ISOLATE** = each unit green in isolation; the cross-component seam never composed

| # | Bug | Sev | (a) Should-catch level | (b) Test existed? | (c) Why it didn't fire | Class |
|---|-----|-----|------------------------|-------------------|------------------------|-------|
| 1 | agent-skill-surface-slop | High | contract (ref-integrity lint: agent→skill refs resolve) | No | No ref-integrity check existed; `check_agent_skill_refs` + stage-time gate added only in 0.1.7 rc-4 | **no-test** |
| 2 | backlog-ownership-gate-persona-unreachable-claude-code | High | e2e (harness-level: hook process env) | Yes (`tests/integration/gate/test_backlog_ownership.py`) | Tests *setenv* persona vars into the subprocess env — simulating a channel the real harness provably never provides. Green tests validated an unreachable mechanism | **blind/ENV** |
| 3 | ci-preflight-raw-traceback-when-poetry-absent | Low | unit (missing-binary error path) | No | Only happy path (poetry present) covered; `test_subprocess_runner_missing_binary_returns_127` added with the fix | **no-test** (HAPPY) |
| 4 | codex-agent-orchestration-mismatch | Critical | contract (capability claims vs behavior: `supports_parallel=True` while sequential file-writer) | No | No test asserts advertised capabilities match dispatcher behavior; docs honesty unchecked | **no-test** |
| 5 | codex-dispatched-agent-persona-not-propagated-to-sdd-gate | Critical | harness e2e (real Codex/Claude hook process) | Yes (same gate suite as #2) | Same as #2 — pytest cannot spawn the harness; the *design assumption* (env propagates) was never validated anywhere. No harness-e2e tier exists | **blind/ENV** (borderline untestable at current tiers) |
| 6 | codex-workflow-dispatch-not-deterministically-enforced | High | — (LLM lead-agent discipline) | n/a | Non-deterministic agent behavior; the deterministic parts (preflight injection) got tests only with the fix (T-017-20) | **untestable-by-design** (deterministic residue: no-test) |
| 7 | configure-hook-writes-malformed-duplicate-userpromptsubmit | High | integration (run BOTH writers → validate settings.json against Claude hook schema) | Yes (each writer tested separately) | Two code paths each unit-tested against its *own* output schema; never composed in one workspace; no external-schema validation | **blind/ISOLATE** |
| 8 | constitution-persona-single-source-drift | High | contract (single-source lint across constitution/personas/skills) | No | No doc-consistency check; `check_memory_phase_single_source` (SINGLE-SRC-1) added in rc-4 | **no-test** |
| 9 | context-bind-forces-mode-choice-on-operator | Med | contract (CLI ergonomics vs workspace-protocol contract "bind never required") | Yes (CLI tests pass `--mode`) | CLI tests supply the flag and thereby ratify it as required; nothing asserts the documented "bind is optional convenience" contract | **blind/RATIFY** |
| 10 | doctor-blind-to-projected-drift | High | integration (edit source → stage → DON'T install → doctor must fail) | No | Doctor tests asserted only the checks doctor *had* (source↔staging); the missing comparison had no failing test. `test_doctor_projected_drift.py` exists now — added with the fix | **no-test** (RATIFY flavor) |
| 11 | gate-cross-context-lock-contamination | CRITICAL | integration (gate subprocess with TWO ALIVE contexts, write to repo B while repo A lease live) | Yes (full gate suite) | Every gate test built a **single-context** workspace (`_build_workspace(context_name="dadaia-workspace")`, `test_path_scope.py:34-62`). First-ALIVE fallback == correct answer in every fixture, so mis-resolution was invisible. Regression `test_no_cross_context_lease_contamination` added post-fix (rc-4) | **blind/ENV** |
| 12 | gate-fpath-not-canonicalized-before-classifier | Med | integration (symlink from UNGATED dir into gated subtree) | No | No symlink/traversal fixture in any gate test; still Open | **no-test** |
| 13 | init-ignores-workspace-flag | Med | integration (`init --workspace X` with cwd *inside an existing workspace*) | Yes (`tests/unit/core/test_workspace_resolver.py`) | Resolver tests ran from clean tmp cwds; the failing precondition — cwd nested under a sentinel ancestor — was never constructed | **blind/ENV** |
| 14 | install-does-not-prune-orphan-projections | High | integration (stage A → install → delete A from source → stage → install → A must be gone) | No | Only add/overwrite lifecycle tested; the **delete** path had zero coverage until `test_copy_agents_for_opencode_prunes_orphan` (rc-4) | **no-test** (lifecycle asymmetry) |
| 15 | install-skips-existing-files | High | integration (modify source → stage → plain install → projection must update) | Yes | Tests ratified skip-on-exists as the contract — the very file is named `test_install_skip_idempotent.py` (the *optimization* is the test's hero); "modified source must propagate" was asserted nowhere | **blind/RATIFY** |
| 16 | lease-cross-context-false-positive-block | Med | integration (same as #11; superseded by it) | Yes | Same single-context fixture monoculture as #11 | **blind/ENV** |
| 17 | lease-stolen-by-additive-write-from-live-session | CRITICAL (Open) | unit+integration+e2e (three defects) | Yes — and blind three different ways | **D1:** `gate_policy.classify_path` ADDITIVE tests use only workspace-root paths (`tests/unit/features/spec_context/test_lease_property.py:74`, `test_lease_activity_exemption.py:27` — `"specs/backlog/x.md"`); `repos/<slug>/specs/bugs/**` never classified → over-fitted to the implementation's own blind spot. **D2:** no test where the holder is *busy but writeless* past TTL while a second actor writes (time + concurrency never composed; `test_short_heartbeat_triad` uses FakeClock single-actor). **D3:** heartbeat tests *setenv* `DADAIA_SESSION_ID` (`tests/unit/gate/test_post_gate_heartbeat.py:79`) — an env var hook subprocesses never receive in any harness, so tests certify a heartbeat that no-ops in production | **blind/RATIFY+ENV** |
| 18 | model-catalog-modelmap-pricing-drift-no-registry | Med (Open) | contract (MODEL_MAP keys ⨝ PRICING_TABLE keys consistent) | Yes — each table separately | Textbook drift-ratification pair: `test_model_mapping.py:25` pins `claude-haiku-4-5-20251001`, `test_pricing.py:47,212` pins `claude-haiku-3-5`. Both green, mutually contradictory, no cross-table assertion exists | **blind/RATIFY+ISOLATE** |
| 19 | opencode-parity-test-asserts-stale-bash-script-ref | Med (Open) | — (the bug IS a test) | Yes — it is the defect | `tests/e2e/features/test_opencode_parity_hardening.py` asserts `"sdd-spec-gate.sh" in text` — encodes the pre-0.1.8 implementation, contradicts the approved SPEC. Over-fitted assertion + planning gap (no task owned updating it) | **blind/RATIFY** (meta) |
| 20 | panel-e2e-shallow-coverage-no-deploy-gate | High | — (meta-defect about the e2e tier itself) | Yes | Three stacked blind spots, per the bug: label-deep chip assertions (`spec-context-tab.spec.ts:29-37`), no global 4xx/5xx guard beyond initial load, CI workspace seeded with **no spec context** so no data-dependent path ever ran | **blind/LABEL+ENV** |
| 21 | panel-handler-parallel-auth-registries | High | unit (every `_RAW_ROUTES` entry must have an explicit auth class) | No | No route-enumeration test; `test_handler_route_classification.py` exists now — added with the fix | **no-test** |
| 22 | panel-memory-doc-links-broken-html | Critical (shipped to PyPI) | e2e (click chip → iframe content 200) + integration (URL builder) | Yes (panel e2e suite, green in CI) | Chips asserted by **text label**, never clicked; iframe 404 invisible to `page.goto` assertions; CI fixture had zero memory atoms. The `.html`→`.md` migration changed the data layer and no test consumed real data | **blind/LABEL+ENV** |
| 23 | panel-subprocess-in-features-layer | High | contract (architecture lint: no subprocess outside `infrastructure/`) | No | The layer rule existed only as prose; import-linter contract arrived in v0.1.9 | **no-test** |
| 24 | panel-theme-switcher-broken-ugly | High | e2e (click → option visible → dataset changes → persists) + visual | Partially (`theme-switcher.spec.ts` existed, reported "thorough") | Functional depth arrived only post-bug (current spec does click+dataset+persistence, E2E-THM-01..09); originally asserted control structure. "Very ugly" half is genuinely untestable by assertion (visual quality → design review) | **blind/LABEL** (visual half: untestable) |
| 25 | panel-token-file-chmod-toctou | Med | unit (token file must be created 0o600-at-open / O_EXCL, not write-then-chmod) | No | `test_auth.py` checked final state (perms after both calls = happy path); the window between calls had no assertion | **no-test** (HAPPY) |
| 26 | panel-wikilink-slug-hardcoded | High | unit (renderer with a NON-default slug) + integration (two contexts) | Yes (renderer tests) | Single-context fixture monoculture again: every fixture slug was `dadaia-workspace`, so the hardcoded literal equaled the expected value. A one-line parametrize over a second slug would have caught it | **blind/ENV+RATIFY** |
| 27 | pre-push-gate-cannot-locate-workspace-venv | Med (Open) | integration (run `pre-push-ci-gate.sh` as subprocess in workspace-layout fixture: venv at `<ws>/.dadaia/.venv`, repo at `<ws>/repos/<slug>`) | No | The pre-push hook script has no subprocess test at all; runner detection never exercised against the canonical self-hosting layout | **no-test** |
| 28 | repeated-visible-userpromptsubmit-memory-injection | Critical | integration (run `ctx-inject.sh` twice WITHOUT any session-id env — the Codex reality) | Yes (`tests/integration/test_hooks.py` runs the script as subprocess — good mechanics) | Tests provided session-id vars the Codex harness doesn't set; the PID-fallback branch (sentinel changes every prompt) was the production path and the untested path. Regression `test_ctx_inject_injects_once_then_silent_same_session` added post-fix | **blind/ENV** |
| 29 | semaphore-no-liveness-reclaim | Med | unit/integration (dead-PID holder must be reclaimable before TTL) | No | Staleness tested as TTL-age only — mirror of `_is_stale()`'s own definition (test restates implementation); liveness dimension absent | **no-test** (RATIFY flavor) |
| 30 | session-bind-primary-residue | Critical | contract (residue grep: retired `primary_context`/`is_primary` model absent from source+assets) | No | No residue/consistency contract until `tests/contract/test_session_bound_context_residue.py` (added with fix) | **no-test** |
| 31 | specs-doctor-dual-error-counter-confusing-output | Low | integration (CLI output contract: last line never contradicts exit code) | No | Output asserted piecemeal per subsystem; no whole-output coherence assertion | **no-test** |
| 32 | specs-upgrade-fails-on-preexisting-doctor-error | Med | integration (upgrade a tree that ALREADY has an unrelated doctor error → must succeed) | Yes (upgrade tests on clean fixtures) | Happy-path fixture monoculture: every upgrade test started from a compliant tree; "dirty but valid input" never constructed | **blind/HAPPY** |

### Escape-matrix totals

| Class | Count | Bugs |
|-------|-------|------|
| **no-test** (surface had zero coverage) | **14** | 1, 3, 4, 8, 10, 12, 14, 21, 23, 25, 27, 29, 30, 31 |
| **test-existed-but-blind** (green test on the surface) | **16** | 2, 7, 9, 11, 13, 15, 16, 17, 18, 19, 20, 22, 24, 26, 28, 32 |
| **untestable-by-design** (at any automatable tier) | **2** | 5 (harness env propagation — needs a harness-e2e tier that doesn't exist), 6 (LLM lead discipline) |

Blind-mode breakdown of the 16: **ENV** (multi-context / multi-session / missing harness env /
nested cwd / unseeded fixtures) ×9 · **RATIFY/over-fitted** ×7 · **LABEL** ×3 · **ISOLATE** ×2 ·
**HAPPY** ×2 (several bugs carry two modes).

The most damning pattern: **at least 9 of the fixes shipped WITH the regression test that
would have caught the bug** (10, 11, 14, 15, 21, 22, 24, 28, 30 — e.g. `test_doctor_projected_drift.py`,
`test_no_cross_context_lease_contamination`, `test_handler_route_classification.py`,
E2E-SCP-03..06, `test_ctx_inject_injects_once_then_silent_same_session`). Every one of those
tests was *writable before the bug* with the same tooling. The suite grows by post-mortem, not
by adversarial design.

---

## 2. Pyramid & strategy assessment

**Shape (files):** unit 166 · integration 49 · contract 18 · e2e 12 (+11 Playwright `.spec.ts`).
~2,378 Python test functions. Ratio ≈ 70/20/8/2 — textbook pyramid *shape*; the count
(2,378 for 33.7k src LOC) is on the high side but not padded: `test_public_assets.py`
(2,658 LOC, 206 tests) is fine-grained coverage of pure render/escape functions, not copy-paste.

**What is genuinely good (credit where due):**
- Gate integration tests are **real black-box subprocess invocations** of `sdd-spec-gate.sh`
  with controlled stdin/env and exit-code assertions (`tests/integration/gate/test_path_scope.py:64-90`).
- `tests/integration/test_hooks.py` runs `ctx-inject.sh` via `subprocess.run(["bash", ...])`.
- `tests/e2e/test_two_process_denial.py` spawns **two real OS processes** with a file-based
  rendezvous against the lease — this is the right idea, executed once.
- `tests/conftest.py` root-write backstop + session pollution guard; `addopts = "-p no:cacheprovider"`;
  hypothesis DB redirected. Hygiene engineering is above average.
- Windows/macOS contract tests exist post-0.1.8 (`test_platform_classifier.py`,
  `test_file_permission_windows.py`, CRLF contract in `test_install_skip_idempotent.py`).

**Where the e2e tier is shallow (generalizing panel-e2e-shallow-coverage):**
- **Panel:** fixed for the named regressions (response-guard.spec.ts, deep THM/SCP tests), but the
  CI fixture seeding problem was the structural lesson and it generalizes: any tier whose fixture
  has no real data tests only the empty-state render.
- **`tests/e2e/features/*`** are mostly CLI-pipeline tests in tmp workspaces — legitimate, but
  they exercise the *Python API/CLI*, not the harness. There is **no harness-e2e tier at all**:
  nothing ever runs a hook the way Claude/Codex runs it (hook process env, stdin JSON envelope
  from the real harness, PreToolUse→PostToolUse sequencing across one session). Bugs 2, 5, 17-D3,
  28 all live exactly in that gap.
- **Concurrency:** exactly one real-two-process test exists (lease denial). Everything else —
  heartbeat starvation (17-D2), takeover during long ops, cross-context lease ping-pong (11) —
  is simulated with state files + FakeClock, single actor. FakeClock triad is well built but
  it can only verify the state machine the implementer *imagined*, never the interleaving the
  OS produces. The two CRITICALs of this cycle are both interleaving bugs.
- **Pre-push hook:** zero subprocess coverage (bug 27).

**Hooks tested as real subprocess?** Bash hooks: yes (gate + ctx-inject). Python hooks
(`hooks/sdd_gate.py` family, the 0.1.8 replacements): **only as imported functions with
monkeypatched env** (`tests/unit/hooks/*`) — the new hook layer regressed to in-process testing,
and that is exactly where the open CRITICAL (17) lives.

---

## 3. Slop scan

**Estimated slop: ~8%** — low for classic slop, and that is the point: the problem is
blindness, not padding.

- **Tautological asserts:** 0 hits for `assert True`; very few vacuous tests found in sampling.
- **Mock-the-world:** absent. Mock density is exceptionally low — the top mock-using unit file
  has 5 references (`tests/unit/infrastructure/test_signal_shutdown.py`); the majority of unit
  files use **zero** mocks and operate on `tmp_path` + real objects. 65 `assert_called*`
  occurrences across 166 unit files is restrained.
- **Drift-ratifying tests (the real slop of this suite), named examples:**
  - `tests/unit/features/telemetry/test_pricing.py:47,212` vs
    `tests/unit/infrastructure/runtime_transforms/test_model_mapping.py:25` — two green tests
    pinning two contradictory haiku ids (bug 18, Open).
  - `tests/e2e/features/test_opencode_parity_hardening.py` — `assert "sdd-spec-gate.sh" in text`
    pins the retired implementation against the approved SPEC (bug 19, Open).
  - `tests/unit/features/spec_context/test_lease_property.py:74` + `test_lease_activity_exemption.py:27`
    — ADDITIVE classification asserted only on workspace-root paths, restating
    `_ADDITIVE_PREFIXES`'s own bug (bug 17-D1, Open CRITICAL).
  - Pre-fix `test_install_skip_idempotent` lineage — the skip *optimization* asserted as the
    contract while the propagation contract was unasserted (bug 15).
  - `tests/unit/gate/test_post_gate_heartbeat.py:79` — heartbeat verified under
    `DADAIA_SESSION_ID` injected by the test; production hook processes never have it (17-D3).
- **Copy-paste batteries:** mild. Large files (`test_public_assets.py` 206 tests,
  `test_doctor.py` 1,359 LOC) are granular but each case differs; parametrize is underused
  (only ~7 unit files) so some batteries could compress 3-5×, but they do test distinct lines.
- **Label-deep e2e remnants:** the panel suite's pre-fix pattern (assert chip text, never click)
  — largely remediated, but `servers-tab.spec.ts` (1 test) and `api-contracts.spec.ts` (3 tests)
  remain thin relative to surface.

---

## 4. Hygiene

- `tests/__pycache__/` in working tree: **gitignored** (`git check-ignore` confirms), inherent
  to running CPython; NOT in the repo-cleanliness forbidden list (`.pytest_cache`, `.mypy_cache`,
  etc. — none present). **Compliant.**
- `tests/tmp/`: contains only a `README.md` declaring rules (excluded from collection, never
  coverage, delete-or-promote before closure). Currently empty of tests. **Compliant by design**;
  note the "every test here must be deleted or promoted before release closure" rule has no
  doctor/CI enforcement — convention only.
- `pyproject.toml:83` `addopts = "-ra -p no:cacheprovider"`; mypy `incremental = false`;
  hypothesis DB disabled + home-dir redirected at conftest import time. **Compliant.**
- conftest root-write backstop (function-scoped, autouse) + session-level pollution guard
  failing the run on `.dadaia/.venv/.pytest_cache/...` at repo root. **Exemplary.**
- `tests/e2e/node_modules/` lives in-tree (Playwright + axe-core). Not on the forbidden list,
  but it is a tool-artifact directory inside the repo working tree; flag for project-auditor as
  a gray-zone against the spirit of the repo-cleanliness law.

---

## 5. Top 5 systemic test-architecture defects (ranked)

1. **Single-context / single-session fixture monoculture.** No pre-bug test ever constructed
   two ALIVE contexts, two concurrent sessions, or a non-default context slug. Both CRITICALs of
   this cycle (gate-cross-context-lock-contamination; lease-stolen D1) plus bugs 16, 26 are
   direct products. When every fixture's answer equals the buggy fallback's answer, the fallback
   is unfalsifiable.
2. **Simulated harness environment — tests certify channels production doesn't have.** Hook and
   heartbeat tests `setenv` `DADAIA_SESSION_ID` / persona vars that no harness delivers to hook
   subprocesses (bugs 2, 5, 17-D3, 28). The suite validated persona gating and heartbeats that
   were *physically dead* in every real runtime. This is the precise sense in which the tests
   "lie": green on a world that doesn't exist.
3. **Drift-ratifying assertions instead of contracts.** Tests pin current implementation output
   (install skip, haiku pricing vs mapping pair, stale `sdd-spec-gate.sh` assertion, TTL-only
   staleness mirroring `_is_stale()`). When the implementation is wrong, the test enshrines the
   wrong; when the spec moves, the test blocks the spec (bug 19).
4. **No cross-component consistency tier.** Two writers of `.claude/settings.json` never
   composed (7); MODEL_MAP↔PRICING_TABLE never cross-asserted (18); route table↔auth registries
   never enumerated (21); staging↔projected never compared (10); constitution↔persona facts
   never linted (8, 30). Each unit green in isolation, every seam dark. 6+ bugs.
5. **Lifecycle asymmetry: create/modify tested, delete/error/time untested.** Orphan prune (14),
   dead-PID reclaim (29), missing binary (3), pre-existing-error input (32), TOCTOU window (25),
   heartbeat starvation under a long-running operation (17-D2). The suite tests the system being
   built up, never being torn down, starved, or fed dirty input.

---

## 6. What a non-lying test strategy for THIS product must contain

The product's core surfaces — gate, lease, hooks, projection — are **multi-process,
multi-session, multi-context, multi-OS by nature**. A strategy that matches:

1. **A harness-fidelity e2e tier (new).** Run every hook exactly as the harness does: spawn the
   hook entry point as a subprocess with the *documented harness env contract* — and maintain
   that contract as an explicit fixture (`claude_hook_env()`, `codex_hook_env()`) containing
   ONLY what each harness actually provides (verified once against real harness traces, then
   pinned). Any test that needs an env var outside that fixture fails review. This single rule
   would have killed bugs 2, 5, 17-D3, 28.
2. **Two-actor concurrency tests as a standing pattern, not a one-off.** Generalize
   `test_two_process_denial.py`: real OS processes + file rendezvous for (a) holder-busy-past-TTL
   while second actor writes ADDITIVE (17-D2/D1), (b) two contexts mutating disjoint repos
   simultaneously (11), (c) takeover/ping-pong sequences. Property: "a live holder never loses
   the lease; an additive write never appears in the lock record" asserted on the *lock file
   history*, not the return value.
3. **Fixture matrix instead of fixture monoculture.** Every gate/lease/panel/renderer test
   parametrized over: {1 context, 2 contexts} × {default slug, non-default slug} × {seeded
   memory/data, empty}. Cheap (the builders exist), kills the unfalsifiable-fallback class
   (11, 16, 22, 26).
4. **Consistency contracts as a first-class tier.** Cross-table key equality (MODEL_MAP vs
   PRICING_TABLE), route↔auth enumeration, staging↔projected hash, settings.json validated
   against the external harness schema after running ALL writers, residue greps for retired
   models, agent→skill ref integrity. Most already exist *post-bug* — the policy change is:
   any pair of modules sharing an identifier set gets a consistency contract **at introduction
   time**, enforced by review checklist.
5. **Adversarial lifecycle coverage required per feature:** for every create/modify test, the
   PR must show the delete/orphan test, the dirty-input test, and the missing-dependency test,
   or justify their absence in the test plan. (Bugs 3, 14, 25, 29, 32.)
6. **Contract tests own the SPEC, not the code.** When a SPEC/ADR retires a behavior (bash→python
   hooks), the task list MUST include flipping the pinned assertions (bug 19's planning gap).
   Mechanical aid: tag implementation-pinning assertions with the ADR they encode, grep at
   release definition.
7. **Deploy/e2e gates with teeth (keep what panel learned):** global zero-4xx/5xx + console-error
   guard during full interaction tours; CI workspaces seeded with real data; the e2e job gating
   publish. Extend the same pattern to `dadaia panel`'s sibling: a *workspace-lifecycle* smoke
   (init → bind → write under gate → push gate) run as real subprocesses on all 3 OSes.
8. **Multi-OS already started (0.1.8) — finish it for hooks:** the Python hook layer must run
   its subprocess tests in the Windows/macOS CI legs, not only importability.

---

## 7. Test-quality score: 5/10

Rubric (each 0-2):

| Axis | Score | Justification |
|------|-------|---------------|
| Mechanical craft (no tautology/mock-abuse, hygiene, determinism) | **2/2** | Low mock density, real tmp_path fixtures, subprocess black-box gate tests, exemplary conftest guards |
| Contract fidelity (tests assert the spec, not the implementation) | **0.5/2** | 7 drift-ratifying escapes incl. two still-Open; contradictory pinned tables; stale-SPEC assertion |
| Environment fidelity (tests run where the product runs) | **0.5/2** | Simulated harness env, single-context monoculture, one real concurrency test, no harness tier; both CRITICALs escaped here |
| Adversarial coverage (error/delete/dirty/time paths) | **1/2** | Happy-path monoculture pre-0.1.7; improving (rc-4 regression tests are adversarial) but reactive |
| Escape record (does the suite catch bugs before operators do?) | **1/2** | 32 escapes, 16 past green tests; but ~9 fixes shipped with the right regression test, and post-bug guards (E2E-GUARD, two-process e2e) show the team can write the right tests — after being hurt |

**Net: 5/10.** A well-built suite that interrogates a simpler product than the one that ships.
The volume is honest; the *environment* is fictional. The fastest quality lever is not more
tests — it is the harness-env fixture contract (defect 2) and the fixture matrix (defect 1),
which together cover 11 of the 16 blind escapes.

---

*Audit artifacts: this file. No production, test, or spec files were modified. Evidence gathered
read-only via grep/ls/head over `tests/` and `specs/bugs/`; no test runs were required.*
