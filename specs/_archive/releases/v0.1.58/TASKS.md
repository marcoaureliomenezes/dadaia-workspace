# TASKS — v0.1.58 — Harness & Projection Distribution

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared files (PLAN §Write sets: `public_assets.py`
W1+W3, `public_assets_common.py` W1+W3) are sequential — one owner, no parallel `[-]`. Every
implementation-wave task: **NO `specs/backlog/**` paths staged** (dead/surviving anchors dispositioned at
CLOSURE — T-58-70). Every move/rename/repoint grep **includes `tests/` AND non-import textual references**
(docstrings/comments). AC-9 mutation-sanity: each new test is sabotaged → shown to FAIL → reverted, captured
on the task line. **FR1 lands FIRST** — it is the identity seam FR2–FR5 build on.

## W0 — definition

- [x] T-58-01 SPEC/PLAN/TASKS authored from the 2026-07-04 **code read** (not a dossier restatement):
  `harness_models.harnesses()` is the Layer-2 model catalog (pi, codex) NOT the L1/L2 identity registry;
  `AgentRuntimeKind` is the runtime-adapter roster; the L1 roster `{claude,codex,pi}` is bare literals at 4
  Python sites + JS; `dadaia init` has no `--harness`; `WorkspaceService.init` always makes all-four +
  configures the claude hook; `public_assets.doctor()` unconditionally checks all-four runtime projections
  (would false-fail a partial install); `_consumer_repos_for_root` requires an in-repo `.dadaia/agentic/`
  marker that the repo-cleanliness law forbids (fan-out dead by construction); `_doctor_guardrail_pair`
  `[skip]`s marker-less repos; `spec_contexts.json` (v2, `repo_slug`) is the clean detection source; PI has
  no session env var (entry-harness auto-default not cleanly detectable). Mandatory release-definition grill
  on the picked set (report emitted). **Rulings recorded (§9, operator unavailable — overridable):** A new
  registry not editing `harnesses()`; B scoped literal centralization; C `--harness` flag + persisted
  profile; D profile is install/doctor source of truth; E no harness removal; F defer workflow-spawn
  auto-default; G keep `_consumer_repos_for_root` by name; H fan to all on-disk contexts minus self; I
  tri-copy untouched; J doctor flags stale copies. **Dual definition review 2026-07-04 (qa REJECT Q1–Q7 +
  architect REJECT A1–A7) — all amendments folded into SPEC/PLAN/TASKS with `(Q#)`/`(A#)` markers; PM binding
  rulings K (A2 REPOINT the 3 L2 `_LAYER2_HARNESSES` sites), L (A5 consumer root AGENTS.md lib-owned,
  restore-with-`[updated]`-line), M (A6 doctor-before-install ship order) recorded in §9.** `Aprovado` after
  the confirming dual review re-pass; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 typed core harness registry (golden-first)

- [x] T-58-10 Capture + commit the behaviour goldens BEFORE any refactor. Checklist:
  - **Evidence:** `tests/unit/infrastructure/test_install_target_goldens.py` (4 tests, all green) +
    3 committed goldens under `tests/unit/infrastructure/_golden/`: `install_target_resolution_v0158.json`
    (5 targets: all=135/agents=42/claude=67/codex=70/pi=26 normalized `installed` lines),
    `panel_runtime_validation_v0158.json` (api_workflows + api_agents × claude/codex/pi/bogus — api_agents
    DISCRIMINATES: claude→[software-engineer], codex→[qa-engineer], pi→[security-reviewer], bogus→claude),
    `doctor_all_four_v0158.json` (219 report lines on a fully-installed all-four no-profile tree, git-dirty
    env-lines dropped, all paths `<WS>`-normalized). Captured on the pre-registry tree — the AC-1 behaviour lock.
  - Add `tests/unit/infrastructure/test_install_target_goldens.py` running `public_assets.install()` under a
    `FileSystemPublicAssetManager` + `tmp_path` for each `--target` in `{all, agents, claude, codex, pi}`;
    capture the produced `installed` list. Capture the panel runtime-validation accept/reject outputs
    (`api_workflows`/`api_agents` for `claude`/`codex`/`pi`/a bogus value).
  - **(Q2/A4) ALSO capture + commit a golden of `public_assets.doctor()`'s full report list** on a
    fully-installed all-four (no-profile) tree under `tmp_path` + `FileSystemPublicAssetManager` —
    path/version-normalized (v0.1.55), any clock the output depends on frozen. This is the FR3 absent-profile
    back-compat lock (AC-5 asserts byte-equality against it); captured now because W1 precedes W3.
  - **Path-normalize** every golden (v0.1.55 platform-invariant law) — `.dadaia/` and `repos/` refs +
    `os.sep` normalized to placeholders. Commit the goldens. These are the AC-1 behaviour lock.
  - **AC-11 ledger** — NEW: `test_install_target_goldens.py` + install/panel/**doctor** goldens. No
    `specs/backlog/**` staged.

- [x] T-58-11 Add `core/harness_registry.py` and consume it in the roster-encoding literals. Checklist:
  - **Evidence:** NEW `dadaia_workspace/core/harness_registry.py` (pure core leaf, stdlib-only —
    lint-imports 8 kept / 0 broken, core contract intact) + `tests/unit/core/test_harness_registry.py`
    (30 tests). **AC-1:** the T-58-10 goldens (install/panel/doctor) replay BYTE-IDENTICAL post-refactor
    (test_install_target_goldens.py 4/4 green, no regeneration). **AC-9(a):** reverted `api_workflows.py:70`
    to a hard-coded `("claude", "codex")` tuple (omits pi) ⇒ `test_roster_literal_absent_and_registry_consumed
    [api_workflows.py]` FAILED (`'"claude","codex"'` found) ⇒ reverted, green. **AC-9(a′):** reverted
    `policy_resolver.py:136` to bare `frozenset({"codex", "pi"})` ⇒ same grep test FAILED for
    `policy_resolver.py` ⇒ reverted, green. **Contract test (R1):** `frozenset(L2_WORKER_HARNESSES) ==
    frozenset(harness_models.harnesses())` passes (order-independent; harnesses() PI-first). **Fate ledger:**
    `test_api_golden.py`+`api_golden_v0155.json` SURVIVE byte-identical INVARIANT (no regen);
    `test_api_workflows.py`/`test_api_agents.py`/`test_public_assets.py`/`test_policy_doctor.py`/
    `test_policy_resolver.py`/`test_json_workflow_model_policy_store.py` all SURVIVE (277 green).
    Full gates: ruff format+check, mypy --strict (306 files), lint-imports (8/0), full pytest 4524 passed.
  - **NEW `dadaia_workspace/core/harness_registry.py`** — pure `core` leaf (stdlib only, no upward import):
    `L1_ENTRY_HARNESSES = ("claude","codex","pi")`, `L2_WORKER_HARNESSES = ("codex","pi")`, capability
    predicates (`is_l1`/`is_l2`/`can_be_workflow_worker`), `PROJECTION_TARGETS`/`INSTALL_TARGETS` (the
    `_VALID_TARGETS` single source), `parse_harness_set(value) -> tuple[str,...]` (comma set / `all` →
    validated ordered L1 tuple; unknown name raises a listing error).
  - **Consume — L1 (Ruling B — scoped)**: repoint `features/panel/views/api_workflows.py:70`,
    `api_agents.py:161`, `infrastructure/public_assets_common.py:20` (`_VALID_TARGETS` → registry re-export),
    `infrastructure/public_assets.py:275` (target list) to registry lookups. **Leave the documented
    residual**: telemetry readers, panel display strings, CSS tokens, JS `runtime.js` (cannot import Python),
    JSON schema enums.
  - **(A2 / Ruling K — REPOINT L2, PM binding)**: repoint the 3 bare-literal `_LAYER2_HARNESSES` sites —
    `features/lifecycle/policy_doctor.py:77`, `features/lifecycle/policy_resolver.py:136`,
    `infrastructure/json_workflow_model_policy_store.py:54` — to `harness_registry.L2_WORKER_HARNESSES`,
    making the L2 surface load-bearing NOW. Do **NOT** repoint the 4th derived site
    `features/lifecycle/model_profiles.py:112` (it derives from `harness_models` constants) — instead add a
    **contract test** asserting `frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())` (order-independent — `harnesses()` is PI-first; the registry constant keeps canonical order `("codex", "pi")`) (R1).
  - **Single-source law**: `tech-stack.md` "Agent runtimes" stays the roster doc source; `harness_models.py`
    (L2 catalog) + `AgentRuntimeKind` unchanged (the contract test locks the two coincident encodings equal).
  - **Tests — AC-1** install/panel goldens byte-identical post-refactor; **AC-2** `core/test_harness_registry.py`:
    predicates (`is_l2("claude")` False, `can_be_workflow_worker("claude")` False), `parse_harness_set`
    (`"codex,pi"`, `"all"`, `"bogus"` raises), the L2⇔`harness_models.harnesses()` contract test, + a grep test
    that the tuple/set literals are gone from all **7** sites (4 L1 + 3 L2).
  - **AC-9(a) sabotage:** point one L1 repointed literal back at a hard-coded tuple omitting `pi` ⇒ the AC-2
    consumption test FAILS → revert. **(a′/A2) AC-9 sabotage:** point `policy_resolver.py:136` back at a bare
    `{"codex","pi"}` literal ⇒ the AC-2 L2-consumption grep test FAILS → revert. Capture each command +
    failing test on this line.
  - **existing-test fate ledger (Q3 — file-enumerated):** SURVIVE byte-identical INVARIANT —
    `tests/unit/features/panel/test_api_golden.py` + `_golden/api_golden_v0155.json` (reproduced from the
    registry-backed views; **a byte diff is adjudicated as INVARIANT, never regenerated to mask a behaviour
    change**). SURVIVE — `tests/integration/panel/test_api_workflows.py` + `test_api_agents.py` (runtime
    validation now via registry, same behaviour); `tests/unit/infrastructure/test_public_assets.py`
    (`_VALID_TARGETS` import) via the re-export; the 3 L2-site test suites
    (`test_policy_doctor.py`/`test_policy_resolver.py`/`test_json_workflow_model_policy_store.py`) SURVIVE
    (same frozenset value, now sourced from the registry).
  - **AC-11 ledger** — NEW: `core/harness_registry.py`, `test_harness_registry.py`; CENTRALIZED (7 sites):
    4 L1 (`api_workflows.py:70`, `api_agents.py:161`, `public_assets_common.py:20`, `public_assets.py:275`)
    + 3 L2 (`policy_doctor.py:77`, `policy_resolver.py:136`, `json_workflow_model_policy_store.py:54`);
    RECONCILED (not repointed): `model_profiles.py:112` (contract test); SURVIVING/EDITED:
    `public_assets_common._VALID_TARGETS` (→ registry re-export), `public_assets.py` target list, the 2 panel
    views; DEAD: the 7 inline tuple/set literals. Residual literals (readers / panel display / CSS / JS /
    schema) enumerated + justified. No `specs/backlog/**` staged.

## W2 — FR2 `init --harness` profiles + persisted profile + harness-aware scaffold

- [x] T-58-20 `dadaia init --harness <set>` + harness-aware `WorkspaceService.init` + persisted profile.
  Checklist:
  - **(A1 — persistence seam, ports-and-adapters, layer-pinned; BLOCKING):**
    - **`core`**: NEW pure typed model `HarnessProfile` (`schema_version` + `harnesses` tuple) +
      `parse_harness_set` (in `core/harness_registry.py`) — **NO I/O in `core`** (mirrors the discipline of
      `core/models/spec_context.py`, not the IO).
    - **`core/protocols`**: NEW `HarnessProfileStore` port (read/write signature).
    - **`infrastructure`**: NEW `json_harness_profile_store.py` ADAPTER doing the JSON read/write, mirroring
      `infrastructure/json_context_store.py`; consumed same-layer by `public_assets` (W3).
    - **`features/workspace/service.py`**: init-time WRITE via the injected `core.protocols` port OR inline
      like the existing `_init_json_file` bootstrap.
    - **Forbidden edges (AC-10 ignore-cap 9 UNCHANGED):** NO new `features → infrastructure` import; NO
      `infrastructure → features` import. Delete any "core/models/state helper doing IO" phrasing.
  - **CLI** (`cli/commands/init.py`): add `--harness <set>` (default `all`); parse via
    `harness_registry.parse_harness_set`; a bad value raises Click `BadParameter`.
  - **Harness-aware `WorkspaceService.init`** (`features/workspace/service.py`): thread the chosen set;
    create only chosen harnesses' dirs (`.claude/` / `.codex/` / `.pi/`); `_configure_hook` (claude
    `settings.json`) runs only when `claude` in set; install only the profile set (never `target="all"` for
    a subset).
  - **Persisted profile**: write `.dadaia/states/harness_profile.json`
    (`{"schema_version":"1","harnesses":[...]}`) **via the infra adapter**; idempotent (re-run same set =
    no-op, no second hook entry).
  - **Tests — AC-3** (`tests/unit/cli/test_init_harness.py`): `--harness claude` → `.claude/` + hook, no
    `.codex/`/`.pi/`; `--harness codex,pi` → `.codex/` (+ `.dadaia/hooks/codex-*`) + `.pi/`, no `.claude/`
    agents; `--harness` omitted → all-four (back-compat); `--harness zzz` → `exit_code == 2`, `"zzz"`/
    `"harness"` in `result.stderr`, empty `result.stdout` (**no `mix_stderr` kwarg**). **RED-first:** pre-fix
    `init` always produced all-four. **AC-4** (`test_service_harness_profile.py`): profile file records the
    set; idempotent; absent profile treated as all-four.
  - **Layer-boundary check (A1)**: `lint-imports --no-cache` stays `8 kept / 0 broken`, ignore-cap 9
    UNCHANGED (no new `features → infra` edge; no `infra → features` edge) — asserted in W6 gates.
  - **AC-9(b) sabotage:** make `WorkspaceService.init` ignore the harness set (always all-four) ⇒ the AC-3
    claude-only test FAILS → revert. **DONE:** sabotage = `chosen = L1_ENTRY_HARNESSES` (ignore `harnesses`
    param) in `WorkspaceService.init`; command
    `pytest tests/unit/cli/test_init_harness.py::test_harness_claude_scaffolds_claude_only -p no:cacheprovider`
    → **FAILED** at `assert not (tmp_path / ".codex").exists()` (`.codex/` created because init always
    scaffolds all-four). Reverted to `chosen = tuple(harnesses) if harnesses is not None else
    L1_ENTRY_HARNESSES`; re-run → 4 passed. **RED-first also captured:** the same suite run against the
    pre-flag HEAD failed 3/4 (claude-only, codex,pi, bad-value: `No such option: --harness`); the omitted →
    all-four back-compat test passed pre-change, confirming the "always all-four" baseline.
  - **existing-test fate ledger (Q3):** SURVIVE/EXTEND — `tests/unit/test_workspace_service.py` (the canonical
    `WorkspaceService.init` suite; there is no `tests/unit/features/workspace/test_service.py`) SURVIVES
    **unchanged** (10 tests pass: default `--harness` omitted still yields all-four — `.claude`+`.codex`
    created, ctx-inject hook configured; idempotent; state files); the all-harness `init` E2E in
    `tests/e2e/features/test_public_pipeline.py` SURVIVES (unchanged default path) — full unpiped suite
    **4539 passed / 17 skipped / 0 failed**. The v0.1.50 frozen no-steal lease/gate suite is **zero-diff**
    (release never enters `spec_context`/lease/gate). NEW sibling coverage lives in NEW files (no frozen edit).
  - **AC-11 ledger** — NEW: `core/models/harness_profile.py` (`HarnessProfile` pure model, NO I/O),
    `core/protocols/harness_profile_store.py` (`HarnessProfileStore` port), `infrastructure/json_harness_profile_store.py`
    (`JsonHarnessProfileStore` adapter, mirrors `json_context_store.py` read/write style; W3 read-side consumer),
    `tests/unit/cli/test_init_harness.py` (AC-3), `tests/unit/features/workspace/test_service_harness_profile.py`
    (AC-4), `tests/unit/infrastructure/test_json_harness_profile_store.py` (adapter round-trip). REUSED:
    `parse_harness_set` (already in `core/harness_registry.py` from W1 — extended NOT). EDITED: `cli/commands/init.py`
    (`--harness` default `all` → `parse_harness_set` → `typer.BadParameter`, parsed before any stdout),
    `features/workspace/service.py` (harness-aware `init` + `_install_for_harnesses` per-target subset +
    inline `_write_harness_profile` bootstrap + `.claude`/`.codex` dir + `_configure_hook` gating). SEAM:
    write is INLINE (allowed `_init_json_file`-style; no new `features→infra` edge), adapter serves W3 read.
    Gates: ruff format+check clean, `mypy --strict` clean (309 files), `lint-imports --no-cache` **8 kept / 0
    broken**, ignore-cap **26 UNCHANGED** (`features-no-infrastructure` still 9). No `specs/backlog/**` staged.
    Deviation: pi-only/agents-only fresh init installs no chokepoint scripts (existing rule: scripts install
    for `{all,claude,codex}` targets — FR2 "follow the existing rule"); flagged for W3/W5 (not a W2 AC).

## W3 — FR3 profile-aware `public install`-all + `public doctor`

- [x] T-58-30 Profile-aware install-all + profile-scoped doctor. Checklist:
  - **Evidence:** EDITED `dadaia_workspace/infrastructure/public_assets.py` — (1) `install()`
    reads `.dadaia/states/harness_profile.json` via the same-layer `JsonHarnessProfileStore`
    adapter (new `_profile_harnesses` helper): `target=="all"` installs `("agents", *profile)`
    when a profile exists, all-four when absent (back-compat), explicit `--target X` overrides;
    (2) `doctor()` scopes the inline `_compare` block — claude `settings.json` gated on
    `claude in profile`; codex hooks.json/wrappers/config.toml/rules gated on `codex`; the
    `.pi/` tree gated on `pi`; **(Q1)** `check_codex_drift` (D-CX-1..10) + `codex_trust_boundary_info`
    gated on `codex in profile`; **(A3)** `_OUT_OF_PROFILE_WARN` emitted for a runtime dir that
    physically exists outside the profile (never silent). Kept unconditional: `classify_workflows`,
    `check_codex_rule_corpus_reachable`, `check_agent_skill_refs`, `check_memory_phase_single_source`,
    the runtime_expectations agents/claude/scripts loop, `_check_public_privacy`, git-dirty.
    NEW `tests/unit/infrastructure/test_public_assets_profile.py` (8 tests, all green).
  - **AC-5 RED-first (captured against unmodified public_assets.py):** the new suite ran 5
    failed / 3 passed — `test_claude_only_profile_install_all_writes_only_claude` FAILED at
    `assert not (ws/".codex").exists()` (install-all ignored the profile → all-four written);
    `test_claude_only_profile_doctor_is_green` FAILED with the D-CX-1 ×12 `[missing]
    codex:agents/<name>.toml (D-CX-1)` lines + `[missing] pi:*` + `[drift] codex:hooks.json`;
    the CLI-exit-0 test FAILED (exit 1); the stale-`.codex` A3 test FAILED (no out-of-profile
    line). The absent-profile byte-equality + explicit-override invariants PASSED pre-fix.
    Post-fix: 8/8 green.
  - **(Q2/A4) byte-equality:** `test_absent_profile_doctor_byte_equals_all_four_golden` asserts
    the absent-profile doctor == `tests/unit/infrastructure/_golden/doctor_all_four_v0158.json`
    using the W1 golden normalizer (`_norm_path_line` + git-dirty exclusion, imported from
    `test_install_target_goldens`) — PASS. The W1 `test_install_target_goldens.py` doctor golden
    also replays byte-identical (201 fate-ledger tests green).
  - **AC-9 sabotages (captured → reverted):** (c) `active = set(L1_ENTRY_HARNESSES)` (ignore
    profile) ⇒ `test_claude_only_profile_doctor_is_green` FAILED on the D-CX-1 assertion ⇒
    reverted → 1 passed. (c′) `check_codex_drift` unconditional (inline block still scoped) ⇒
    same green test FAILED with the D-CX-1 ×12 lines ⇒ reverted → 1 passed. (c″) drop the codex
    `_OUT_OF_PROFILE_WARN` branch (zero lines for on-disk out-of-profile) ⇒
    `test_stale_out_of_profile_codex_on_disk_is_not_silent` FAILED (report ended at
    `[ok] public-privacy`, no out-of-profile line) ⇒ reverted → 1 passed.
  - **Fate ledger (SURVIVE byte-identical on the absent-profile path):**
    `tests/integration/test_public_doctor_parity.py`,
    `tests/unit/features/public_assets/test_doctor_projected_drift.py`,
    `tests/unit/infrastructure/test_public_assets.py` doctor cases (`TestDoctorMethod`/
    `TestDoctorGitDirtyCheck`/`TestDoctorFindingPersistence`),
    `tests/unit/infrastructure/test_install_target_goldens.py` (incl. the doctor golden) — all
    SURVIVE (201 passed together, no regeneration). Q2 golden proves the absent-profile lock.
  - **Gates:** ruff format --check (794 files) clean; ruff check --no-cache clean; mypy --strict
    clean (309 files); lint-imports --no-cache **8 kept / 0 broken** (ignore-cap unchanged — the
    W2 `json_harness_profile_store` adapter is consumed same-layer by `public_assets`, no new
    features→infra / infra→features edge); full unpiped pytest **4547 passed / 17 skipped / 0
    failed**. NO `specs/backlog/**` staged.
  - **Boundary flagged for W5 (not silently gated):** the `runtime_expectations` claude/pi
    projection loop (claude rules/skills/agents/workflows + scripts) stays UNCONDITIONAL per the
    T-58-30 scope (only the inline `_compare` block is scoped). For a **claude-only** tree this is
    fine (claude installed → `[ok]`; W3 tests are claude-only). A **codex-only / pi-only** doctor
    would still emit `[missing] claude:*` from that loop, so W5 (T-58-50) codex-only/pi-only green
    will additionally need that loop scoped — flagged as a boundary rather than expanding W3 scope.
    (The W2 pi-only-scripts boundary does NOT bite W3: profile-aware install-all keeps `target=="all"`
    so scripts install for the claude profile.)
  - **Install-all reads the profile** (`public_assets.install`, via the W2 `json_harness_profile_store`
    adapter): install the profile set when `.dadaia/states/harness_profile.json` exists; absent ⇒ all-four
    (back-compat); explicit `--target claude|codex|pi|agents` overrides regardless of profile.
  - **Doctor scopes runtime expectations** (`public_assets.doctor`): the inline `_compare` block — claude
    `settings.json` only when `claude` in profile; codex `hooks.json`/`config.toml`/rules/`.dadaia/hooks/codex-*`
    only when `codex`; `.pi/` tree only when `pi`.
  - **(Q1, BLOCKING) Gate the codex-parity block on `codex in profile`:** `check_codex_drift`
    (D-CX-1..10 — the source of `[missing] codex:agents/<name>.toml (D-CX-1)` ×12 for any codex-absent tree)
    **and** `codex_trust_boundary_info` run only when `codex` in profile (absent ⇒ run). **Stay unconditional
    (harness-independent):** `check_codex_rule_corpus_reachable` (safe — early-returns on absent
    `.codex/agents`), `classify_workflows`, `check_agent_skill_refs`, `check_memory_phase_single_source`,
    agents/`.agents` skills, AGENTS.md pair, chokepoint scripts, `_check_public_privacy` (`[ok] public-privacy`),
    git-dirty.
  - **(A3, BLOCKING) Out-of-profile runtime present on disk is NEVER silent:** when a runtime dir OUTSIDE the
    profile physically exists (e.g. a hand-installed `.codex/`), emit a non-silent `[warn] <harness>:
    out-of-profile runtime present (drift unchecked)` (or a `[drift]`). Pure silence only for a genuinely-absent
    dir.
  - **(Q7) "green" is mechanical:** report list has no `[missing]`/`[drift]`/`[fail]` for out-of-profile
    harnesses AND `dadaia public doctor` CLI exit 0.
  - **Tests — AC-5** (`test_public_assets_profile.py`): a claude-only workspace's `install` (no target)
    writes only the claude projection (no codex/pi write); `public doctor` is green (Q7) — the report list has
    **NO `[missing] codex:agents/*.toml (D-CX-1)`** and no `[missing]` `.codex/`/`.pi/`, CLI exit 0.
    **RED-first:** pre-fix reports `[missing]` codex/pi + the D-CX-1 ×12 `codex:agents` lines, CLI exit 1.
    **(Q2/A4)** absent-profile doctor asserts **byte-equality vs the T-58-10 all-four doctor golden**.
    **(A3) RED-first:** claude-only profile + a stale `.codex/hooks.json` on disk ⇒ a non-silent line (not
    green). Explicit `--target codex` still installs codex (override).
  - **AC-9(c) sabotage:** make `public_assets.doctor()` ignore the profile for the inline block (always
    all-four) ⇒ AC-5 claude-only green test FAILS with a `[missing]` codex line → revert. **(c′/Q1) sabotage:**
    leave `check_codex_drift` unconditional ⇒ AC-5 FAILS with `[missing] codex:agents/*.toml (D-CX-1)` →
    revert. **(c″/A3) sabotage:** make the doctor emit ZERO lines for an on-disk out-of-profile runtime ⇒ the
    stale-`.codex/` non-silent test FAILS (reads green) → revert. Capture each command + failing test.
  - **existing-test fate ledger (Q3 — file-enumerated):** SURVIVE byte-identical on the absent-profile path
    (proven by the Q2/A4 doctor golden) — `tests/integration/test_public_doctor_parity.py`,
    `tests/unit/features/public_assets/test_doctor_projected_drift.py`,
    `tests/unit/infrastructure/test_public_assets.py` doctor cases.
  - **AC-11 ledger** — EDITED: `public_assets.install` (profile read via adapter) + `doctor` (profile scope
    incl. Q1 codex-parity gate + A3 out-of-profile line). No `specs/backlog/**` staged.

## W4 — FR4 consumer `AGENTS.md` fan-out redesign

- [x] T-58-40 Registry-based consumer detection + doctor flagging. Checklist:
  - **Evidence:** EDITED `dadaia_workspace/infrastructure/workspace_guardrail.py` — (1)
    `_consumer_repos_for_root` KEPT BY NAME, reimplemented to read
    `.dadaia/states/spec_contexts.json` (direct defensive JSON read, never raises) and derive
    `repos/<repo_slug>/` for each context whose dir exists on disk (alive OR dead — Ruling H); the
    in-repo `.dadaia/agentic/` marker requirement DROPPED; absent-repo contexts skipped silently (no
    stderr); duplicate slugs collapsed; `_is_self_repo` skip RETAINED in the callers. (2)
    `_install_guardrail_pair`/`_write_pair` refactored to a `_write_one(dst, expected_sha, write_fn,
    is_consumer)` helper: fresh create → `[ok]`, identical → `[skip]` (or `[ok]` under force),
    **divergent CONSUMER overwrite → DISTINCT `[updated] <path> (overwrote divergent workspace-law
    copy)`** (Ruling L / A5); the workspace-root pair keeps `[ok]` overwrite semantics; nested subtree
    AGENTS.md never touched (only repo root written). (3) `_doctor_guardrail_pair` iterates the same
    registry-derived repos, emits `[drift]`/`[missing]`/`[ok]`, never `[skip]` for a real consumer
    (Ruling J). NEW `tests/unit/infrastructure/test_consumer_fanout.py` (11 tests, all green).
  - **RED-first captures (AC-6/AC-7, against unmodified `workspace_guardrail.py`):** the new suite ran
    **10 failed / 1 passed** — `test_fan_out_fires_for_registry_listed_marker_less_consumer` FAILED
    (`repos/demo/AGENTS.md` not written; stderr `[skip] .../repos/demo/AGENTS.md (no .dadaia/ marker)`
    — old marker filter drops the marker-less registry repo); `test_doctor_flags_drift_for_stale_consumer`
    FAILED (report list == `['[missing] root:AGENTS.md','[missing] root:CLAUDE.md']`, **NO
    `repos/demo:AGENTS.md` line at all** — Q5-corrected anchor). The 1 pre-passing case
    (`test_tri_copy_targets_not_written_by_fan_out`) is invariant in both states. Post-fix: 11/11 green.
  - **AC-9 sabotages (captured → reverted):** (d) restored the in-repo `.dadaia/agentic/` marker
    requirement in `_consumer_repos_for_root` (`candidate.is_dir() and (candidate/".dadaia"/"agentic").is_dir()`)
    ⇒ `test_fan_out_fires_for_registry_listed_marker_less_consumer` FAILED at
    `assert (repo/"AGENTS.md").exists()` (nothing written) ⇒ reverted → green. (e/Q5-corrected) SAME
    restored-marker-filter sabotage ⇒ `test_doctor_flags_drift_for_stale_consumer` FAILED — report list
    dropped to `['[missing] root:AGENTS.md','[missing] root:CLAUDE.md']`, the `[drift] repos/demo:AGENTS.md`
    line disappeared ⇒ reverted → green.
  - **Fate ledger (Q3 — INVERT, outcomes):** `tests/unit/features/public/test_workspace_guardrail_pair.py`
    — Case 1 (`test_four_target_projection_write`) INVERTED to a registry-listed marker-less consumer
    (kept 4×`[ok]` + byte-identical/hash-compare); Case 4 (`test_skip_self_slug_package_version_match`)
    INVERTED (registry-listed self repo, RETAINED manifest-based self-skip, kept assertions); Case 6
    (`test_doctor_four_line_output`) INVERTED (registry-listed, kept 4-label `[ok]`); Case 2
    (`test_skip_no_dadaia_marker`) INVERTED → `test_unregistered_repo_not_written`; **Case 3
    (`test_skip_no_agentic_marker`) DELETED** — the `.dadaia/` vs `.dadaia/agentic/` marker distinction it
    exercised no longer exists; registry-based detection gives it no invertible assertion distinct from
    the inverted Case 2. `tests/integration/test_public_doctor_parity.py::test_doctor_emits_four_labels_with_one_consumer`
    INVERTED (via `_add_consumer` → registry registration, kept `[ok]`×4) +
    `test_no_marker_consumer...`→`test_unregistered_consumer...` repointed. Grep-repointed EVERY
    `_consumer_repos_for_root`/`.dadaia/agentic` consumer-marker usage: `test_public_assets.py` (helper
    `_add_marker_consumer` now registers in the registry + keeps manifest for retained `_is_self_repo`;
    `TestConsumerReposForRoot`/`TestInstanceConsumerRepos` skip-stderr assertions dropped, renamed to
    `test_unregistered_on_disk_repo_not_detected`; `TestInstallConsumerReposGuardrailPair` divergent-overwrite
    assertion repointed `[ok]`→`[updated]` per Ruling L); `test_public_install_e2e.py`,
    `test_public_install_scope_flags.py` (contract), `test_install_scope_flags.py` (integration) helpers
    all register in the registry.
  - **Gates (all five, `.dadaia/.venv/bin`):** `ruff format --check` (795 files) clean; `ruff check
    --no-cache` clean; `mypy --strict dadaia_workspace/` clean (309 files); `lint-imports --no-cache`
    **8 kept / 0 broken** (ignore-cap UNCHANGED — the registry read is a direct defensive JSON read, no
    new import edge); full **unpiped** `pytest -p no:cacheprovider` **4557 passed / 17 skipped / 0
    failed** (exit 0). Frozen no-steal suite zero-diff. No `specs/backlog/**` staged; no `.dadaia/` inside
    the repo tree.
  - **Deviation:** `_consumer_repos_for_root` reads `spec_contexts.json` via a direct, defensive
    `json.loads` (never-raises contract) rather than `JsonContextStore.list_all()` — the store raises
    `SchemaVersionError` on v1/unknown registries and its `_load` carries a "not outside SpecContextService"
    caveat, so a read-only best-effort detection path is more honest and keeps fan-out/doctor from
    crashing on a malformed registry. Same schema (`repo_slug`), no new infra→infra dependency.
  - **Reimplement `_consumer_repos_for_root` (KEPT BY NAME, Ruling G)** (`workspace_guardrail.py`): read
    `.dadaia/states/spec_contexts.json`, derive `repos/<repo_slug>/` for each context whose dir exists on
    disk (alive OR dead, Ruling H); drop the in-repo `.dadaia/agentic/` marker requirement; skip absent
    repos silently; **retain `_is_self_repo` skip**.
  - **Fan-out fires**: `_install_guardrail_pair` writes the workspace-law `AGENTS.md` + 1-line `CLAUDE.md`
    stub to each detected on-disk consumer repo (hash-compare). **Tri-copy untouched (Ruling I)** — do NOT
    write `specs/AGENTS.md` / `specs/memory/AGENTS.md` / any `public/scaffold/**` target.
  - **(A5/Ruling L — consumer root AGENTS.md is lib-owned)**: a divergent (hand-edited) consumer root
    `AGENTS.md` is **restored to canonical**, and `_write_pair` emits a **DISTINCT** line
    `[updated] <path> (overwrote divergent workspace-law copy)` (separate from the `[ok]` fresh-create line),
    so restoration is never silent. Nested subtree `AGENTS.md` (e.g. `repos/<slug>/src/AGENTS.md`) is
    **never touched**.
  - **Doctor flags stale/missing (Ruling J)**: `_doctor_guardrail_pair` iterates the same registry-derived
    on-disk repos, emits `[drift]`/`[missing]`/`[ok]` per consumer `AGENTS.md`/`CLAUDE.md`, never `[skip]`
    for a real consumer repo. Labels stay `repos/<slug>:AGENTS.md` / `repos/<slug>:CLAUDE.md`.
  - **Tests — AC-6** (`test_consumer_fanout.py`): fixture workspace with `spec_contexts.json` naming context
    `demo` + real `repos/demo/` (no in-repo `.dadaia/`) → `install` (scope="all") writes
    `repos/demo/AGENTS.md` (workspace-law) + `repos/demo/CLAUDE.md`; **RED-first:** pre-fix (marker-based)
    writes nothing. A registry context with no on-disk `repos/<slug>/` is skipped without error; the
    self-repo is skipped; `specs/memory/AGENTS.md` NOT written. **(A5)** a **divergent** `repos/demo/AGENTS.md`
    is restored to canonical with the DISTINCT `[updated]` line; a nested `repos/demo/src/AGENTS.md` is
    UNTOUCHED. **AC-7**: `public doctor` with a stale `repos/demo/AGENTS.md` — the returned **report list**
    contains `[drift] repos/demo:AGENTS.md`, absent → `[missing]`, fresh → `[ok]`. **(Q5 — anchor corrected)
    RED-first:** pre-fix, the report list contains **NO `repos/demo:AGENTS.md` line at all** (the marker-less
    repo is dropped by `_consumer_repos_for_root:49`, which writes only a stderr `[skip]` that never enters
    the report list; `_doctor_guardrail_pair` itself never emits `[skip]`).
  - **AC-9(d) sabotage:** restore the in-repo `.dadaia/agentic/` marker requirement in
    `_consumer_repos_for_root` ⇒ AC-6 fan-out-fires test FAILS (nothing written) → revert.
  - **(e/Q5 — corrected) AC-9 sabotage:** restore the in-repo-marker filter in `_consumer_repos_for_root` ⇒
    AC-7 `[drift]` test FAILS (the `repos/demo:AGENTS.md` line disappears from the report list) → revert.
    Capture both commands + failing tests on this line.
  - **existing-test fate ledger (Q3 — file-enumerated):** INVERT the marker fixture —
    `tests/unit/features/public/test_workspace_guardrail_pair.py` and
    `tests/integration/test_public_doctor_parity.py`'s `test_doctor_emits_four_labels_with_one_consumer`:
    the marker-bearing consumer fixture becomes a **registry-listed marker-less consumer** (keep the
    `[ok]`×4 + self-repo-skip + hash-compare assertions); DELETE only a case with no invertible assertion.
    Grep `tests/` for `_consumer_repos_for_root` + `.dadaia/agentic` marker usages and repoint.
  - **AC-11 ledger** — EDITED: `_consumer_repos_for_root` (reimplemented, kept by name), `_install_guardrail_pair`
    (fires via registry + A5 `[updated]` line), `_doctor_guardrail_pair` (flags stale/missing). No
    `specs/backlog/**` staged.

## W5 — FR5 per-profile sandboxed E2E

- [x] T-58-50 Per-profile E2E extending `test_public_pipeline.py`. Checklist:
  - **Evidence:** EXTENDED `tests/e2e/features/test_public_pipeline.py` — new `TestPerProfileInit`
    class with 4 E2Es (`test_claude_only_profile`, `test_codex_only_profile`, `test_pi_only_profile`,
    `test_default_no_flag_scaffolds_all_four`). Scaffold is **in-process (Q4)** via
    `CliRunner.invoke(cli_app, ["init","--harness",X,"--workspace",ws])` (NOT a subprocess); the
    root conftest `_no_real_venv_in_tests` autouse fakes `ensure_workspace_venv` so real-CLI init
    builds no venv. Module-scoped shared fixture `_staged_pi_files` stages ONCE and supplies the
    reused `.pi/` expectation baseline (each init re-stages internally, 0.12s — measured, negligible).
    Each E2E asserts the EXACT structure (chosen-harness dirs present / un-chosen absent + ctx-inject
    hook / codex wrappers / `.pi/` file-set match) + persisted `harness_profile.json` == the requested
    set + a profile-scoped **green** `public doctor` on BOTH Q7 surfaces (report-list blocker-free via
    `mgr.doctor(ws)` AND real `dadaia public doctor` CLI **exit 0** via `monkeypatch.chdir(ws)`).
    **Batch wall-time:** the 4-profile matrix = **~6.0s test-exec (~7.9s incl. interpreter startup)** —
    well under the ~30s budget; `tmp_path` isolation (no `.dadaia/` inside any repo), `-p no:cacheprovider`.
  - **Boundary completion 1 (in-spirit FR3 "doctor scopes runtime expectations", W3-flagged → W5):**
    EDITED `dadaia_workspace/infrastructure/public_assets.py#doctor()` — the `runtime_expectations`
    projection loop (`_CLAUDE_DIRS` → `claude:<dir>/*`) stayed UNCONDITIONAL after W3 (only the inline
    `_compare` block was scoped). Now the `profile_harnesses`/`active` resolution is hoisted ABOVE the
    loop and a one-line guard `if not claude_active and label.startswith("claude:"): continue` scopes
    the `claude:*` projection lines to `claude in profile`. The shared `agents:skills/*`, the AGENTS.md
    guardrail pairs, and the harness-independent `dadaia:scripts/*` lines stay unconditional; A3 is
    unaffected (a physically-present out-of-profile `.claude/` still emits the inline `[warn]`).
    **RED-first capture:** neutralising the guard (`if False and …`) made the 4 new profile-doctor
    unit tests FAIL — codex-only & pi-only each emit **×40 `[missing] claude:rules|skills|commands|
    agents|workflows/*`** lines and `dadaia public doctor` exits 1; restoring the guard → GREEN.
    **Byte-lock preserved:** claude ∈ all-four ⇒ the loop runs fully on the absent-profile path;
    `test_absent_profile_doctor_byte_equals_all_four_golden` + the W1 doctor golden replay byte-identical.
    NEW unit tests in `tests/unit/infrastructure/test_public_assets_profile.py`:
    `test_codex_only_profile_doctor_is_green`, `test_codex_only_cli_doctor_exits_zero`,
    `test_pi_only_profile_doctor_is_green`, `test_pi_only_cli_doctor_exits_zero`,
    `test_codex_only_out_of_profile_claude_on_disk_is_not_silent` (A3 symmetry).
  - **Boundary 2 (W2 scripts — NOT scoped, per FR3):** a pi-only per-target subset init installs no
    chokepoint scripts (existing rule installs them only for `{all,claude,codex}` targets). FR3 keeps the
    scripts doctor check **UNCONDITIONAL** (chokepoints are harness-independent), so scoping them would
    contradict FR3 — instead the pi-only E2E (and unit fixture) **scaffold the scripts** via the real
    production `_install_scripts` (exactly what `dadaia public install` runs). Recorded boundary; no
    production install-path change.
  - **(Q6) AC-9(f) sabotage (captured → reverted):** applied the AC-9(b) init sabotage
    (`chosen = L1_ENTRY_HARNESSES` in `WorkspaceService.init` → always all-four); command
    `pytest tests/e2e/features/test_public_pipeline.py::TestPerProfileInit::test_claude_only_profile`
    ⇒ **FAILED** at `assert not (ws/".codex").exists()` ("codex must NOT be scaffolded for a claude
    profile") — the discriminating "NO `.codex/`, NO `.pi/`" anchor. Reverted → 4/4 green.
  - **AC-11 ledger — file-enumerated fates:** NEW/EXTENDED —
    `tests/e2e/features/test_public_pipeline.py` (+4 E2Es; `TestPerProfileInit` + `_run_init`/
    `_persisted_profile`/`_assert_profile_doctor_green`/`_staged_pi_files` helpers; imports `cli.main.app`,
    `CliRunner`, `pytest`); `tests/unit/infrastructure/test_public_assets_profile.py` (+5 tests; `_install_codex_only_tree`/
    `_install_pi_only_tree`/`_scaffold_chokepoint_scripts`/`_mentions_claude` helpers). EDITED (boundary-1
    completion) — `dadaia_workspace/infrastructure/public_assets.py#doctor()` (hoisted `active`, one-line
    `claude:*` scope). SURVIVE untouched — `runtime_expectations`/`_runtime_expectations` signatures (their
    consumers `test_public_assets.py`, `test_doctor_projected_drift.py`, `test_public_doctor_parity.py`
    unchanged); the W1 install/doctor goldens replay byte-identical. **Gates:** ruff format --check clean
    (795 files); ruff check --no-cache clean; mypy --strict clean (309 files); lint-imports --no-cache
    **8 kept / 0 broken** (ignore-cap unchanged — the doctor edit adds no import edge); full unpiped pytest
    **4566 passed / 17 skipped / 0 failed** (exit 0). No `specs/backlog/**` staged.
  - Extend `tests/e2e/features/test_public_pipeline.py` (or a sibling module reusing its helpers +
    `FileSystemPublicAssetManager`) with **claude-only / codex-only / pi-only / all** E2Es. **(Q4 — pinned
    mechanism)** scaffold **in-process** via `CliRunner.invoke(app, ["init","--harness",X,"--workspace",tmp])`
    — **NOT a subprocess** (no `shutil.which('dadaia')` console-script resolution, keeps width-independent
    stderr). **Stage the asset set ONCE via a shared fixture reused ×4** profiles (avoid re-staging ×4).
    **Wall-time budget:** the 4-profile matrix stays under ~30s combined; `tmp_path` isolation from the repo
    (no `.dadaia/` inside a repo) + `pytest -p no:cacheprovider`. Assert the EXACT default structure per FR5:
    - claude-only: `.claude/` (agents/skills/rules) + ctx-inject hook in `settings.json`; NO `.codex/`, NO
      `.pi/`; profile-scoped `public doctor` green.
    - codex-only: `.codex/` (agents/config/rules/hooks.json) + `.dadaia/hooks/codex-*`; NO `.claude/`
      agents, NO `.pi/`; green doctor.
    - pi-only: `.pi/` post-trust projection; NO `.claude/` agents, NO `.codex/`; green doctor.
    - all: the existing all-harness structure (retained), default (no `--harness`) still all-four; green
      doctor.
  - Assert `.dadaia/states/harness_profile.json` matches the requested set per profile.
  - **(Q7) "green" is mechanical:** report list has no `[missing]`/`[drift]`/`[fail]` for out-of-profile
    harnesses AND `dadaia public doctor` CLI exit 0.
  - **Tests — AC-8** four profiles, **in-process CLI** scaffold, structure + profile + profile-scoped green
    `public doctor`. Extends (does not duplicate) the all-harness pipeline test.
  - **(Q6) AC-9(f) sabotage:** with the AC-9(b) init sabotage active (`WorkspaceService.init` ignores the
    harness set → always all-four), the **claude-only E2E FAILS** (its "NO `.codex/`, NO `.pi/`" assertions
    break) — the discriminating anchor for this wave. Capture the command + failing E2E on this line, then
    revert.
  - **AC-11 ledger** — NEW/EXTENDED: the four per-profile E2Es on `test_public_pipeline.py`. No
    `specs/backlog/**` staged.

## W6 — gates + ship

- [x] T-58-60 Full local gates (AC-10) + self-hosting reconcile (AC-12), then ship. **Gate evidence
  (2026-07-04, tree = 6e16a98b):** unpiped full pytest **4566 passed / 17 skipped, exit 0**; ruff
  format --check clean (795 files); ruff check --no-cache clean; mypy --strict clean (309 files);
  lint-imports --no-cache **8 kept / 0 broken** + ignore-cap 4/4 UNCHANGED (A1 held: no new
  features→infra / infra→features edge); `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0;
  frozen v0.1.50 no-steal suite **zero-diff**; no `public/**` asset content changed; no
  `specs/backlog/**` staged (both anchors survive → CLOSURE archival). **AC-12 reconcile (Ruling M,
  doctor-before-install, executed + recorded):** stage exit 0 → pre-install doctor surfaced the FULL
  consumer write set — 6 consumer repos (sample-provisioner, sample-project, sample-bots,
  sample-consumer, sample-explorer, sample-games), each `[drift]` AGENTS.md + `[missing]` CLAUDE.md,
  12 targets total, self-repo absent — PM reviewed: all lib-owned root law files, no nested/operator
  files → install restored each divergent root with the DISTINCT `[updated]` line + created the
  CLAUDE.md bridges, self-repo `[skip]` (self-projection) → confirming doctor exit 0, **0
  drift/missing, [ok] public-privacy**. Every consumer overwrite appeared in the pre-install surface —
  no silent clobber. **QA ship gate: APPROVE, zero blockers** (AC-1..8 traced + spot-run green;
  golden-first verified by commit order; 9/9 AC-9 evidences specific; slop check clean; AC-12 claims
  verified against the tree) — handoff `2026-07-04T124902Z-qa-engineer-v0158-ship-gate.handoff.json`.
  Ship steps (security push gate keyed to pushed sha; push; CI watch; PR; merge) executed after this
  flip. Checklist:
  - **Unpiped** `pytest` (real exit) — full suite green; `ruff format --check`; `ruff check --no-cache`;
    `mypy --strict dadaia_workspace`.
  - `lint-imports --no-cache` → **`8 kept, 0 broken`**; ignore-cap UNCHANGED — `core/harness_registry.py` is
    a `core` leaf importing only stdlib, **and (A1) the persistence seam adds NO new `features→infrastructure`
    edge and NO `infrastructure→features` edge** — verify; if any new edge is unavoidable, STOP and document
    (would fail AC-10).
  - `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0.
  - **Self-hosting reconcile (AC-12 / A6/Ruling M — DOCTOR-BEFORE-INSTALL, PM binding):** run in this order —
    `dadaia public stage` → **`dadaia public doctor`** (enumerates every `repos/<slug>:AGENTS.md`
    `[drift]`/`[missing]` write target across the **(A7) alive OR dead on-disk context repos minus the
    self-repo `dadaia-workspace`** — ~12 real repos) → **PM reviews the surfaced consumer write set in-session
    and RECORDS it in the ship evidence** (an in-session checkpoint, NOT an operator halt — flow never stops)
    → **`dadaia public install --target all`** → confirming `dadaia public doctor` (`[ok] public-privacy`,
    exit 0). Confirm the v0.1.50 frozen no-steal suite is **zero-diff**. Confirm **every consumer overwrite
    appeared in the pre-install surface** (a divergent overwrite emits the distinct `[updated]` line, A5), so
    no consumer repo is silently clobbered. Instance files never hand-edited — reconcile only via
    stage/doctor/install/doctor. *(PE surfaces these + the git commands to PM/operator or requests
    devops-engineer; PE runs no shell.)*
  - Confirm **no `public/**` asset content changed** (the release changes package code, not projected
    assets) — if the AGENTS.md law text or any `public/**` file did change, enumerate it and re-verify
    `[ok] public-privacy`.
  - QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job
    green**; PR; merge. No dead anchor this release → **no SHIP-time backlog archival** (both anchors survive
    → CLOSURE). Verify no W1–W5 commit staged `specs/backlog`.

## W7 — closure (CLOSURE phase)

- [ ] T-58-70 CLOSURE.md + memory truth + disposition + archive. Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write `CLOSURE.md` (Summary, Tasks completed w/ SHAs, Validations
    triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive decision).
  - **MEMORY (§SPEC 8):** `public-asset-distribution.md` → profile-aware install/doctor + registry-based
    consumer fan-out + doctor flagging (primary); `workspace-init.md` → `init --harness` + persisted
    profile; `harness-claude-code.md` / `harness-codex.md` / `harness-pi.md` → isolation now enforced at
    init; `multi-platform-parity.md` → typed L1 registry note; `architecture.md` → module map gains
    `core/harness_registry.py` + profile-aware install/doctor + registry-based detection; `tech-stack.md` →
    assess pointer to the registry (roster wording canonical); `quality-assurance.md` → assess
    install-golden + real-CLI-E2E note. Regen `catalog.json` + `index.md` ONLY if `tldr`/`summary`/`area`
    change — **keep the regenerated `tldr` within the established length cap** so the catalog regen +
    `dadaia specs doctor` at W7 stays clean. `release_origin` → v0.1.58 on each edited atom.
  - **Backlog return (Ruling F)**: file `workflow-spawn-entry-harness-autodefault` (route through PM
    curation). Record in the CLOSURE `## Backlog returns`.
  - **Dispositions**: archive `harness-isolation-profiles` + `consumer-agents-md-fanout-redesign` →
    `specs/_archive/v0.1.58/consumed-backlog/` + `consumed_backlog.json`; terminal status
    `DELIVERED — v0.1.58` (both anchors survive → CLOSURE archival; no SHIP-time archival). Record all in
    the CLOSURE `## Dispositions` table.
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.58 → specs/_archive/releases/`
    (devops/operator); set `ACTIVE.md` → next release or `release: none`; mark candidates R10 row
    **SHIPPED — v0.1.58**.
