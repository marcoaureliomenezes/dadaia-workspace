# TASKS — v0.1.64 — Platform Ergonomics & Tiering

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Waves sequential; inside W3, ai-engineer (bodies) precedes
software-engineer (parser) — no parallel `[-]` anywhere (shared surfaces: golden test files W1↔W3; agent bodies ↔
reader). Every implementation task: **NO `specs/backlog/**` paths staged** (dispositioned at CLOSURE — T-64-50).
Every move/repoint grep includes `tests/` AND non-import textual references (docstrings/comments). AC-9
mutation-sanity: each new test class is sabotaged → shown to FAIL → reverted, captured on its task line.
**W1 lands FIRST** (SPEC §7 ordering law — W3's regens ride the W1 layer).

## W0 — definition

- [x] T-64-01 SPEC/PLAN/TASKS authored from the 2026-07-07 **code read** (not dossier restatements): 5 helper-copy
  sites + fragile cross-test import; 12 `--harness "fake"` sites; NO PI-native session env var
  (`session_env.py` carries only CLAUDE/CODEX ids; `pi_runtime.py` reads none); rename blast radius pinned
  (reader/AgentDTO/api_agents/12 bodies/6 test files) with the **stale dossier claim corrected** (Codex projection
  derives effort from registry Tier via `model:`, never reads numeric `tier:`); fast-tier premise **stale** vs the
  pinned 2026-07-06 retier map. Inspection-first grill: findings F-1..F-4 + ADR-1..5 (SPEC §9, operator-overridable);
  §8 operator-checkpoint protocol recorded; FR6 REJECT recommendation surfaced in the definition handoff
  `decisions_required`. **Marker normalized to `[x]` (QA64-3 — the definition set IS authored, matching the
  siblings).** <!-- AMEND:QA64-3 --> **Review fold (2026-07-07, APPROVE-with-amendments):** QA64-1..3 +
  ARCH64-2 + ARCHX/QAX folded; PM Rulings 64-A/64-B in SPEC §0 (this release lands + closes LAST; W3 rebases
  the 12 bodies and re-verifies its `^tier:` grep + v0.1.62's AC-6 grep; shared-atom merge order). `Aprovado`
  after re-verify; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1/FR2 shared golden platform-invariance module (golden-first: ZERO regen)

- [x] T-64-10 NEW `tests/helpers/` package + `golden_platform.py` + unit fixtures. Owner: software-engineer.
  Write set: NEW `tests/helpers/__init__.py`, NEW `tests/helpers/golden_platform.py`,
  NEW `tests/unit/helpers/test_golden_platform.py` (+ `tests/unit/helpers/__init__.py`).
  Checklist:
  - FR1 surface: `norm_path_line`, `norm_panel_body`, `canon_env_line`, `sort_line_lists`, `is_env_doctor_line`,
    `assert_golden(path, obj, what, *, update_env="UPDATE_INSTALL_GOLDENS")`, `norm_stderr`. Pure functions,
    stdlib-only. Leak-class taxonomy docstring (host-state / iteration-order / OS-phrase / path-version / clock /
    Rich-width) citing the v0.1.58 three-round commits (`60f42904`, `c02e74f6`, `1dadfafe`).
  - AC-2 unit fixtures: denylist-marker variant → bare marker; D-CX-9 Linux (`exited 127`) AND Windows
    (`[WinError 193]`) phrasings → one canonical line; unsorted list → sorted multiset (count-preserving);
    Rich box-wrapped stderr → collapsed; JSON-escaped ws path + ISO timestamp → `<WS>`/`<TS>`.
  - Preconditions: none. Done: module + unit tests green; `lint-imports --no-cache` 8/0 ignore-cap unchanged.
  - AC-9 sabotage (a) drop the sort in `sort_line_lists` ⇒ multiset unit test FAILS → revert; (b) make
    `canon_env_line` identity ⇒ D-CX-9 unit test FAILS → revert. Capture both on this line.
  - Fate ledger — NEW files only; **pin the branch-point `pytest --collect-only -q` count here (QA64-2/QAX-4 —
    first implementation wave; re-validated at closure).** <!-- AMEND:QA64-2 --> Commit `test(T-64-10): ...`.
  - **EVIDENCE (2026-07-07, software-engineer):** branch-point collect pin (HEAD `8020d117`) =
    **4795 tests collected**. Fate ledger (NEW only): `tests/helpers/__init__.py`,
    `tests/helpers/golden_platform.py` (7-function FR1 surface + 6-class leak taxonomy docstring citing
    `60f42904`/`c02e74f6`/`1dadfafe`; superset params: `assert_golden(..., update_env=None, message=...)` for the
    e2e no-regen/bespoke-message variants, `norm_stderr(..., wide_glyphs=True)` for the policy-CLI `_norm`
    variant), `tests/unit/helpers/__init__.py`, `tests/unit/helpers/test_golden_platform.py` (20 tests: denylist
    marker, D-CX-9 Linux `exited 127` + Windows `[WinError 193]` → one canonical line, sorted multiset
    count-preserving, Rich box-wrap collapse both variants, JSON-escaped `<WS>` + `<TS>`, regen-flag mechanics).
    AC-9 sabotage (a) drop sort ⇒ `test_sort_line_lists_locks_a_sorted_multiset` + 3 more FAILED (4F/16P) →
    reverted; (b) `canon_env_line` identity ⇒ `test_canon_env_line_windows_phrasing` +
    `test_canon_env_line_both_os_phrasings_converge` + 5 more FAILED (7F/13P) → reverted; post-revert 20/20 green.
    Gates: `ruff format --check` 0, `ruff check --no-cache` 0, `mypy --strict` 0 on both new modules,
    `lint-imports --no-cache` **9 kept / 0 broken** (REBASE NOTE: TASKS' "8/0" predates v0.1.61 — base truth is
    9/0, `_RECORDED_IGNORE_EDGE_CAP = 36`, unchanged by this task).

- [x] T-64-11 Byte-identical adoption by the 13 duplicate sites. Owner: software-engineer.
  Write set: EDIT `tests/unit/infrastructure/test_install_target_goldens.py`,
  `tests/unit/infrastructure/test_public_assets_profile.py`, `tests/integration/test_plugin_install_goldens.py`,
  `tests/integration/test_plugin_projection.py`, `tests/e2e/features/test_plugin_pipeline.py`,
  `tests/unit/cli/test_plugin_cli.py`, `tests/unit/cli/test_init_harness.py`,
  `tests/integration/cli/test_lifecycle_cli.py`, `tests/integration/cli/test_model_flag_removed_ac9.py`,
  `tests/integration/cli/test_implement_review_cli.py`, `tests/integration/cli/test_lifecycle_fr2_wire_verbs.py`,
  `tests/integration/cli/test_lifecycle_verb_governance.py`, `tests/integration/cli/test_lifecycle_policy_cli.py`.
  Checklist:
  - Delete each local `_norm_path_line`/`_canon_env_line`/`_sort_line_lists`/`_norm_stderr` copy; import from
    `tests.helpers.golden_platform`; kill the `test_public_assets_profile.py` → `test_install_target_goldens`
    cross-test import (AC-1 grep). Capture functions and golden-file constants stay local.
  - **Proof (AC-1):** `git diff --stat -- 'tests/**/_golden'` empty in this commit; full suite green with
    `UPDATE_INSTALL_GOLDENS` unset. Any needed regen = defect, STOP.
  - Preconditions: T-64-10 done. Done: zero-golden-diff + suite green + AC-1 no-cross-import grep test added.
  - AC-9 sabotage (f) re-point one adopter at a re-added stale local copy ⇒ the AC-1 grep test FAILS → revert.
  - Fate ledger — per file: which local helpers DELETED, which adopter imports NEW; grep transcript incl. tests/ +
    docstrings. Commit `refactor(T-64-11): ...`.
  - **EVIDENCE (2026-07-07, software-engineer):** per-file ledger —
    `test_install_target_goldens.py` DELETED `_norm_path_line/_norm_panel_body/_is_env_doctor_line/
    _canon_env_line/_sort_line_lists/_assert_golden/_TS_RE/_DCX9_WRAPPER_RE`, NEW import
    `assert_golden/is_env_doctor_line/norm_panel_body/norm_path_line` (+ local `_v0158_message`);
    `test_public_assets_profile.py` cross-test import KILLED, NEW import
    `is_env_doctor_line/norm_path_line/sort_line_lists` + local `_DOCTOR_GOLDEN` constant;
    `test_plugin_install_goldens.py` DELETED trio + `_assert_golden` + `_DCX9`, kept local `_is_plugins_line` +
    `_golden_a_message`, NEW import `assert_golden/is_env_doctor_line/norm_path_line`, docstring refs repointed;
    `test_plugin_projection.py` same DELETE set, same NEW import + local `_golden_b_message`;
    `test_plugin_pipeline.py` (e2e) DELETED trio + `_assert_matches_golden`, NEW import with
    `assert_golden(..., update_env=None)` (reproduction site never regens); bespoke `_squash`
    (whitespace-DROPPING, not a copy) stays local; 7× CLI files (`test_plugin_cli`, `test_init_harness`,
    `test_lifecycle_cli`, `test_model_flag_removed_ac9`, `test_implement_review_cli`,
    `test_lifecycle_fr2_wire_verbs`, `test_lifecycle_verb_governance`) DELETED `_ANSI_RE/_BOX_CHARS/
    _norm_stderr`, NEW import `norm_stderr`; `test_lifecycle_policy_cli.py` DELETED `_ANSI/_BOX` + the `_norm`
    body → thin `_norm` delegate to `norm_stderr(..., wide_glyphs=True)`. **REBASE DISCOVERY:**
    `tests/integration/test_plugin_uninstall.py` (landed v0.1.63 — post-enumeration 14th duplicate site) carried
    verbatim copies of `_norm_path_line/_is_env_doctor_line/_canon_env_line/_DCX9` — adopted alongside the 13
    (bespoke `_norm_doctor` composition stays local). AC-1 grep contract test added
    (`tests/unit/helpers/test_no_local_helper_copies.py`: no re-declared consolidated helper `def` tests-wide,
    with the SPEC-FR2 bespoke exemptions cited explicitly — `test_fragment_gate_goldens.py`,
    `test_api_golden.py`, `specs/test_doctor_golden.py` — and the `test_install_target_goldens` cross-import
    stays dead). **AC-1 PROOF:** `git diff --stat -- 'tests/**/_golden'` EMPTY (zero golden regen); full
    unpiped pytest with `UPDATE_INSTALL_GOLDENS` unset → **exit 0, 4800 passed / 17 skipped** (branch-point
    4795 collected + 22 new helper/contract tests = 4817). Grep transcript: `grep -rn "def _norm_path_line|def
    _canon_env_line|def _sort_line_lists|def _norm_stderr|def _assert_golden|def _assert_matches_golden|def
    _norm_panel_body|def _is_env_doctor_line" tests/` → only the cited bespoke exemptions;
    `grep -rn "test_install_target_goldens import" tests/` → none. AC-9 sabotage (f): re-added a stale local
    `norm_stderr` copy in `test_init_harness.py` ⇒ `test_no_test_file_redeclares_a_consolidated_helper` FAILED →
    reverted, 22/22 green. Gates: `ruff format --check` 0, `ruff check --no-cache` 0, `mypy --strict
    dadaia_workspace/` 0 (tests outside CI mypy scope; residual test-file mypy notes verified PRE-EXISTING at
    merge base), `lint-imports --no-cache` 9 kept / 0 broken, ignore-cap 36 (rebase-true base, supersedes the
    stale "8/0" text).

## W2 — FR3/FR4 entry-harness auto-default + PI seam

- [x] T-64-20 `core/session_env.entry_harness()` + lifecycle auto-default + loud echo + hermeticity. Owner:
  software-engineer. Write set: EDIT `dadaia_workspace/core/session_env.py`,
  `dadaia_workspace/cli/commands/lifecycle.py`, `tests/fixtures/harness_env.py` (+ conftest wiring),
  NEW/EDIT `tests/unit/core/test_session_env.py`, EDIT ≥2 lifecycle CLI test files for the verb-level matrix.
  Checklist:
  - `entry_harness()`: `DADAIA_ENTRY_HARNESS` in {codex,pi} > `CODEX_SESSION_ID` ⇒ "codex" > `None`. Stdlib-only;
    core leaf unchanged in layering.
  - CLI: default literal `"auto"` at the 12 `--harness` sites (L346/475/645/950/983/1016/1049/1178/1235/1289/
    1447/1528 pre-change); ONE `_resolve_default_harness()` shim → existing `_resolve_harness`; loud echo
    `[harness] auto-default: <name> (from entry session; pass --harness to override)` ONLY when a real worker was
    auto-defaulted; help text `"auto (entry session) | fake | codex | pi (claude is Layer-1 only)"`. `--step-harness`
    + LAW-1 claude rejection untouched.
  - Hermeticity (AC-4): autouse scrub of `DADAIA_ENTRY_HARNESS`/`CODEX_SESSION_ID`/`CLAUDE_CODE_SESSION_ID` over
    the lifecycle CLI envelope via `tests/fixtures/harness_env.py`; test sets a simulated developer
    `CODEX_SESSION_ID` and proves the envelope still resolves `fake`. **CI half (QA64-1):**
    <!-- AMEND:QA64-1 --> add the CI-scoped assert — active only when `GITHUB_ACTIONS` is set, skipped locally —
    that the GHA quality jobs' raw env carries NONE of the three entry-signal vars, so no CI shell step can
    auto-default a real worker outside pytest either.
  - Tests (AC-3, RED-first vs literal `"fake"`): resolver unit matrix (precedence, claude-only ⇒ None, garbage
    value ignored) + verb-level on one single-step verb AND the pipeline (echo asserted present/absent).
  - Preconditions: none (file-disjoint from W1). Done: matrix green; no real spawn in tests (fake/echo asserts only).
  - AC-9 sabotage (c) ignore `DADAIA_ENTRY_HARNESS` ⇒ precedence test FAILS → revert; (d) drop the echo ⇒ echo
    assert FAILS → revert.
  - Fate ledger — the 12 option sites enumerated with before/after default; existing lifecycle CLI tests that
    passed `--harness` explicitly SURVIVE unchanged. Commit `feat(T-64-20): ...`.
  - Evidence (2026-07-07): resolver matrix `tests/unit/core/test_session_env.py` (17 pass + CI-scoped skip local);
    shim matrix `tests/unit/cli/commands/test_lifecycle_harness_map.py`; verb-level `implement` + `pipeline`
    (echo present pi-entry / absent fake-explicit; echo on stderr so `--json` stdout stays pure). 12 sites
    pre-change L346/475/645/950/983/1016/1049/1178/1235/1289/1447/1528 default "fake" → post-change "auto"
    (grep `"auto",` = 12, `"fake", "--harness"` = 0). AC-9 (c) pin-ignored ⇒ 6 FAIL captured+reverted;
    (d) echo-dropped ⇒ 4 FAIL captured+reverted. Gates: ruff format --check 0, ruff check 0, mypy --strict
    dadaia_workspace/ 0, lint-imports 9 kept/0 broken, full pytest 4833 passed/18 skipped exit 0.

- [x] T-64-21 PI entry-signal seam in the Ring-1 extension. Owner: software-engineer (ai-engineer sign-off on the
  `public/**` surface). Write set: EDIT `dadaia_workspace/public/pi/extensions/dadaia-sdd-gate.ts`, NEW grep-level
  contract test (e.g. `tests/contract/test_pi_entry_signal.py`).
  Checklist:
  - Guarded export at factory load: set `DADAIA_ENTRY_HARNESS = "pi"` only when unset (operator pin wins); header
    note documents post-trust semantics + no-secrets **+ the ARCH64-2 security posture: the pin is session-wide
    and credit-affecting; set-only-when-unset; the FR3 loud echo guards every auto-default; the signal is never
    derived from telemetry**. <!-- AMEND:ARCH64-2 --> No other TS change.
  - Contract test asserts the canonical source (and staged copy when present) contains the guarded export;
    FR3 unit matrix already covers the `pi` value.
  - Preconditions: T-64-20 done. Done: grep contract green; `public doctor` `[ok] public-privacy` at W4 (AC-5).
  - Fate ledger — one lib-asset EDIT (manifest-tracked; propagates at W4 via stage/install, never hand-edited in
    projections). Commit `feat(T-64-21): ...`.
  - Evidence (2026-07-07): guarded pin at factory load (set-only-when-unset) + ARCH64-2 posture header in
    `dadaia_workspace/public/pi/extensions/dadaia-sdd-gate.ts`; contract `tests/contract/test_pi_entry_signal.py`
    (canonical guard + exactly-one-assignment + posture needles green; staged copy fail-soft pre-W4 skip).
    No other TS change; stage/install deferred to W4. Gates: ruff format/check 0, mypy --strict 0,
    lint-imports 9/0, full pytest 4835 passed/19 skipped exit 0.

## W3 — FR5 `tier:` → `dispatch_band:` rename (strictly AFTER W1)

- [x] T-64-30 Rename the frontmatter key in the 12 agent bodies. Owner: ai-engineer.
  Write set: EDIT `dadaia_workspace/public/agents/{project-manager,product-engineer,project-auditor,ai-engineer,
  software-engineer,qa-engineer,software-architect,security-reviewer,code-reviewer}.md`,
  `dadaia_workspace/public/plugins/frontend-design/agents/{frontend-engineer,design-specialist}.md`,
  `dadaia_workspace/public/plugins/devops/agents/devops-engineer.md`.
  Checklist: `tier: N` → `dispatch_band: N` (values unchanged; stubs untouched — they carry no tier). No body-prose
  change. Preconditions: T-64-11 done (ordering law); **v0.1.62 W3 + v0.1.63 W2/W3 landed (Ruling 64-A — this
  release is the LAST writer of the 12 bodies): REBASE onto their state, then post-rename re-run the `^tier:`
  grep AND verify v0.1.62's AC-6 adoption grep (handoff-v1.2/self_pull instruction present in all 12 bodies)
  stays satisfied.** <!-- AMEND:ARCHX-1 --> Done: `grep -rn "^tier:"` over both agent dirs = zero (AC-6 half)
  + the v0.1.62 AC-6 re-verification recorded. Fate ledger — 12 EDITs enumerated. Commit `feat(T-64-30): ...`.
  - Evidence (2026-07-07): 12 EDITs (fate ledger, `dispatch_band:` values unchanged) — project-manager 1,
    project-auditor 1, product-engineer 2, ai-engineer 3, software-engineer 3, qa-engineer 3,
    software-architect 3, security-reviewer 3, code-reviewer 3, frontend-engineer 3, design-specialist 3,
    devops-engineer 3. The 3 `plugin: true` stubs under `public/agents/` verified tier-less (untouched).
    `grep -rn "^tier:"` over both agent dirs = ZERO; `grep -rn "^dispatch_band:"` = exactly 12. Ruling 64-A
    re-verifications: (a) v61 AC-1 — `git diff -U0` shows ONLY the tier→dispatch_band line per file; all
    `model:`/`effort:` values untouched (opus×4, fable-5×5 w/ effort high/high/medium/low/low, sonnet×3);
    (b) v62 AC-6 — `handoff-v1.2` grep 12/12 AND `self_pull` grep 12/12 post-rename. RED-first window
    recorded for T-64-31: `tests/contract/test_agent_tier_taxonomy.py` = 2 failed / 2 passed (contract
    still reads `tier`; core + plugin band asserts get None) — expected RED, fix owned by T-64-31.

- [x] T-64-31 Parser/model/renderer/tests rename (tolerate-then-strip) + deliberate golden regens. Owner:
  software-engineer. Write set: EDIT `dadaia_workspace/features/agents/reader.py`,
  `dadaia_workspace/features/agents/__init__.py`, `dadaia_workspace/core/models/agent.py`,
  `dadaia_workspace/features/panel/views/api_agents.py`, `tests/contract/test_agent_tier_taxonomy.py`,
  `tests/unit/features/agents/test_reader.py`, `tests/unit/features/panel/test_api_agents.py`,
  `tests/unit/features/panel/test_api_golden.py` (+ its golden), `tests/unit/infrastructure/test_plugin_content.py`,
  `tests/unit/infrastructure/test_install_target_goldens.py` (+ `panel_runtime_validation_v0158.json`), any plugin
  golden embedding body bytes/API field.
  Checklist:
  - Reader: allowlist carries BOTH keys for the window; prefer `dispatch_band`, silent legacy `tier:` fallback
    (no new warning); missing-both keeps default-3 + warning (text names `dispatch_band`);
    `MissingDispatchBandError` + module alias `MissingTierError = MissingDispatchBandError`; `__init__` re-exports
    both. `AgentDTO.tier` → `dispatch_band`; `api_agents` renders `"dispatch_band"`.
  - Contract test: renamed assertions; the pinned `_CORE_MODEL_EFFORT` map + roster counts BYTE-UNCHANGED.
  - Fallback test (AC-6): a legacy `tier:`-only body resolves its band silently.
  - **Deliberate regens (AC-7):** each regenerated golden listed with a multiset diff proving EXACTLY the
    `tier`→`dispatch_band` token change (zero other delta/removals), via the W1 `assert_golden` mechanism.
    Verify (don't assume) install/doctor goldens need NO regen.
  - Preconditions: T-64-30 done. Done: AC-6 full (RED-first shown: pre-change contract test reads `tier`).
  - AC-9 sabotage (e) reader rejects legacy `tier:` ⇒ fallback test FAILS → revert.
  - Fate ledger — every EDIT + every REGEN-golden with its diff transcript. Commit `feat(T-64-31): ...`.
  - Evidence (2026-07-07): Fate ledger — 10 EDITs: `dadaia_workspace/features/agents/reader.py` (allowlist
    carries BOTH `dispatch_band` + legacy `tier`; prefer `dispatch_band`, SILENT legacy fallback — no new
    warning; missing-both default-3 warning renamed to name `dispatch_band`; `MissingDispatchBandError` +
    alias `MissingTierError = MissingDispatchBandError`), `features/agents/__init__.py` (re-exports both),
    `core/models/agent.py` (`AgentDTO.tier` → `dispatch_band`), `features/panel/views/api_agents.py`
    (renders `"dispatch_band"`), `tests/contract/test_agent_tier_taxonomy.py` (assertions read
    `dispatch_band`; `_CORE_MODEL_EFFORT` + `_MODEL_TIER` maps + roster counts BYTE-UNCHANGED; fn names
    kept — backlog BL-SCHEMA anchors pin them), `tests/unit/features/agents/test_reader.py` (band tests
    renamed + NEW AC-6 fallback test `test_legacy_tier_only_body_resolves_band_silently`: legacy-only body
    → band resolved, stderr EMPTY; `dispatch_band` beats stale `tier`; alias-identity assert),
    `tests/unit/features/panel/test_api_agents.py`, `tests/unit/features/panel/test_api_golden.py`,
    `tests/unit/infrastructure/test_install_target_goldens.py`,
    `tests/unit/infrastructure/test_plugin_content.py` (fixtures/asserts → `dispatch_band`). RED-first
    (AC-6 full): pre-change baseline captured — 2 contract FAILED + `test_plugin_content` AC-6 FAILED +
    `test_reader` topology FAILED (T-64-30 body rename) → all GREEN post-change. 2 REGEN-goldens (AC-7,
    via the W1 `assert_golden` mechanism under `UPDATE_API_GOLDEN` / `UPDATE_INSTALL_GOLDENS`):
    `tests/unit/features/panel/_golden/api_golden_v0155.json` — multiset diff: removed {tier: 1}, added
    {dispatch_band: 1}; `tests/unit/infrastructure/_golden/panel_runtime_validation_v0158.json` —
    removed {tier: 4}, added {dispatch_band: 4}; BOTH verified byte-equal to old-bytes-with-token-rename
    (zero other delta, zero removals). VERIFIED (not assumed) no-regen:
    `install_target_resolution_v0158.json` + `doctor_all_four_v0158.json` byte-unchanged under the regen
    env (0 `tier` tokens in either). AC-9(e) sabotage: reader raised `MissingDispatchBandError` on legacy
    `tier` ⇒ `test_legacy_tier_only_body_resolves_band_silently` FAILED (captured) → reverted. Stale-ref
    grep (`\.tier\b`/textual, dadaia_workspace/ + tests/): surviving hits are ONLY the registry Tier
    model-cost axis (`core/model_registry.py`, `runtime_transforms/codex_assets.py:118`,
    `infrastructure/codex_runtime.py:229`, registry-tier asserts in the contract test) + the deliberate
    deprecation alias + the deliberate legacy-fallback window (strip tracked by
    `dispatch-band-legacy-fallback-removal`). Gates: `ruff format --check` exit 0 (829 files),
    `ruff check --no-cache` exit 0, `mypy --strict dadaia_workspace/` exit 0 (313 files),
    `lint-imports --no-cache` 9 kept / 0 broken, full unpiped `pytest` exit 0 — 4836 passed / 19 skipped
    (the T-64-30 RED contract now GREEN).

## W4 — gates + projection ship

- [-] T-64-40 Full gates + instance re-projection. Owner: software-engineer (orchestrated; shell via PM/operator).
  Checklist: `ruff format --check` + `ruff check --no-cache` + `mypy --strict` + full **unpiped** `pytest` +
  `lint-imports --no-cache` (8/0, ignore-cap unchanged) + `dadaia specs doctor` (exit 0) + `dadaia backlog doctor`
  (exit 0); v0.1.50 frozen no-steal suite **zero-diff**; `dadaia public stage` → `dadaia public install --target
  all` → confirming `dadaia public doctor` (`[ok] public-privacy`, exit 0) — projections (incl. `.pi/` extension +
  renamed agent frontmatter) reconciled via the pipeline only. Reviews per release-governance cadence; push rides
  the security-verdict chokepoint. Done: transcripts on this line (AC-10). Commit `chore(T-64-40): ...`.
  - **AC-10 evidence (2026-07-07, PM shell):** unpiped pytest exit 0 — **4837 passed, 18 skipped** · ruff
    format --check 0 · ruff check --no-cache 0 · mypy --strict 0 · lint-imports --no-cache **9 kept / 0
    broken, ignore-cap 36** (rebase note: TASKS' "8/0" predates v0.1.61's 9th contract) · specs doctor exit 0
    · backlog doctor clean (after the recorded `golden-platform-normalization-layer` anchor repoint —
    T-64-11's helper deletion broke it; commit `dc3a5c8b`) · frozen v0.1.50 suite zero-diff vs main ·
    instance re-projection `stage → install --target all → doctor` all exit 0 with `[ok] public-privacy`
    (renamed frontmatter + the .pi/ guarded pin projected via the pipeline only). Task SHAs: W1 `5797a1de` +
    `1ddae485`, W2 `b4d744bd` + `3ed64aac`, W3 `5c1a7f1b` + `521deb01`.

## W5 — CLOSURE (MEMORY phase)

- [ ] T-64-50 CLOSURE.md + disposition sweep + memory truth + archive. Owner: product-engineer.
  Checklist: ACTIVE.md → CLOSURE (orchestrator); CLOSURE.md per skill template (Summary / Tasks+SHAs / Validations
  triples / Drifts / Memory updates / **Dispositions**: 3× `DELIVERED — v0.1.64` +
  `fast-tier-persona-validation` `REJECTED — premise-dead post-2026-07-06 retier` **after the operator
  ratifies/overrides** the handoff decision (override ⇒ re-disposition `DEFERRED` + revival carries SPEC §8
  AC-OPCHECK) / Backlog returns: `dispatch-band-legacy-fallback-removal` (+ optional
  `golden-normalizer-residual-consolidation`) / Archive **MOVE**); memory updates per SPEC §10 — **incl. the
  `harness-pi.md` ARCH64-2 security-posture note (session-wide credit-affecting pin; set-only-when-unset; loud
  echo; never telemetry-derived)** <!-- AMEND:ARCH64-2 --> — + catalog regen (`dadaia memory catalog generate`)
  BEFORE ACTIVE → none (closure order law). **Merge order (Ruling 64-B — this release closes LAST):**
  <!-- AMEND:ARCHX-2 --> REBASE `quality-assurance.md`, `tech-stack.md`, `agent-orchestration.md`,
  `dadaia-workflows.md`/`lifecycle-foundation.md` on the siblings' closed state (never revert their
  corrections); catalog regen includes all prior tldr/summary deltas. `dadaia specs doctor` exit 0;
  `git mv specs/releases/v0.1.64 specs/_archive/releases/v0.1.64` (surfaced to operator/devops).
  Preconditions: T-64-40 done + trio reviews green. Done: archive complete, ACTIVE.md advanced.
