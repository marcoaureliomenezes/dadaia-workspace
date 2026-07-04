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

- [ ] T-58-11 Add `core/harness_registry.py` and consume it in the roster-encoding literals. Checklist:
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

- [ ] T-58-20 `dadaia init --harness <set>` + harness-aware `WorkspaceService.init` + persisted profile.
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
    claude-only test FAILS → revert. Capture command + failing test on this line.
  - **existing-test fate ledger (Q3):** SURVIVE/EXTEND — the existing `WorkspaceService.init` /
    `tests/unit/features/workspace/test_service.py` tests (default `--harness` omitted must still yield
    all-four; assert unchanged); any `init` E2E in the all-harness pipeline (unchanged default path).
  - **AC-11 ledger** — NEW (A1): `core/models/harness_profile.py`, `core/protocols/harness_profile_store.py`,
    `infrastructure/json_harness_profile_store.py`, `parse_harness_set` (in `harness_registry.py`) + FR2
    tests; EDITED: `init.py` (`--harness`), `service.py` (harness-aware init + profile write via port + hook
    gating). No `specs/backlog/**` staged.

## W3 — FR3 profile-aware `public install`-all + `public doctor`

- [ ] T-58-30 Profile-aware install-all + profile-scoped doctor. Checklist:
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

- [ ] T-58-40 Registry-based consumer detection + doctor flagging. Checklist:
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

- [ ] T-58-50 Per-profile E2E extending `test_public_pipeline.py`. Checklist:
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

- [ ] T-58-60 Full local gates (AC-10) + self-hosting reconcile (AC-12), then ship. Checklist:
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
