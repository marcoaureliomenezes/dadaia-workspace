# PLAN — v0.1.58 — Harness & Projection Distribution

**Status:** Aprovado

Seven waves. **FR1 (the typed harness registry) lands FIRST** — it is the single identity source FR2/FR3
consume, captured golden-first (install/target-resolution behaviour byte-locked before the refactor).
`infrastructure/public_assets.py` + `public_assets_common.py` are shared across W1/W3/W4 →
those waves are **sequential** (no parallel `[-]`). FR4 (`workspace_guardrail.py`) is a distinct file but
its doctor path is reached through `public_assets.doctor()`, so it stays sequential too.

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on
  the picked set (report emitted); ten operator-unavailable rulings recorded (§9); `Aprovado` after dual
  review; definition commit. Owner: product-engineer (orchestrated).

- **W1 — FR1 typed core harness registry (golden-first, the identity seam).**
  1. **Golden capture FIRST.** Add a golden test capturing `public_assets.install()` per-target resolution
     for each `--target` in `{all, agents, claude, codex, pi}` (the produced `installed` list,
     path-normalized per v0.1.55) + the panel runtime-validation accept/reject outputs
     (`api_workflows`/`api_agents` for `claude`/`codex`/`pi`/bogus) **+ (Q2/A4) `public_assets.doctor()`'s
     full report list on a fully-installed all-four (no-profile) tree** (path/version-normalized, clock
     frozen). Commit BEFORE any refactor — the AC-1 behaviour lock (the doctor golden is the FR3
     absent-profile back-compat lock, captured now because W1 precedes W3).
  2. **New `core/harness_registry.py`.** `L1_ENTRY_HARNESSES`/`L2_WORKER_HARNESSES`, capability predicates
     (`is_l1`/`is_l2`/`can_be_workflow_worker`), `PROJECTION_TARGETS`/`INSTALL_TARGETS` (the
     `_VALID_TARGETS` single source moves here; `public_assets_common` re-exports), and
     `parse_harness_set(value)`. Pure `core` leaf, stdlib only, import-linter clean.
  3. **Consume in the roster-encoding literals — L1 AND L2 (Ruling B + A2/Ruling K).** Repoint the 4 L1 sites
     `api_workflows.py:70`, `api_agents.py:161`, `public_assets_common.py:20` (`_VALID_TARGETS`),
     `public_assets.py:275` + the install target list, **AND (A2) the 3 L2 `_LAYER2_HARNESSES` sites**
     (`policy_doctor.py:77`, `policy_resolver.py:136`, `json_workflow_model_policy_store.py:54`) to
     `harness_registry.L2_WORKER_HARNESSES`. Add a **contract test**
     `frozenset(L2_WORKER_HARNESSES) == frozenset(harness_models.harnesses())` — order-independent set
     agreement (R1): `harnesses()` is PI-first, the registry constant keeps canonical order
     `("codex", "pi")` — reconciling the derived 4th site `model_profiles.py:112` (NOT repointed).
     Leave the documented residual (readers/panel/CSS/JS/schema).
  - Tests: AC-1 install/panel goldens byte-identical post-refactor + doctor golden committed; AC-2
    registry-is-single-source (predicates + `parse_harness_set` + grep that the 7 literals are gone + L2
    contract test). AC-9(a) L1 sabotage + **(a′/A2) L2-site sabotage**. AC-11 **file-enumerated** ledger
    (Q3): `test_api_golden.py` + `api_golden_v0155.json` SURVIVE byte-identical INVARIANT (a byte diff is
    adjudicated, never regenerated), `test_api_workflows.py`/`test_api_agents.py` SURVIVE,
    `test_public_assets.py` `_VALID_TARGETS` SURVIVE via re-export; 7 centralized sites + residual enumerated.
    NO `specs/backlog`.

- **W2 — FR2 `init --harness` profiles + persisted profile + harness-aware scaffold.**
  0. **(A1) Persistence seam — ports-and-adapters, layer-pinned.** Pure typed `HarnessProfile` model
     (`schema_version` + `harnesses` tuple) + `parse_harness_set` in **`core`** (NO I/O); the JSON read/write
     **ADAPTER in `infrastructure/`** mirroring `json_context_store.py`; the init-time WRITE in
     `features/workspace/service.py` via an injected `core.protocols` port OR inline like `_init_json_file`.
     **Forbid** a new `features→infrastructure` edge (ignore-cap 9 UNCHANGED) and any `infrastructure→features`
     edge. (The "core/models/state helper" phrasing is deleted from the write-set below.)
  1. **CLI**: add `--harness <set>` to `cli/commands/init.py` (parsed via `parse_harness_set`; bad value →
     Click `BadParameter`, width-independent stderr).
  2. **Harness-aware `WorkspaceService.init`**: thread the chosen set; create only the chosen harnesses'
     dirs + hooks (`_configure_hook` runs only when `claude` in set); write
     `.dadaia/states/harness_profile.json` via the infra adapter (idempotent).
  3. **Install derivation**: `init` installs the profile set (per-target or profile-aware install), never
     `target="all"` for a subset.
  - Tests: AC-3 claude-only / codex,pi / default scaffolds (RED-first: pre-fix always all-four) + bad-value
    stderr; AC-4 persisted profile + idempotent; a **layer-boundary assertion** (lint-imports 8 kept/0 broken,
    ignore-cap unchanged — no new features→infra edge). AC-9(b) sabotage. AC-11 ledger. NO `specs/backlog`.

- **W3 — FR3 profile-aware `public install`-all + `public doctor`.**
  1. **Install-all reads the profile** (`public_assets.install`, via the A1 infra adapter): profile set when
     the profile file exists; absent ⇒ all-four; explicit `--target X` overrides.
  2. **Doctor scopes runtime expectations** (`public_assets.doctor`): the inline `_compare` block — claude
     settings only when `claude`; codex hooks/config/rules/wrappers only when `codex`; `.pi/` only when `pi`.
     **(Q1) The codex-parity block** — `check_codex_drift` (D-CX-1..10, emits the `[missing] codex:agents/*.toml`
     ×12) **+ `codex_trust_boundary_info`** — ALSO gates on `codex in profile` (absent ⇒ run). Stay
     unconditional: `check_codex_rule_corpus_reachable` (safe early-return), `classify_workflows`,
     `check_agent_skill_refs`, `check_memory_phase_single_source`, agents/`.agents` skills, AGENTS.md pair,
     chokepoint scripts, `_check_public_privacy`, git-dirty. **(A3)** an out-of-profile runtime dir that
     EXISTS on disk emits a non-silent `[warn]`/`[drift]` line — never zero lines.
  - Tests: AC-5 claude-only install writes only claude + `public doctor` green with **NO `[missing]
    codex:agents/*.toml (D-CX-1)`** (RED-first: pre-fix reports `[missing]`); **(Q2/A4) absent-profile doctor
    asserts BYTE-EQUALITY vs the W1 all-four doctor golden**; **(A3) RED-first: claude-only profile + stale
    `.codex/hooks.json` on disk ⇒ non-silent** (not green); explicit `--target codex` override. AC-9(c) +
    **(c′/Q1) + (c″/A3)** sabotages. AC-11 **file-enumerated** ledger (Q3): `test_public_doctor_parity.py`,
    `test_doctor_projected_drift.py`, `test_public_assets.py` doctor cases SURVIVE byte-identical on the
    absent-profile path (proven by the Q2 golden). NO `specs/backlog`.

- **W4 — FR4 consumer `AGENTS.md` fan-out redesign.**
  1. **Reimplement `_consumer_repos_for_root` (KEPT BY NAME, Ruling G)**: read
     `.dadaia/states/spec_contexts.json`, derive `repos/<repo_slug>/` for each on-disk context (alive OR
     dead, Ruling H), drop the in-repo marker; skip absent repos silently; retain `_is_self_repo` skip.
  2. **Fan-out fires**: `_install_guardrail_pair` writes the workspace-law pair to each detected on-disk
     consumer repo (hash-compare). Tri-copy untouched (Ruling I). **(A5/Ruling L) consumer root `AGENTS.md`
     is lib-owned**: a divergent root copy is restored to canonical, and `_write_pair` emits a DISTINCT
     `[updated] ... (overwrote divergent workspace-law copy)` line (never silent `[ok]`); nested subtree
     `AGENTS.md` is never touched.
  3. **Doctor flags stale/missing (Ruling J)**: `_doctor_guardrail_pair` iterates the same registry-derived
     repos, emits `[drift]`/`[missing]`/`[ok]`, never `[skip]` for a real consumer repo.
  - Tests: AC-6 fan-out fires via registry (RED-first: pre-fix marker-based writes nothing) + absent-repo
    skip + self-repo skip + tri-copy NOT written + **(A5) divergent-root restored w/ `[updated]` line +
    nested subtree untouched**; AC-7 doctor `[drift]`/`[missing]`/`[ok]` — **(Q5 anchor corrected) RED-first:
    pre-fix the report list has NO `repos/demo:AGENTS.md` line** (the `[skip]` is a stderr-only line from
    `_consumer_repos_for_root:49`, never in the report list). AC-9(d) + **(e/Q5 corrected — restore the
    in-repo-marker filter in `_consumer_repos_for_root`)** sabotage. AC-11 **file-enumerated** ledger (Q3):
    `test_workspace_guardrail_pair.py` + `test_public_doctor_parity.py`'s
    `test_doctor_emits_four_labels_with_one_consumer` **INVERT** the marker fixture → a registry-listed
    marker-less consumer (keep `[ok]`×4). NO `specs/backlog`.

- **W5 — FR5 per-profile sandboxed E2E.**
  1. Extend `tests/e2e/features/test_public_pipeline.py` (or a sibling reusing its helpers +
     `FileSystemPublicAssetManager`) with claude-only / codex-only / pi-only / all E2Es. **(Q4) Pinned
     mechanism**: scaffold **in-process** via `CliRunner.invoke(app, ["init","--harness",X,"--workspace",tmp])`
     (NO subprocess); **stage the asset set ONCE via a shared fixture reused ×4**; ~30s combined wall-time
     budget; `tmp_path` isolation + `pytest -p no:cacheprovider`. Assert the EXACT default structure +
     persisted profile + profile-scoped **green** `public doctor` (Q7 definition).
  - Tests: AC-8 four profiles, in-process CLI scaffold, structure + profile + doctor. **(Q6) AC-9(f)**: with
    the AC-9(b) init sabotage active, the claude-only E2E FAILS (its NO-`.codex`/NO-`.pi` assertions) → the
    discriminating anchor for this wave (captured on the T-58-50 line, then reverted). AC-11 ledger. NO
    `specs/backlog`.

- **W6 — gates + ship.** Full local gates (AC-10): unpiped `pytest` + `ruff format --check` + `ruff check
  --no-cache` + `mypy --strict` + `lint-imports --no-cache` (8 kept / 0 broken; ignore-cap unchanged —
  `core/harness_registry.py` adds no edge; the A1 seam adds no features→infra edge) + `dadaia specs doctor` +
  `dadaia backlog doctor`. **Self-hosting reconcile (AC-12 / A6/Ruling M — DOCTOR-BEFORE-INSTALL):**
  `dadaia public stage` → **`dadaia public doctor`** (enumerates every `repos/<slug>:AGENTS.md`
  `[drift]`/`[missing]` write target across the **(A7) alive OR dead on-disk context repos minus the
  self-repo** — ~12 real repos) → **PM reviews the surfaced consumer write set in-session and records it in
  the ship evidence** (an in-session checkpoint, NOT an operator halt) → **`dadaia public install --target
  all`** →
  confirming `dadaia public doctor` (`[ok] public-privacy`). Confirm the v0.1.50 frozen no-steal suite is
  **zero-diff**; confirm every consumer overwrite appeared in the pre-install surface (a divergent overwrite
  emits the distinct `[updated]` line, A5). QA ship-gate; security push-gate keyed to the pushed sha; push;
  **watch CI until every job green**; PR; merge. *(PE runs no shell — surfaces the `stage/doctor/install/doctor`
  + git commands to PM/operator or requests devops-engineer.)*

- **W7 — closure (CLOSURE phase).** `ACTIVE.md` phase = `CLOSURE`; CLOSURE.md (Summary, Tasks + SHAs,
  Validations triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive). MEMORY (§SPEC 8):
  `public-asset-distribution.md` (profile-aware install/doctor + registry-based consumer fan-out + doctor
  flagging); `workspace-init.md` (`init --harness` + persisted profile); `harness-claude-code.md` /
  `harness-codex.md` / `harness-pi.md` (isolation now enforced at init); `multi-platform-parity.md` (typed
  L1 registry note); `architecture.md` (module map gains `core/harness_registry.py` + profile-aware
  install/doctor + registry-based detection); `tech-stack.md` (assess pointer to the registry, roster
  wording canonical); `quality-assurance.md` (assess install-golden + real-CLI-E2E note). Regen
  `catalog.json` + `index.md` only if `tldr`/`summary`/`area` change — keep regenerated `tldr` within the
  length cap. `release_origin` → v0.1.58 on each edited atom. **Backlog return (Ruling F)**: file
  `workflow-spawn-entry-harness-autodefault` (route through PM curation). **Dispositions**: archive
  `harness-isolation-profiles` + `consumer-agents-md-fanout-redesign` →
  `specs/_archive/v0.1.58/consumed-backlog/` + `consumed_backlog.json` (`DELIVERED — v0.1.58`; both anchors
  survive → CLOSURE archival, no SHIP-time archival). `dadaia specs doctor` clean; request `git mv
  specs/releases/v0.1.58 → specs/_archive/releases/` (devops/operator); set `ACTIVE.md` → next release or
  `release: none`; mark candidates R10 row **SHIPPED — v0.1.58**.

## Write sets (disjoint per wave; shared files force sequential order)

| Wave | Files |
|---|---|
| W1 | NEW `dadaia_workspace/core/harness_registry.py`; `infrastructure/public_assets_common.py` (`_VALID_TARGETS` → registry re-export); `infrastructure/public_assets.py` (target list → registry); `features/panel/views/api_workflows.py` + `api_agents.py` (runtime validation → registry); **(A2) `features/lifecycle/policy_doctor.py:77` + `policy_resolver.py:136` + `infrastructure/json_workflow_model_policy_store.py:54` (`_LAYER2_HARNESSES` → `L2_WORKER_HARNESSES`)**; NEW golden test `tests/unit/infrastructure/test_install_target_goldens.py` + install/panel/**doctor** goldens; `tests/unit/core/test_harness_registry.py` (incl. the L2⇔`harness_models.harnesses()` contract test) |
| W2 | **(A1) NEW `core/models/harness_profile.py` (`HarnessProfile` model) + `parse_harness_set` (in `core/harness_registry.py`, NO IO); NEW `core/protocols/harness_profile_store.py` port; NEW `infrastructure/json_harness_profile_store.py` adapter (mirrors `json_context_store.py`)**; `dadaia_workspace/cli/commands/init.py` (`--harness`); `features/workspace/service.py` (harness-aware `init` + profile write via port/inline + hook gating); FR2 tests (`tests/unit/cli/test_init_harness.py`, `tests/unit/features/workspace/test_service_harness_profile.py`) — **NO `core/models`/state-file helper doing IO (A1)** |
| W3 | `infrastructure/public_assets.py` (`install` profile-read + `doctor` profile-scoped expectations incl. **Q1 codex-parity gating + A3 out-of-profile non-silent**); consumes the W2 `json_harness_profile_store` adapter (read side); FR3 tests (`tests/unit/infrastructure/test_public_assets_profile.py`) + the Q2/A4 doctor byte-golden assertion |
| W4 | `infrastructure/workspace_guardrail.py` (`_consumer_repos_for_root` reimplement + `_doctor_guardrail_pair` flagging); FR4 tests (`tests/unit/infrastructure/test_consumer_fanout.py`) |
| W5 | `tests/e2e/features/test_public_pipeline.py` (+ optional sibling module); FR5 E2E only |
| W6 | (gates + `public stage/install/doctor`; self-hosting reconcile; no `specs/**` change) |
| W7 | `specs/releases/v0.1.58/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.58/consumed-backlog/` + `ACTIVE.md` |

**`public_assets.py` shared W1 (target list) + W3 (install/doctor profile)** — sequential; disjoint symbols,
one file. **`public_assets_common.py` W1 only (`_VALID_TARGETS` → registry re-export).** **The A1 profile
adapter (`infrastructure/json_harness_profile_store.py`) is NEW in W2, read by W3** — sequential.
**`features/workspace/service.py` W2 only.** **The 3 L2 `_LAYER2_HARNESSES` sites (policy_doctor.py,
policy_resolver.py, json_workflow_model_policy_store.py) W1 only.** **`workspace_guardrail.py` W4 only.**
**No parallel `[-]`.**

## Test strategy

- **Golden-first (FR1, the spine + Q2/A4 doctor lock).** Capture + commit install/target-resolution +
  panel-validation goldens **and the `public_assets.doctor()` all-four (no-profile) report-list golden**
  under `FileSystemPublicAssetManager` + `tmp_path` BEFORE the registry refactor (doctor golden also before
  the FR3 refactor); prove byte-identity after (fix-the-consumer-never-the-golden). Platform/version-invariant
  normalization (v0.1.55) on every path-bearing golden, clock frozen.
- **RED-first for new behaviour (FR2/FR3/FR4/FR5).** Each new capability's test asserts the post-fix
  behaviour and is shown to FAIL against the pre-fix tree (init always-all-four; doctor `[missing]`
  codex/pi + **(Q1) `[missing] codex:agents/*.toml (D-CX-1)`** on a claude-only tree; **(Q5) fan-out report
  list has NO `repos/demo:AGENTS.md` line** pre-fix; **(A3) stale out-of-profile `.codex/` reads green**
  pre-fix).
- **Width-independent stderr asserts.** The `init --harness zzz` error is asserted via `result.stderr`
  substring + `exit_code == 2` + empty `result.stdout`; **no `mix_stderr` kwarg** on `CliRunner` (removed in
  Click 8.2, TypeErrors on the installed 8.4.1 — the v0.1.57 QA-atom law).
- **Platform-invariant golden normalization** on all path-bearing goldens (install AND doctor) (`.dadaia/`/`repos/`
  refs → placeholders; `os.sep` normalized) — the 3-OS CI matrix runs these.
- **Profile back-compat = byte-golden (Q2/A4).** The absent-profile doctor path asserts **byte-equality vs
  the captured all-four doctor golden**, not "all-four checked" prose — this is the release's hardest target
  (every pre-v0.1.58 workspace rides on it).
- **AC-9 mutation-sanity per new test** (a, a′, b, c, c′, c″, d, e, f): one-line sabotage ⇒ FAIL, captured on
  the task line, reverted. Includes the (a′) L2-site, (c′) codex-drift-unconditional, (c″) out-of-profile
  silence, and (f) E2E-under-init-sabotage checks.
- **AC-11 surviving/dead ledger per wave — FILE-ENUMERATED (Q3)**; greps include `tests/` + textual/docstring
  refs; the FR1 ledger records the 7 centralized sites (4 L1 + 3 L2) vs residual + the `model_profiles.py:112`
  contract-test reconciliation; the named suites `test_api_golden.py`/`api_golden_v0155.json` (INVARIANT),
  `test_public_doctor_parity.py`, `test_doctor_projected_drift.py`, `test_workspace_guardrail_pair.py`.
- **Frozen suite:** the v0.1.50 no-steal lease/gate suite is untouched (this release never enters
  `spec_context`/lease/gate) — confirm zero-diff. If any init/scaffolding test is found to touch a
  gate-adjacent fixture, flag adjudication in the wave ledger.
- **E2E (FR5) — in-process (Q4).** the four per-profile E2Es scaffold **in-process via `CliRunner.invoke`**
  (NOT a subprocess), stage the asset set ONCE via a shared fixture reused ×4 (~30s budget, `tmp_path`
  isolation, `-p no:cacheprovider`), assert exact structure + persisted profile + profile-scoped green
  `public doctor`; they extend `test_public_pipeline.py`, not duplicate it. **(Q6)** the claude-only E2E is
  discriminating — it FAILS under the AC-9(b) init sabotage.
- Full **unpiped** `pytest` + ruff + `mypy --strict` + `lint-imports --no-cache` + `specs doctor` +
  `backlog doctor` + `public doctor` locally before push (AC-10).

## Platform seam note (3-OS CI)

Any filesystem/path work (profile file read/write, install path assertions, consumer-repo detection)
respects the platform seam: paths via `pathlib`, `os.sep` normalization in goldens, `shutil.which` for
console scripts if invoked, and the `core/platform.py` singleton for any OS branch. The profile JSON is
stdlib `json`. No symlink work is introduced. The E2E `tmp_path` scaffolds are OS-agnostic.

## Rollback

Single feature branch `feature/v0.1.58` (base v0.1.57 closure). FR1 is behind committed goldens (revert =
restore the literals). FR2 adds a flag + a state file + harness-gated dir/hook creation (revert restores
all-four init). FR3 makes install/doctor profile-aware with an absent-profile all-four fallback (revert =
unconditional checks). FR4 reimplements one function + one doctor path (revert = restore marker-based
detection). FR5 is test-only. No data migration; the profile file is additive-optional (absent ⇒ all-four).
The only irreversible-ish step is `public install` on the live instance (re-run `stage`/`install`/`doctor`
to reconcile). The CLOSURE dispositions are recoverable by reverting the closure commit.
