# TASKS — v0.1.60 — Capability Tail (plugin packs + Layer-1 model-tier efficiency)

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. Shared file `public_assets.py` is touched only in W2 (after the
W1 adapter lands) — sequential, one owner, no parallel `[-]`. Every implementation-wave task: **NO `specs/backlog/**`
paths staged** (dead/surviving anchors dispositioned at CLOSURE — T-60-70). Every move/repoint grep **includes `tests/`
AND non-import textual references** (docstrings/comments). AC-11 mutation-sanity: each new test is sabotaged → shown to
FAIL → reverted, captured on the task line. **FR1/FR2 land FIRST** (golden-first) — the machinery FR3–FR8 build on.

## W0 — definition

- [x] T-60-01 SPEC/PLAN/TASKS authored from the 2026-07-04 **code read** (not a dossier restatement): `_COPY_DIRS`
  already stages `"plugins"` but the route is dead-on-arrival (no projection/ledger); the registry `Tier` already has
  `fast`+`plugin` (only unassigned); the "mechanical sub-task classes" are deterministic CLI (no model) and Layer-1 has
  no sub-task tiering (only whole-persona `model:`); the efficiency-audit rubric exists but has no recurring trigger/
  marker; `tier: 1/2/3` frontmatter vs registry `Tier` is a divergent-naming inconsistency; constitution §14 already
  forward-compatible. Mandatory release-definition grill on the picked set (report emitted). **DEFINITION-phase memory
  correction:** `architecture.md` L63 kanban "remain served" corrected as a dated v0.1.52 drift-fix (no catalog regen —
  `core` atom). **ADRs recorded (§9, operator unavailable — overridable):** ADR-1 in-package storage; ADR-2 install/
  list/doctor + ledger, no uninstall; ADR-3 install-gated plugin-scope; ADR-4 stub-overwrite + projection precedence;
  ADR-5 machinery + minimal-viable content; ADR-6 defer fast/haiku persona downgrade; ADR-7 deterministic
  efficiency-audit marker; ADR-8 plugin agents on the `plugin`/sonnet tier; ADR-9 banner-match discriminator (FR9).
  **Dual DEFINITION review REJECT (2026-07-04) folded** with greppable `<!-- AMEND:ARCH-n -->` / `<!-- AMEND:QA-n -->`
  markers + PM binding Rulings 10-17 (SPEC §0.1): 10 EFF-1 `DoctorIssue` (not `[warn]`); 11 cadence 30d + writer
  `dadaia reports mark-efficiency-audit`; 12 FR4 ceiling (2 named skills: `browser-frontend-implementation`,
  `github-actions-cicd`); 13 profile×pack scope; 14 two goldens + three-leak norm; 15 banner module constant + contract
  test; 16 PAIRED CLAUDE.md doctor line (CRITICAL); 17 mandatory tier contract + plugin `tier: 3` + `tier-taxonomy-rename`
  return. `Aprovado` after dual **re-verify**; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1/FR2 pack storage + `dadaia plugin` machinery (golden-first, ports-and-adapters)

- [x] T-60-10 Capture + commit **golden (a)** (pre-descriptor refactor-lock) BEFORE any descriptor/projection code.
  Owner: software-engineer. Write set: NEW `tests/integration/test_plugin_install_goldens.py` + `_golden/`. <!-- AMEND:ARCH-4 --> <!-- AMEND:QA-2 --> <!-- AMEND:QA-8 -->
  Checklist:
  - Add the golden test (**`integration` layer** — real stage/install/doctor, QA-8b) running `public_assets.install()`
    (all targets) + `public_assets.doctor()`'s full report list on the **current pre-descriptor** tree under
    `FileSystemPublicAssetManager` + `tmp_path`. **Normalize from day one (Ruling 14 / QA-2):** v0.1.55 path/version +
    clock-freeze PLUS the v0.1.58 three leak classes the doctor surface carries — (1) host-state cwd-walk
    (`_check_public_privacy` denylist) → host-state canonicalization; (2) directory-iteration order (`.pi/` lines) →
    sorted-multiset lock; (3) OS-phrased exec-probe text → OS-phrase canonicalization. Golden (a) is the transient
    refactor-lock (retired at ship). Commit BEFORE T-60-11's descriptors. (Golden (b) is captured in T-60-20.)
  - Evidence: golden (a) file + green test on the pre-descriptor tree; the normalization strategy stated in the test.
  - AC-13 ledger — NEW: the golden test + golden (a). No `specs/backlog/**`.
  - **DONE-evidence:** NEW `tests/integration/test_plugin_install_goldens.py` (integration layer, `pytestmark = integration`)
    + `tests/integration/_golden/plugin_install_targets_golden_a_v0160.json` + `plugin_doctor_report_golden_a_v0160.json`.
    Green on the pre-descriptor tree: `pytest tests/integration/test_plugin_install_goldens.py -p no:cacheprovider` → 3 passed.
    Normalization stated in the module docstring: v0.1.55 path/version + clock + the v0.1.58 three leak classes
    (host-state cwd-walk `_norm_path_line`; directory-iteration order `_sort_line_lists`; OS-phrased exec-probe
    `_canon_env_line`); env `git-dirty` dropped; `stage:plugins/*` descriptor-source lines excluded as golden (b)'s
    territory (SPEC AC-5) so golden (a) is byte-stable across T-60-11's pack.json addition. Non-vacuous guard asserts
    per-target install sets + the `[ok] stage:data/AGENTS.md` + `public-privacy` anchors. Commit `test(T-60-10): ...`.

- [x] T-60-11 Ports-and-adapters seam + `dadaia plugin` CLI. Owner: software-engineer. Write set: NEW
  `core/models/plugin_pack.py`, NEW `core/protocols/plugin_store.py`, NEW `infrastructure/json_plugin_store.py`, NEW
  `cli/commands/plugin.py`, `cli/main.py` (register), NEW `public/plugins/{frontend-design,devops}/pack.json` (+ empty
  agents/skills/rules dirs), NEW `tests/unit/core/test_plugin_pack.py`, `tests/unit/infrastructure/test_json_plugin_store.py`,
  `tests/unit/cli/test_plugin_cli.py`. Checklist:
  - **Seam (A, blocking):** `PluginPack` pure `core` model (NO I/O; mirrors `HarnessProfile`); `PluginStore` port;
    `JsonPluginStore` adapter (mirrors `json_harness_profile_store.py`) reading/writing
    `.dadaia/states/installed_plugins.json`. **Forbid** any new `features→infra` / `infra→features` edge.
  - **CLI:** `dadaia plugin install <pack>` / `list` / `doctor`; bad pack → Click `BadParameter` (`exit_code == 2`,
    empty stdout, no `mix_stderr` kwarg). <!-- AMEND:QA-7 --> The `result.stderr` substring check normalizes via the
    shared `_norm_stderr`-style helper (ANSI-strip + box-drawing collapse) BEFORE the `"bogus"/"plugin"` assert
    (v0.1.57 QA-atom law). Register in `cli/main.py`.
  - **Pack descriptors:** `pack.json` for `frontend-design` (agents `frontend-engineer`+`design-specialist`) and
    `devops` (agent `devops-engineer`) — content bodies land in W3.
  - Tests — AC-2 seam (import-linter clean, ignore-cap UNCHANGED); AC-3 CLI surface + `_norm_stderr` bad-value stderr
    (RED-first: pre-fix there is no `plugin` command); adapter round-trip.
  - **W1 mutation-sanity NOW (QA-6 — born falsifiable, NOT deferred):** <!-- AMEND:QA-6 --> AC-11(0a) make `install`
    accept any pack (skip validation) ⇒ the AC-3 bad-value `exit_code == 2` test FAILS → revert; AC-11(0b) drop a
    ledger field in `JsonPluginStore` ⇒ the adapter round-trip test FAILS → revert. Capture each command + failing test
    on this line. (Projection sabotages a/b/c remain in W2.)
  - **existing-test fate ledger (file-enumerated):** NEW files only; `cli/main.py` gains one `add_typer` (SURVIVE:
    the main-CLI smoke test). Gates: ruff, mypy --strict, lint-imports 8/0 (ignore-cap unchanged), unpiped pytest green.
    **AMENDED — the pre-descriptor v0.1.58 full-staging byte-goldens (PM ruling on the T-60-11 STOP; the definition
    under-enumerated this exposure):** adding `public/plugins/**/pack.json` + empty-dir `.gitkeep`s is FR1's real,
    deliberate staging-inventory surface change, so the three full-inventory goldens are re-captured to the
    descriptors-present truth via each test's OWN `UPDATE_INSTALL_GOLDENS` mechanism — a deliberate recorded amendment,
    never a silent regen; **plugin-blind filtering REJECTED** (would hide future plugin-staging drift — golden (a) is the
    deliberately core-scoped lock, golden (b) in W2 locks the full new baseline; three locks, three distinct roles):
    - `tests/unit/infrastructure/test_install_target_goldens.py::test_install_target_resolution_is_byte_identical`
      (`install_target_resolution_v0158.json`) — diff = **+5× `[stage] <WS>/.dadaia/agentic/plugins`** (one per staging
      install target), ZERO other delta, ZERO removals.
    - `tests/unit/infrastructure/test_install_target_goldens.py::test_doctor_all_four_report_is_byte_identical`
      (`doctor_all_four_v0158.json`) — diff = **+8× `[ok] stage:plugins/{frontend-design,devops}/{pack.json,agents/.gitkeep,skills/.gitkeep,rules/.gitkeep}`**,
      ZERO other delta, ZERO removals.
    - `tests/unit/infrastructure/test_public_assets_profile.py::test_absent_profile_doctor_byte_equals_all_four_golden`
      — reuses `_DOCTOR_GOLDEN`; re-greens transitively with the doctor-golden amendment (no own fixture).
      Rigorous multiset (Counter) diff proved the delta is EXACTLY the added `stage:plugins/*` lines and nothing else;
      the `panel_runtime_validation_v0158.json` golden is untouched.
  - AC-13 ledger — NEW: the seam + CLI + descriptors + tests. No `specs/backlog/**`.
  - **DONE-evidence:**
    - Seam (AC-2): NEW `core/models/plugin_pack.py` (`PluginPack` + `InstalledPlugins`, pure, NO I/O, `from_dict`
      parse/validate), NEW `core/protocols/plugin_store.py` (`PluginStore` port), NEW `infrastructure/json_plugin_store.py`
      (`JsonPluginStore`, ledger `.dadaia/states/installed_plugins.json` = `{"schema_version":"1","plugins":[...]}`).
      `lint-imports --no-cache` = **8 kept / 0 broken**, ignore-cap 26 UNCHANGED (no new features→infra/infra→features edge).
    - CLI (AC-3): NEW `cli/commands/plugin.py` (`install <pack>`/`list`/`doctor`) registered in `cli/main.py` (one
      `add_typer`). Projection is a documented W1 no-op seam `_project_pack` (W2/T-60-20 fills it via `public_assets.py`).
      **RED-first:** pre-change `CliRunner.invoke(app, ["plugin","list"])` → exit 2, empty stdout, stderr
      `No such command 'plugin'.` (Rich-boxed → confirms `_norm_stderr` need). Post-change: `install bogus` → exit 2 +
      `_norm_stderr(stderr)` contains `"bogus"`+`"plugin"` + empty stdout; `install frontend-design` records
      `{"schema_version":"1","plugins":["frontend-design"]}`; re-install idempotent; `list`/`doctor` green.
    - Descriptors (FR1): NEW `public/plugins/frontend-design/pack.json` (agents frontend-engineer+design-specialist)
      + `public/plugins/devops/pack.json` (agent devops-engineer) + empty agents/skills/rules dirs via `.gitkeep`.
    - **W1 mutation-sanity (AC-11, born falsifiable):**
      - **(0a)** sabotage: in `cli/commands/plugin.py` `install`, replace the `if pack not in available: raise
        BadParameter` with `if pack not in available: available = {**available, pack: PluginPack.of(pack, agents=("x",))}`
        (accept any pack) ⇒ `tests/unit/cli/test_plugin_cli.py::test_plugin_install_bad_value_is_bad_parameter` FAILS
        (`assert 0 == 2`). Reverted.
      - **(0b)** sabotage: in `infrastructure/json_plugin_store.py` `_to_dict`, drop the `"plugins"` field ⇒
        `tests/unit/infrastructure/test_json_plugin_store.py::test_write_then_read_round_trips` FAILS
        (`plugins: () != ('frontend-design','devops')`). Reverted.
    - **golden (a)** stays green after descriptors (its `stage:plugins/*` filter holds); the three v0.1.58 full-inventory
      goldens were AMENDED per PM ruling (diff = +5 `[stage] .../plugins` install + +8 `[ok] stage:plugins/*` doctor,
      ZERO other delta / ZERO removals; see the fate-ledger enumeration above).
    - Gates: `ruff format --check` (8 files) + `ruff check --no-cache` (pass) + `mypy --strict dadaia_workspace`
      (312 files, 0 issues) + `lint-imports` (8/0) + **full unpiped `pytest` = 4624 passed, 17 skipped, 0 failed**.
      Commit `feat(T-60-11): ...`.

## W2 — FR3 pack projection + ledger + manifest + precedence

- [x] T-60-20 Golden (b) + pack projection + profile-scope + stub replacement + precedence + doctor. Owner:
  software-engineer. Write set: `infrastructure/public_assets.py` (+ `public_assets_common.py` only if a plugin route
  constant is needed), NEW `tests/integration/test_plugin_projection.py` (real install → integration layer, QA-8b) +
  golden (b). Checklist:
  - **Golden (b) capture (Ruling 14 / ARCH-4):** <!-- AMEND:ARCH-4 --> with the W1 descriptors present but BEFORE any
    projection code, capture the durable **"descriptors-present, zero-plugin-installed"** golden (b) (same three-leak
    normalization as golden (a)). The added `stage:plugins/...` descriptor-source parity lines are captured INTO golden
    (b) — not a violation.
  - **`dadaia plugin install`** projects the pack's agents/skills/rules from `.dadaia/agentic/plugins/<pack>/` into the
    runtime projections, hash-compare; records `installed_plugins.json` via the W1 adapter; idempotent (re-install = no-op).
  - **Profile-scoped projection (Ruling 13 / ARCH-3, blocking):** <!-- AMEND:ARCH-3 --> projection, precedence AND
    plugin doctor scope to the harness profile via the same `_profile_harnesses` seam already in `public_assets`
    (absent profile ⇒ all targets, v0.1.58 back-compat) — a claude-only workspace projects only the `.claude/` agent,
    NEVER a `.codex/` orphan; a later out-of-profile pack asset on disk surfaces via the v0.1.58 A3 never-silent law.
    `installed_plugins.json` records the pack (not per-harness).
  - **Stub replacement (ADR-4):** the pack agent body overwrites the projected core stub
    (`.claude/agents/<name>.md`, `.codex/agents/<name>.toml`).
  - **Projection precedence (blocking):** core `public_assets.install` reads `installed_plugins.json` and projects the
    **pack body** (not the stub) for installed plugins, within the profile scope.
  - **Manifest tracking** of pack-projected files; **doctor** reports `[ok]`/`[drift]`/`[missing]` per pack file; a
    stale installed-pack file is never silent.
  - Tests — **AC-3** real-body install (`.claude/agents/frontend-engineer.md` contains the pack body, not
    `[PLUGIN REQUIRED]`) + idempotent (RED-first: no `plugin` command / stub only pre-fix); **AC-4** clobber-safety —
    a following core `public install --target all` keeps the pack body (RED-first: pre-fix core install re-writes the
    stub); **AC-5** doctor **byte-equality vs golden (b)** (runtime-projection + install-set lines) + non-silent stale
    installed-pack file; **AC-15 profile×pack** — `plugin install frontend-design` in a claude-only-profile workspace
    projects NO `.codex/` orphan; precedence honors the scope.
  - **AC-11 sabotages (capture → revert):** (a) `plugin install` skips projection ⇒ AC-3 real-body test FAILS; (b) core
    install ignores `installed_plugins.json` ⇒ AC-4 clobber-safety test FAILS (stub re-written); (c) doctor emits zero
    lines for a stale installed-pack file ⇒ AC-5 non-silent test FAILS. Capture each command + failing test.
  - **existing-test fate ledger (file-enumerated):** SURVIVE byte-identical on the no-plugin path (proven by the
    T-60-10 golden) — `tests/unit/infrastructure/test_public_assets.py` doctor/install cases,
    `tests/integration/test_public_doctor_parity.py`.
  - AC-13 ledger — EDITED: `public_assets.install`/`doctor` (plugin projection + precedence + doctor). No
    `specs/backlog/**`.
  - **DONE-evidence:**
    - **Golden (b)** captured FIRST (descriptors present, zero plugin, BEFORE projection code) into NEW
      `tests/integration/test_plugin_projection.py` + `tests/integration/_golden/plugin_{install_targets,doctor_report}_golden_b_v0160.json`
      (INCLUDES the 8 `stage:plugins/*` lines — golden (b)'s baseline, unlike plugin-blind golden (a)); committed
      `test(T-60-20): ...` (SHA `fbc261bd`) BEFORE any projection code. After the projection code the zero-plugin path
      is byte-identical to golden (b) (AC-5 green): `_project_installed_plugins`/`_doctor_installed_plugins` are strict
      no-ops when `installed_plugins.json` is absent.
    - **Projection (FR3):** `install_plugin` on `FileSystemPublicAssetManager` records the ledger (idempotent) + projects
      the pack's agents/skills/rules from staged `.dadaia/agentic/plugins/<pack>/` (profile-scoped via `_profile_harnesses`;
      pack agent body overwrites the `.claude/agents/<name>.md` stub + renders `.codex/agents/<name>.toml` from the pack
      model). CLI `_project_pack` seam (flagged in W1) now delegates to `install_plugin`; ledger write moved into it
      (single owner). `plugin doctor` reports per-pack-file status via new public `doctor_plugins`.
    - **Precedence (AC-4):** core `install()` calls `_project_installed_plugins(active_harnesses)` after the core loop —
      a later `public install --target all` keeps the pack body. **Doctor precedence:** the core `claude:agents/<name>.md`
      line is skipped for installed-plugin agents (reported vs the pack body by the `plugin:<pack>:...` block, no false
      drift). Codex doctor is presence/quality-based (dcx1/4/5) so the pack-rendered toml needs no special-casing.
    - **Tests (integration, synthetic pack body seeded into the staged tree — real W3 bodies land later):** AC-3 real-body
      install + idempotent + codex `gpt-5.3-codex` render; AC-4 clobber-safety (core install keeps pack body); AC-5 doctor
      `[ok] plugin:...` + no false `[drift] claude:agents/...` + non-silent stale ([drift]/[missing]); AC-15 claude-only
      profile → NO `.codex/` orphan + ledger records the pack (not per-harness). Full suite **4633 passed, 17 skipped, 0
      failed**.
    - **AC-11 sabotages (capture → revert):**
      - **(a)** `install_plugin` skips `_project_installed_plugins` ⇒ `test_plugin_install_projects_real_body_over_stub`
        FAILS (stub not replaced). Reverted.
      - **(b)** core `install()` drops the precedence `_project_installed_plugins` call ⇒
        `test_core_install_keeps_pack_body_precedence` FAILS (stub clobbers pack body). Reverted.
      - **(c)** `_doctor_installed_plugins` forces `packs = ()` ⇒ `test_doctor_non_silent_on_stale_pack_file` FAILS
        (`[drift] plugin:...` absent). Reverted.
    - **existing-test fate ledger (file-enumerated — SURVIVE byte-identical on the no-plugin path, proven by golden (a) +
      golden (b) + the amended v0.1.58 goldens all green untouched this wave):**
      `tests/unit/infrastructure/test_public_assets.py` (doctor/install cases — unchanged, green),
      `tests/integration/test_public_doctor_parity.py` (guardrail-pair doctor cases — unchanged, green),
      `tests/unit/infrastructure/test_install_target_goldens.py` + `test_public_assets_profile.py` (the W1-amended
      goldens — unchanged, green). No `specs/backlog/**` staged.
    - Gates: `ruff format --check` + `ruff check --no-cache` (I001 import-order auto-fixed) + `mypy --strict` (312 files,
      0 issues) + `lint-imports` **8 kept / 0 broken** ignore-cap 26 UNCHANGED (the projection edit is same-layer inside
      `infrastructure/public_assets.py`; the CLI→`FileSystemPublicAssetManager` edge is cli→infra, ungoverned). Commit
      `feat(T-60-20): ...`.

## W3 — FR4/FR5 minimal-viable pack content + plugin-scope rewrite + plugin tier (ai-engineer)

- [x] T-60-30 Enumerated pack content (3 agent bodies + ONE skill/pack) + plugin-scope rewrite + plugin tier. Owner:
  ai-engineer. Write set: NEW `public/plugins/frontend-design/agents/{frontend-engineer,design-specialist}.md` + NEW
  `public/plugins/frontend-design/skills/browser-frontend-implementation/SKILL.md`; NEW
  `public/plugins/devops/agents/devops-engineer.md` + NEW `public/plugins/devops/skills/github-actions-cicd/SKILL.md`;
  `public/rules/plugin-scope.md` (rewrite); NEW `tests/unit/infrastructure/test_plugin_content.py`. Checklist:
  - **3 real agent bodies** with full frontmatter (`name`/`description`/**`tier: 3`** (leaf-worker band, Ruling 17)/
    **`model: claude-sonnet-4-6`**/tools) + real SDD-role body (frontend: browser HTML/CSS/JS/TS/React; design: UX/UI +
    visual review; devops: CI/CD + GitHub Actions + gitflow + deploy).
  - **Enumerated skills — EXACTLY ONE per pack, ZERO new rules (Ruling 12 / ARCH-5):** <!-- AMEND:ARCH-5 -->
    `frontend-design` → skill `browser-frontend-implementation`; `devops` → skill `github-actions-cicd`. Reference (do
    NOT duplicate) the existing codex `frontend-ctx`/`design-ctx` adapters. Everything beyond the two named skills →
    `plugin-pack-content-libraries` backlog return.
  - **Rewrite `public/rules/plugin-scope.md`** + the `[PLUGIN REQUIRED]` response to install-gated wording (drop "no
    install command exists"/"not yet distributed"; name `dadaia plugin install`); record the retired `panel-ux-overhaul`
    deviation class (doc note).
  - Tests — **AC-6** each pack agent generic + **Codex `model`-field tiered (ARCH-2):** <!-- AMEND:ARCH-2 --> the
    installed agent's `.codex/agents/<name>.toml` renders `model = "gpt-5.3-codex"` (sonnet/plugin), NOT `gpt-5.5`
    (opus) — the `model_reasoning_effort` is `medium` for plugin AND opus AND fallback and is NOT the discriminator —
    plus the Claude frontmatter `model: claude-sonnet-4-6`; `[ok] public-privacy`; exactly the two named skills present;
    ctx adapters reused not duplicated. **AC-7** install-gated grep (RED-first: pre-fix the rule says "no install
    command exists") — retired wording gone from the projected `.claude/rules/plugin-scope.md`.
  - **AC-11 sabotages (capture → revert):** (d) leave the retired wording in `plugin-scope.md` ⇒ AC-7 grep test FAILS;
    **(f)** give a plugin agent `model: claude-opus-4-8` ⇒ AC-6 **Codex `model`-field** test FAILS (`.codex/...toml`
    renders `gpt-5.5`). Capture each.
  - **existing-test fate ledger (file-enumerated):** the `plugin-scope` rule is a lib-originated asset — a grep test
    over the projected rule INVERTS from "asserts stub language" to "asserts install-gated language". `check_agent_skill_refs`
    (public_assets doctor) SURVIVES — pack skill refs must resolve.
  - AC-13 ledger — NEW: 3 agent bodies + minimal skills/rules; EDITED: `plugin-scope.md`. No `specs/backlog/**`.
  - **W5 follow-up (PM-ruled evidence append, FR5-adjacent — commit `feat(T-60-30): install-gated wording in plugin
    stub bodies (W5 follow-up)`):** the W5 E2E surfaced that the 3 STUB agent bodies
    (`public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`) still claimed "plugin pack is not yet
    distributed (no install command exists)" — factually wrong once v0.1.60 ships (W3 rewrote only the plugin-scope
    RULE). Fixed the 3 stub `[PLUGIN REQUIRED]` bodies to the same install-gated wording (`dadaia plugin install <pack>`,
    ships in v0.1.60). Discriminators preserved for E2E scenario (a): `plugin: true` frontmatter kept, `[PLUGIN REQUIRED]`
    marker kept (`test_plugin_projection.py:222` asserts it in the pre-install stub), NO pack-body H1 heading added
    (`_PACK_BODY_HEADING`/`_is_plugin_stub` still discriminate). Grep guard: 0 "not yet distributed"/"no install command
    exists" hits under `public/` source + projected `.claude/agents/` + `.claude/rules/`. Propagated (stage/install/doctor
    exit 0, `[ok] public-privacy`). Goldens did NOT move (`[ok] stage:*`/`[ok] claude:*` line format is hash-verified but
    content-invariant; `git diff _golden/` empty). Gates: ruff format/check clean, full unpiped pytest 4674 passed / 17
    skipped.

## W4 — FR6/FR7 tier-taxonomy fix + efficiency-audit trigger (software-engineer)

- [x] T-60-40 Efficiency-audit EFF-1 `DoctorIssue` + `mark-efficiency-audit` writer + MANDATORY tier-taxonomy contract.
  Owner: software-engineer. Write set: `features/spec_context/doctor.py` (new EFF-1 `DoctorIssue` check) +
  `EFFICIENCY_AUDIT_STALE_DAYS = 30` constant; `cli/commands/reports.py` (NEW `mark-efficiency-audit` verb) + its
  marker-writer helper; NEW `tests/unit/.../test_efficiency_audit_trigger.py` + `tests/unit/cli/test_reports_mark_efficiency_audit.py`;
  **MANDATORY** `tests/contract/test_agent_tier_taxonomy.py`. Checklist:
  - **EFF-1 `DoctorIssue`, NOT a `[warn]` token (Rulings 10/11 / ARCH-6/7 / QA-3):** <!-- AMEND:ARCH-6 --> <!-- AMEND:ARCH-7 --> <!-- AMEND:QA-3 -->
    add a `DoctorService` check emitting `DoctorIssue(code="EFF-1", fixable=False, description=<staleness age + "run:
    dadaia reports mark-efficiency-audit ...">)` reading `.dadaia/states/last_efficiency_audit.json` (schema
    `{schema_version,last_efficiency_audit,by,report}`) vs `EFFICIENCY_AUDIT_STALE_DAYS = 30`. **4-case matrix:**
    *absent* ⇒ **no issue** (preserves the fresh-workspace `All invariants OK` happy path); *fresh* (≤30d) ⇒ no issue;
    *stale* (>30d) ⇒ EFF-1; *malformed* (invalid JSON / missing `last_efficiency_audit`) ⇒ EFF-1 "malformed marker",
    **never a crash**. The bare `dadaia doctor` exit stays 0 (already never exits non-zero on issues).
  - **Writer verb (Ruling 11):** add `dadaia reports mark-efficiency-audit --report <workspace-relative-path>
    [--by <agent>]` (one verb under the existing `reports` group) writing the marker with the current RFC3339 timestamp
    — the production EFF-1 clear path (fresh marker ⇒ no EFF-1).
  - **MANDATORY tier-taxonomy contract (Ruling 17 / ARCH-9 / QA-8a):** <!-- AMEND:ARCH-9 --> <!-- AMEND:QA-8 -->
    NON-OPTIONAL `tests/contract/test_agent_tier_taxonomy.py` asserts every non-plugin core agent carries a numeric
    `tier` + a registry-known `model`, the 9 core keep `dispatch` (opus), the 3 plugin agents carry `tier: 3` +
    `model: claude-sonnet-4-6`.
  - Tests — **AC-8** EFF-1 4-case matrix (absent/fresh/stale/malformed — RED-first: no `DoctorService` EFF-1 check
    pre-fix) + writer round-trip; **AC-9** MANDATORY taxonomy contract.
  - **AC-11 sabotage (capture → revert):** (e) make the `DoctorService` skip the EFF-1 check ⇒ AC-8 stale-marker test
    FAILS. Capture.
  - **existing-test fate ledger (QA-3 — ENUMERATE, do not assert "unchanged"):** <!-- AMEND:QA-3 --> the workspace-doctor
    suite exposed to a default marker state — `tests/integration/test_cli_doctor.py` + every fresh-workspace e2e that
    runs `dadaia doctor` — **stays green because *absent* ⇒ no EFF-1** (the fresh-workspace `All invariants OK` path is
    unchanged); enumerate each and confirm.
  - AC-13 ledger — NEW: the EFF-1 check + writer verb + mandatory taxonomy contract + tests. No `specs/backlog/**`.
  - **DONE-evidence:**
    - **EFF-1 (FR7):** `features/spec_context/doctor.py` — NEW `EFFICIENCY_AUDIT_STALE_DAYS = 30` + `_EFFICIENCY_AUDIT_MARKER`
      constants + `_check_efficiency_audit()` emitting `DoctorIssue(code="EFF-1", fixable=False, description=<age +
      "run: dadaia reports mark-efficiency-audit --report <report-path>">)`, wired into `check()`. Reads
      `.dadaia/states/last_efficiency_audit.json` (`{schema_version,last_efficiency_audit,by,report}`). **4-case matrix
      (through `check()`):** absent ⇒ no issue; fresh/≤30d ⇒ no issue; stale/>30d ⇒ EFF-1; malformed (invalid JSON /
      missing field / unparseable ts) ⇒ EFF-1 "malformed marker", never a crash. Bare `dadaia doctor` exit stays 0
      (service never raises on issues; `[manual]` render for fixable=False).
    - **Writer (FR7):** `cli/commands/reports.py` — NEW `dadaia reports mark-efficiency-audit --report <path> [--by <agent>]`
      + `_write_efficiency_audit_marker` helper writing the marker with the current RFC3339 (`...Z`) timestamp — the
      production EFF-1 clear path. Round-trip test proves writer↔reader agree (stale marker ⇒ EFF-1 → run writer ⇒ EFF-1
      cleared).
    - **MANDATORY tier-taxonomy contract (FR6, Ruling 17):** NEW `tests/contract/test_agent_tier_taxonomy.py` (yaml-parsed
      frontmatter) — every non-plugin core agent (9 in `public/agents/` without `plugin: true`) carries a numeric `tier`
      + registry-known `model == claude-opus-4-8` (registry tier `dispatch`); the 3 plugin bodies
      (`public/plugins/*/agents/*.md`) carry `tier: 3` + `model: claude-sonnet-4-6` (registry tier `plugin`); roster
      counts pinned (9 core, 3 plugin).
    - **RED-first / AC-11(e) sabotage (capture → revert):** removing `issues.extend(self._check_efficiency_audit())` from
      `check()` ⇒ `test_efficiency_audit_trigger.py::test_stale_marker_emits_eff1_through_check` AND
      `test_reports_mark_efficiency_audit.py::test_writer_round_trip_clears_eff1` FAIL (`assert 0 == 1` — EFF-1 not
      emitted). Reverted. (Pre-fix there was no `DoctorService` EFF-1 check — the sabotage is the RED-first proof.)
    - **existing-test fate ledger (QA-3 — ENUMERATED, each verified green because *absent ⇒ no issue*):**
      `tests/integration/test_cli_doctor.py` (workspace-doctor CLI — fresh ws asserts exit 0 / happy path, unchanged),
      `tests/e2e/features/test_public_pipeline.py`, `tests/e2e/features/test_specs_upgrade_e2e.py`,
      `tests/e2e/test_lifecycle_engine_smoke.py` (fresh-workspace `dadaia doctor` journeys — all green). 31/31 passed on
      the enumerated set. No `specs/backlog/**` staged.
    - Gates: `ruff format --check` + `ruff check --no-cache` + `mypy --strict` (312 files, 0 issues) + `lint-imports`
      **8 kept / 0 broken** ignore-cap 26 UNCHANGED (EFF-1 lives in `features/spec_context` reading `.dadaia/states` via
      the existing doctor file-IO patterns — no new edge, no core-IO ratchet trip) + **full unpiped `pytest` = 4657
      passed, 17 skipped, 0 failed**. Goldens untouched this wave. Commit `feat(T-60-40): ...`.

## W4B — FR9 provenance-gated consumer-repo fan-out (HIGH bug fix; AMENDS v0.1.58 Ruling L)

- [x] T-60-45 Banner-constant discriminator + PAIRED provenance-aware doctor on the consumer `AGENTS.md` fan-out.
  Owner: software-engineer. Write set: `infrastructure/workspace_guardrail.py` (`_CANONICAL_AGENTS_BANNER` constant +
  `_install_guardrail_pair._write_one` + `_doctor_guardrail_pair` PAIRED), NEW
  `tests/unit/infrastructure/test_consumer_fanout_provenance.py`, NEW contract
  `tests/contract/test_agents_banner_constant_matches_public_data.py`, ADJUDICATED (QA-gate, full flip set):
  `tests/unit/infrastructure/test_consumer_fanout.py` + `tests/unit/features/public/test_workspace_guardrail_pair.py`
  + `tests/unit/infrastructure/test_public_assets.py` + `tests/integration/test_public_doctor_parity.py`. Resolves bug
  `public-install-clobbers-consumer-repo-agents-md`. Checklist:
  - **Banner = MODULE CONSTANT + contract test (Ruling 15 / QA-1):** <!-- AMEND:QA-1 --> add
    `_CANONICAL_AGENTS_BANNER` (fixed literal = the `public/data/AGENTS.md` banner block) + the contract test
    `test_agents_banner_constant_matches_public_data` asserting BYTE-equality with the actual `public/data/AGENTS.md`
    banner (drift on either side fails; **NO runtime read of `public/data`**). In `_write_one`, gate the divergent
    overwrite on a match against the constant: **banner-match** → restore + `[updated] <path> (overwrote divergent
    workspace-law copy)`; **no banner** → `[foreign] <path> — left untouched` (never overwrite); **absent** → create +
    `[ok]`.
  - **CLAUDE.md bridge follows its sibling** — written only when the sibling `AGENTS.md` is created/restored; when
    `AGENTS.md` is `[foreign]`, NO `CLAUDE.md` is dropped. A foreign (non-stub) existing `CLAUDE.md` → `[foreign]`,
    untouched.
  - **Doctor provenance-aware ON THE PAIR (Ruling 16 / ARCH-1 — CRITICAL):** <!-- AMEND:ARCH-1 --> `_doctor_guardrail_pair`
    makes BOTH lines provenance-aware — when the consumer `AGENTS.md` is `[foreign]` (no banner), the paired `CLAUDE.md`
    line is **also `[foreign]`** whether the CLAUDE.md is absent OR a foreign non-stub — never `[missing]`/`[drift]`, so
    `public doctor` (exits 1 on any `[missing]`/`[drift]`, `public.py:161-172`) **EXITS 0** for a hand-authored repo. A
    banner-bearing (canonical) copy keeps `[ok]`/`[drift]`/`[missing]` on both lines. Self-repo skip retained.
  - Tests — **AC-14 (RED-first, REGISTERED fixture — QA-4):** <!-- AMEND:QA-4 --> the fixture consumer repo is
    **registered** in `spec_contexts.json` (schema-v2, via `_register_context`/`_write_registry`) so the fan-out reaches
    it; a hand-authored (no-banner) `AGENTS.md` survives `install` byte-identical, **BOTH** paired doctor lines
    (`repos/<slug>:AGENTS.md` + `:CLAUDE.md`) report `[foreign]` (no `[missing]`), and `dadaia public doctor` **EXITS
    0**; a stale-canonical (banner-bearing) copy → `[updated]`; absent → `[ok]`. RED-first: pre-fix the registered
    hand-authored file is overwritten + `[updated]` (the bug). Plus the banner **contract test**.
  - **AC-11(g) sabotage (capture → revert):** drop the banner discriminator (overwrite any divergent consumer
    `AGENTS.md`) ⇒ the AC-14 hand-authored-survives test FAILS against the **registered** fixture (foreign file
    clobbered). Capture the command + failing test.
  - **v0.1.58 test-pin adjudication — FULL FLIP SET (Ruling 15 / QA-1; QA-gate, do NOT silently rewrite):**
    <!-- AMEND:QA-1 --> under the module-constant banner, every consumer copy from a **synthetic bannerless source**
    reclassifies `[foreign]`. Enumerate per file the concrete affected cases (not one per file) — re-fixture the source
    to EMBED `_CANONICAL_AGENTS_BANNER` to keep a canonical classification — each adjudicated INVARIANT-or-amended with
    rationale:
    - `test_consumer_fanout.py`: `test_doctor_reports_ok_for_fresh_consumer` (`[ok]`→`[foreign]`),
      `test_doctor_flags_drift_for_stale_consumer` (`[drift]`→`[foreign]`),
      `test_divergent_consumer_root_restored_with_updated_line` (bannerless divergent → `[foreign]`; re-fixture WITH the
      banner to keep `[updated]`).
    - `test_workspace_guardrail_pair.py`: **Case 6 `test_doctor_four_line_output`** — a doctor-`[ok]`-parity flip
      (`[ok]`→`[foreign]`), NOT an `[updated]`-on-divergent case (QA-1 misattribution correction).
    - `test_public_assets.py::TestInstallConsumerReposGuardrailPair::test_force_false_overwrites_divergent_consumer_with_updated_line`
      (@ L748) — the REAL `[updated]`-on-divergent INSTALL pin; re-fixture the source WITH the banner to keep `[updated]`.
    - `test_public_doctor_parity.py` (consumer fan-out `[ok]`/`[drift]` cases → `[foreign]` unless bannered; ALSO add
      the PAIRED CLAUDE.md `[foreign]` assertion).
    A byte diff on a Ruling-L pin is a deliberate amendment, recorded, never a silent regen. Frozen v0.1.50 no-steal
    suite untouched — confirm zero-diff.
  - **AC-13 ledger** — EDITED: `_write_one` (banner-constant gate), `_doctor_guardrail_pair` (PAIRED `[foreign]`); NEW:
    `_CANONICAL_AGENTS_BANNER` constant, `test_consumer_fanout_provenance.py`, banner contract test; ADJUDICATED: the
    full flip set across the 4 v0.1.58 pin files (enumerated cases). No `specs/backlog/**`.
  - **DONE-evidence:**
    - **Fix (FR9):** `infrastructure/workspace_guardrail.py` — NEW `_CANONICAL_AGENTS_BANNER` module constant (fixed
      literal = the `public/data/AGENTS.md` banner block) + `_carries_canonical_banner()`; `_install_guardrail_pair` gains
      `_write_consumer_agents` (three-way: absent→create+`[ok]`; banner-match→restore+`[updated]`; no-banner→`[foreign]
      — left untouched`) + `_write_consumer_claude` (sibling-follows-fate: written only when AGENTS created/restored; a
      foreign non-stub CLAUDE.md is `[foreign]` untouched; AGENTS foreign ⇒ no CLAUDE.md drop). `_doctor_guardrail_pair`
      gains `_check_consumer_agents` (absent→`[missing]`; no-banner→`[foreign]`; banner→`[ok]`/`[drift]`) + PAIRED
      CLAUDE.md `[foreign]` when AGENTS.md is `[foreign]` (Ruling 16 → `public doctor` exits 0). Self-repo skip + root
      (lib-owned) semantics unchanged. Constant re-exported via `public_assets`.
    - **RED capture (bug reproducing, via `git stash` of the fix):** a registered consumer with a hand-authored
      (no-banner) `AGENTS.md` → pre-fix `public install` → `survived byte-identical: False`, `CLAUDE.md dropped: True`,
      install line `[updated] .../repos/game/AGENTS.md (overwrote divergent workspace-law copy)`, doctor
      `['[ok] repos/game:AGENTS.md', '[ok] repos/game:CLAUDE.md']` (masking the clobber). Post-fix (GREEN): survived
      `True`, no CLAUDE.md, `[foreign] ... — left untouched`, doctor `['[foreign] repos/game:AGENTS.md', '[foreign]
      repos/game:CLAUDE.md']`.
    - **NEW tests:** `tests/unit/infrastructure/test_consumer_fanout_provenance.py` (8 — three-way install + CLAUDE
      pairing + AC-14 registered-fixture paired-`[foreign]` + `public doctor` exit-0 proxy + drift/ok);
      `tests/contract/test_agents_banner_constant_matches_public_data.py` (2 — byte-equality of the constant vs the
      shipped banner block).
    - **AC-11(g) sabotage (capture → revert):** `_carries_canonical_banner` → `return True` (drop the discriminator) ⇒
      `test_hand_authored_consumer_agents_survives_untouched` AND `test_doctor_pair_foreign_for_hand_authored_repo_exits_zero`
      FAIL against the REGISTERED fixture (foreign file clobbered). Reverted.
    - **FULL FLIP-SET adjudication (per-case, deliberate Ruling-L amendment — recorded, never silent):**

      | file | case | flip | how |
      |---|---|---|---|
      | `test_consumer_fanout.py` | `test_doctor_reports_ok_for_fresh_consumer`→`..._foreign_for_fresh_bannerless_consumer` | `[ok]`→`[foreign]` | bannerless source; assert `[foreign]` |
      | `test_consumer_fanout.py` | `test_doctor_flags_drift_for_stale_consumer`→`..._flags_foreign_for_bannerless_consumer` | `[drift]`→`[foreign]` | bannerless stale; assert `[foreign]` |
      | `test_consumer_fanout.py` | `test_divergent_consumer_root_restored_with_updated_line` | keep `[updated]` | re-fixture consumer content WITH `_CANONICAL_AGENTS_BANNER` |
      | `test_workspace_guardrail_pair.py` | Case 6 `test_doctor_four_line_output` | `[ok]`→`[foreign]` (parity flip) | root `[ok]` + consumer pair `[foreign]` (QA-1 misattribution corrected) |
      | `test_public_assets.py::TestInstallConsumerReposGuardrailPair` | `test_force_false_overwrites_divergent_consumer_with_updated_line` (@L748) | keep `[updated]` | re-fixture source+stale-consumer WITH the banner |
      | `test_public_doctor_parity.py` | `test_doctor_emits_four_labels_with_one_consumer` | `[ok]`→`[foreign]` + PAIRED CLAUDE.md `[foreign]` | bannerless source; assert root `[ok]` + consumer pair `[foreign]` |

    - **Frozen v0.1.50 no-steal suite:** zero-diff confirmed (`git diff` on `test_lock_steal.py` + `test_lease*.py` = 0
      lines). **Goldens:** unchanged this wave (the fan-out targets CONSUMER repos, not self-repo staging).
    - Gates: `ruff format --check` + `ruff check --no-cache` + `mypy --strict` (312 files, 0 issues) + `lint-imports`
      **8 kept / 0 broken** (guardrail edit is same-layer infra) + **full unpiped `pytest` = 4667 passed, 17 skipped, 0
      failed**. Commit `fix(T-60-45): ...` (bug id `public-install-clobbers-consumer-repo-agents-md` in the body).
  - **FIX ROUND (QA REQUEST_CHANGES — HIGH bug `public-doctor-flags-hand-authored-consumer-agents-md`, found by the W5
    E2E `b9c588b4`):** the FR9 `_doctor_guardrail_pair`/`_check_consumer_agents` provenance logic was DEAD for the real
    `dadaia public doctor` — `manager.doctor()` doctored consumers via the untouched `runtime_expectations` path, emitting
    `[drift] repos/<slug>:AGENTS.md` + `[missing] repos/<slug>:CLAUDE.md` → EXIT 1 (Ruling 16 violation); the unit test
    passed by calling the dead helper directly (false confidence).
    - **Root-cause wiring:** extracted the consumer classification into a SINGLE authority
      `_doctor_consumer_pair_lines` (`workspace_guardrail.py`); `manager.doctor()` (`public_assets.py`) now calls it after
      the runtime loop; `runtime_expectations` (`install_helpers.py`) NO LONGER yields the `repos/<slug>:` pairs (unused
      `_consumer_repos_for_root`/`_is_self_repo` imports removed). `_doctor_guardrail_pair` also delegates to it — ONE
      classification path for consumers, no parallel legacy path.
    - **PRIMARY end-to-end proof:** NEW `test_public_doctor_parity.py::test_manager_doctor_foreign_pair_for_hand_authored_consumer`
      exercises the REAL `manager.doctor()` (stage+install+doctor) → `[foreign]` pair, no `[drift]`/`[missing]` on
      `repos/game`. **E2E xfail LIFTED:** `test_plugin_pipeline.py::test_e_public_doctor_exits_zero_for_hand_authored_consumer`
      now PASSES (real `dadaia public doctor` exit 0). The direct-helper provenance test is retained as a SECONDARY lens
      (now hits the shared authority, not dead code).
    - **fate ledger (fix round):** `test_public_assets.py::TestRuntimeExpectations::test_yields_consumer_repo_pair`
      INVERTED → `test_no_longer_yields_consumer_repo_pair` (runtime_expectations no longer yields consumer pairs — the
      deliberate authority move; root pair still yielded). The W4B flip-set doctor tests
      (`test_consumer_fanout.py`, `test_workspace_guardrail_pair.py` Case 6, `test_public_doctor_parity.py`
      four-labels) call `_doctor_guardrail_pair` which now delegates to the shared authority → valid (secondary lenses),
      re-verified green.
    - Frozen v0.1.50 no-steal suite zero-diff; goldens unchanged (consumer lines are workspace-level, not self-repo
      staging); `mypy --strict` 0 issues; `lint-imports` 8/0; **full unpiped `pytest` = 4674 passed, 17 skipped, 0
      failed, 0 xfailed**. Fix commit `fix(T-60-45): wire provenance gate into the real doctor consumer fan-out` (new
      bug id in the body). Both bugs' terminal `resolved` events appended at CLOSURE (T-60-70).

## W5 — per-pack sandboxed E2E (qa-engineer)

- [x] T-60-50 Per-pack E2E. Owner: qa-engineer. Write set: NEW `tests/e2e/features/test_plugin_pipeline.py` (or a
  sibling of `test_public_pipeline.py` reusing its helpers). Checklist:
  - Scaffold a workspace in-process via `CliRunner.invoke`; assert: (a) fresh no-plugin → the 3 agents are stubs +
    descriptors-present-zero-plugin doctor green + golden (b) byte-lock; (b) `plugin install frontend-design` → both
    agents real + `installed_plugins.json` correct + doctor green; (c) `plugin install devops` → `devops-engineer`
    real; (d) a following core `public install --target all` keeps the pack bodies (AC-4); **(e/FR9, QA-4)** a
    **registered** (in `spec_contexts.json` via `_register_context`/`_write_registry`) consumer repo with a
    hand-authored root `AGENTS.md` survives `public install --target all` byte-identical (**BOTH** paired doctor lines
    `[foreign]`) and a real `dadaia public doctor` run **EXITS 0** while a stale-canonical fixture gets `[updated]`;
    **(f/QA-5)** double `plugin install frontend-design` no-ops (`installed_plugins.json` unchanged — ledger
    idempotency); **(g/QA-5)** `installed_plugins.json` coexists with `harness_profile.json`/overlay state without
    interference (profile×pack). `tmp_path` isolation + `-p no:cacheprovider`; <!-- AMEND:QA-4 --> <!-- AMEND:QA-5 -->
    **wall-time ≤ ~10s** (v0.1.58 ~6s precedent — a concrete bound, not "stated budget").
  - Tests — **AC-10** (a)-(g) scenarios.
  - **AC-11 discriminating sabotage (capture → revert):** with the T-60-20(b) precedence sabotage active, the E2E
    scenario (d) FAILS (pack body reverts to stub); with the T-60-45 banner discriminator dropped, scenario (e) FAILS
    (registered hand-authored `AGENTS.md` clobbered). Capture the command + failing E2E.
  - AC-13 ledger — NEW/EXTENDED: the per-pack E2E. No `specs/backlog/**`.
  - **DONE-evidence:**
    - NEW `tests/e2e/features/test_plugin_pipeline.py` — real-CLI in-process E2E (`CliRunner` + `tmp_path`, mirroring
      `test_public_pipeline.py`); **6 tests → 5 passed + 1 xfailed**, module wall-time **~7.7s** (call-time 6.1s;
      transient 10.x readings were post-suite machine load) — inside the ~10s bound. `-p no:cacheprovider`, venv faked
      by the conftest autouse fixture. Scenario evidence (real `dadaia` verbs):
      - **(a)** fresh `dadaia init --harness all` → all 3 plugin agents are `plugin: true` stubs (no pack-body heading);
        empty ledger; **golden (b) doctor byte-lock** reused from `tests/integration/_golden/plugin_doctor_report_golden_b_v0160.json`
        (same three-leak normalization) + zero `[missing]`/`[drift]` blockers (green). `test_a_fresh_no_plugin_stubs_doctor_green_and_golden_b_bytelock` PASS.
      - **(b)+(c)+(d)** merged install-chain `test_bcd_install_chain_and_core_reinstall_precedence` PASS: `plugin install
        frontend-design` → `frontend-engineer`+`design-specialist` real bodies (`# … [plugin]`), codex tomls render
        `gpt-5.3-codex` (plugin tier, not `gpt-5.5`), `installed_plugins.json` = `{"schema_version":"1","plugins":["frontend-design"]}`,
        `dadaia public doctor` exit 0; then `plugin install devops` → `devops-engineer` real, ledger accumulates; then core
        `dadaia public install --target all` keeps ALL 3 pack bodies (AC-4 precedence).
      - **(e/FR9, QA-4)** split: `test_e_install_registered_hand_authored_consumer_survives_byte_identical` PASS — a
        REGISTERED (schema-v2 `spec_contexts.json`) consumer `repos/game` with a hand-authored root `AGENTS.md` survives
        `public install --target all` byte-identical (`[foreign] … — left untouched`, no `CLAUDE.md` orphan); a
        stale-canonical `repos/stale` is restored + `[updated]`. The DOCTOR half
        `test_e_public_doctor_exits_zero_for_hand_authored_consumer` is **`xfail(strict=True)`** against **OPEN HIGH bug
        `public-doctor-flags-hand-authored-consumer-agents-md`**: the real `dadaia public doctor` emits
        `[drift] repos/game:AGENTS.md` + `[missing] repos/game:CLAUDE.md` and EXITS **1** (not the Ruling-16 `[foreign]`
        pair + exit 0) because FR9's `_doctor_guardrail_pair` is imported but **never called by `manager.doctor()`**
        (consumer doctor lines still come from `runtime_expectations`). Strict xfail = regression lock: it XPASSES → suite
        red the moment software-engineer wires the provenance gate into the doctor fan-out; the marker must then be removed.
      - **(f/QA-5)** `test_f_double_install_frontend_design_ledger_idempotent` PASS — a second `plugin install
        frontend-design` reports "already installed" and leaves `installed_plugins.json` byte-unchanged.
      - **(g/QA-5)** `test_g_installed_plugins_coexists_with_harness_profile_state` PASS — `init --harness claude` +
        `plugin install frontend-design`: `harness_profile.json` byte-unchanged (`["claude"]`), ledger records the pack,
        claude body real, NO `.codex/` orphan (profile-scoped).
    - **AC-11 discriminating sabotages (capture → revert, both reverted CLEAN):**
      - **(d) precedence** — in `public_assets.install()` replaced the trailing
        `self._project_installed_plugins(agentic_dir, workspace_root, active_harnesses, force, installed)` with a no-op ⇒
        `test_bcd_install_chain_and_core_reinstall_precedence` FAILS: `AssertionError: frontend-engineer is still a stub
        after install`. Reverted.
      - **(e) banner** — in `workspace_guardrail._carries_canonical_banner` replaced the banner `startswith` check with
        `return True` ⇒ `test_e_install_registered_hand_authored_consumer_survives_byte_identical` FAILS:
        `AssertionError: hand-authored AGENTS.md clobbered`. Reverted.
    - **Bug filed (mandatory):** `specs/bugs/20260704T23Z-00.jsonl` — `public-doctor-flags-hand-authored-consumer-agents-md`
      (HIGH). Surfaced to project-manager (REQUEST_CHANGES on FR9's doctor wiring) for software-engineer remediation.
    - Gates: `ruff format --check` + `ruff check --no-cache` (dadaia_workspace/ + tests/, 812 files) + `mypy --strict
      dadaia_workspace` (312 files, 0 issues) + `mypy --strict` on the new test file (0 issues) + `lint-imports` **8 kept /
      0 broken** (E2E-only, no import edges) + **full unpiped `pytest` = 4674 passed, 17 skipped, 1 xfailed, 0 failed**.
      Goldens untouched (integration `_golden/` byte-identical). Caches removed; `git status` clean (test + this marker +
      the bug jsonl). Commit `test(T-60-50): ...`.

## W6 — gates + ship

- [x] T-60-60 Full local gates (AC-12) + self-hosting reconcile, then ship. Owner: software-engineer (gates) +
  qa-engineer (ship-gate) + security-reviewer (push-gate). Write set: none (`specs/**` untouched). **DONE evidence
  (2026-07-05):** gates — ruff format --check 0 / ruff check --no-cache 0 / mypy --strict 312 files 0 issues /
  lint-imports 8 kept 0 broken / full unpiped pytest 4674 passed 17 skipped 0 failed 0 xfailed exit 0 (one transient
  failure was the import-linter cache-hygiene contract catching the orchestrator's own non-`--no-cache` run — cache
  removed, test green: the contract working, not a bug); specs doctor exit 0 (0 errors) + backlog doctor clean exit 0.
  **Self-hosting reconcile (FR9 on the live instance):** the bug's damage was found LIVE on all 6 consumer repos
  (working-tree AGENTS.md clobbered + untracked CLAUDE.md bridge stubs — inflicted by the v0.1.58 reconcile and
  re-inflicted by the W3 propagation running pre-fix code); remediated by `git checkout -- AGENTS.md` ×6 + removal of
  the 6 untracked `@AGENTS.md` bridge stubs (tracked/operator files untouched); post-restore doctor exit 0 with
  **[foreign] ×12** (6 repos × AGENTS.md+CLAUDE.md); `public install --target all` left ALL hand-authored copies
  byte-identical (**0 [updated] / 12 [foreign] / self-repo [skip]** — vs the v0.1.58 ship that fanned [updated] to 6);
  confirming doctor exit 0 + [ok] public-privacy; consumer trees verified 0 AGENTS/CLAUDE deltas. No-plugin byte-lock
  held in-suite (golden (a)+(b) green). **QA ship gate: APPROVED** (handoff
  2026-07-05T003903Z-qa-engineer-v0160-ship-gate.handoff.json, validated — E2E 6/6 no-xfail, structural single
  authority verified, AC-1..15 all live, frozen no-steal suite zero-diff vs merge-base 96440487). No W1–W5 commit
  staged specs/backlog (verified). Security push-gate keyed to the pushed sha + CI watch recorded on the PR. Checklist:
  - **Unpiped** `pytest` (real exit) — full suite green; `ruff format --check`; `ruff check --no-cache`;
    `mypy --strict dadaia_workspace`.
  - `lint-imports --no-cache` → **`8 kept, 0 broken`**; ignore-cap UNCHANGED — the new `core/models/plugin_pack.py` +
    `core/protocols/plugin_store.py` are `core` leaves, and the `JsonPluginStore` adapter is consumed same-layer by
    `public_assets` (no new `features→infra` / `infra→features` edge); if any new edge is unavoidable, STOP and
    document (would fail AC-12).
  - `dadaia specs doctor` exit 0; `dadaia backlog doctor` exit 0.
  - **Self-hosting reconcile:** run in order — `dadaia public stage` → `dadaia public doctor` (surfaces any consumer
    write targets + confirms the pack staging) → `dadaia public install --target all` → confirming `dadaia public
    doctor` (`[ok] public-privacy`, exit 0). Confirm the v0.1.50 frozen no-steal suite is **zero-diff**. **FR9
    reconcile (bug fix on the live instance):** the pre-install `public doctor` must surface
    `[foreign] repos/<slug>:AGENTS.md` for any of the ~6 on-disk consumer repos carrying a hand-authored (no-banner)
    root `AGENTS.md`; the install leaves those byte-identical (NO `[updated]`, NO CLAUDE.md drop) — PM records the
    `[foreign]`/`[updated]`/`[ok]` split in the ship evidence and proves no hand-authored consumer `AGENTS.md` was
    clobbered (the v0.1.58 ship had fanned `[updated]` to 6 repos). *(PE surfaces these + the git commands to
    PM/operator or requests devops-engineer; PE runs no shell.)*
  - Confirm the **no-plugin byte-lock** holds on the live instance (a `public install`/`doctor` with no plugin installed
    is byte-identical to the T-60-10 golden).
  - QA ship-gate APPROVE; security push-gate keyed to the pushed sha; push; **watch CI until every job green**; PR;
    merge. No dead anchor this release → **no SHIP-time backlog archival** (both anchors survive → CLOSURE). Verify no
    W1–W5 commit staged `specs/backlog`.

## W7 — closure (CLOSURE phase)

- [ ] T-60-70 CLOSURE.md + memory truth + disposition + archive. Owner: product-engineer. Write set:
  `specs/releases/v0.1.60/CLOSURE.md`, `specs/memory/**`, `specs/_archive/v0.1.60/consumed-backlog/`, `ACTIVE.md`.
  Checklist:
  - Set `ACTIVE.md` phase = `CLOSURE`. Write `CLOSURE.md` (Summary, Tasks completed w/ SHAs, Validations triples,
    Drifts, Memory updates, Dispositions, Backlog returns, Archive decision).
  - **MEMORY (§SPEC 8):** `public-asset-distribution.md` → plugin staging/projection/ledger/doctor (primary);
    `agent-orchestration.md` → plugin agents carry behavior + plugin tier + two tier axes; assess a NEW
    `plugin-packs.md` atom vs fold; `tech-stack.md` → two tier axes + efficiency marker cadence; `architecture.md` →
    module map (`cli/commands/plugin.py`, `core/models/plugin_pack.py`, `core/protocols/plugin_store.py`,
    `infrastructure/json_plugin_store.py`, `public/plugins/`, precedence, efficiency check); `quality-assurance.md` →
    assess absent-pack golden + plugin-install E2E note. Regen `catalog.json` + `index.md` ONLY if
    `tldr`/`summary`/`area` change — **keep the regenerated `tldr` within the established length cap** so the catalog
    regen + `dadaia specs doctor` at W7 stays clean. `release_origin` → v0.1.60 on each edited atom.
  - **Backlog returns:** file `plugin-pack-content-libraries` (full skill corpora), `plugin-uninstall`,
    `fast-tier-persona-validation`, **`tier-taxonomy-rename`** (Ruling 17 — the eventual `tier:` → `dispatch_band:`
    frontmatter rename) (route through PM curation). Record in the CLOSURE `## Backlog returns`.
  - **Dispositions:** archive `plugin-packs-and-install-command` + `model-tier-efficiency-and-fast-tier-utilization` →
    `specs/_archive/v0.1.60/consumed-backlog/` + `consumed_backlog.json`; terminal status `DELIVERED — v0.1.60` (both
    anchors survive → CLOSURE archival). **Bug terminal event:** append `dadaia bugs append --bug-id
    public-install-clobbers-consumer-repo-agents-md --event resolved --release v0.1.60` (never dropped — solved by FR9;
    the `resolved` event is appended NOW at closure, not at definition). Record all in the CLOSURE `## Dispositions`
    table (bug row: `resolved` / evidence = the FR9 commit SHA + AC-14 test).
  - `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.60 → specs/_archive/releases/`
    (devops/operator); set `ACTIVE.md` → `release: none` (final release of the R9→R12 mandate); mark candidates R12 row
    **SHIPPED — v0.1.60**.
