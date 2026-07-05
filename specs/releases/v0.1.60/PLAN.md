# PLAN — v0.1.60 — Capability Tail (plugin packs + Layer-1 model-tier efficiency)

**Status:** Aprovado

Nine waves (W0–W7 + the inserted **W4B** for the reopened HIGH bug FR9). **FR1/FR2 (pack storage + the `dadaia plugin`
machinery) land FIRST**, captured **golden-first** so the
no-plugin `public install`/`public doctor` behaviour is byte-locked before any plugin-projection code. FR3
(`public_assets.py` projection + precedence) and FR4/FR5 (pack content, `public/**`) are separable by owner
(software-engineer machinery vs ai-engineer content) but share the `public_assets.py` projection path with W1/W2 →
those waves stay **sequential** (no parallel `[-]`) on `public_assets.py`. The model-tier waves (FR6/FR7) touch
disjoint files (`doctor`, memory, frontmatter docs) and can follow.

## Wave map

- **W0 — definition.** SPEC/PLAN/TASKS from the 2026-07-04 code read; mandatory release-definition grill on the picked
  set (report emitted); nine operator-unavailable ADRs (§9) + eight PM binding rulings (§0.1, Rulings 10-17, folding the
  dual-review REJECT ARCH-1..10 + QA-1..8); the DEFINITION-phase `architecture.md` L63 kanban drift-correction applied;
  `Aprovado` after dual **re-verify**; definition commit. Owner: product-engineer (orchestrated).

- **W1 — FR1/FR2 pack storage + `dadaia plugin` machinery (golden-first, ports-and-adapters).**
  1. **Golden (a) capture FIRST (Ruling 14 / ARCH-4 / QA-2).** <!-- AMEND:ARCH-4 --> <!-- AMEND:QA-2 --> Capture the
     **pre-descriptor** `public_assets.install()` (all targets) + full `public_assets.doctor()` report list on the
     current tree under `FileSystemPublicAssetManager` + `tmp_path`. **Normalization from day one = v0.1.55
     path/version + clock-freeze PLUS the v0.1.58 three-leak-class layer** the doctor surface carries: (1) host-state
     cwd-walk (`_check_public_privacy` denylist) → host-state canonicalization; (2) directory-iteration order (`.pi/`
     lines) → sorted-multiset lock; (3) OS-phrased exec-probe text → OS-phrase canonicalization. Golden (a) is the
     **transient refactor-lock** through the `public_assets` internal changes (retired at ship). Commit BEFORE any
     descriptor/projection code. (Golden (b), the durable descriptors-present baseline, is captured in W2.)
  2. **Pack layout** (`ai-engineer` seeds `public/plugins/<pack>/pack.json` + empty agents/skills/rules dirs; content
     bodies land in W3). `frontend-design` + `devops` descriptors.
  3. **Ports-and-adapters seam (A-seam, blocking):** NEW `core/models/plugin_pack.py` (`PluginPack`, NO I/O) + NEW
     `core/protocols/plugin_store.py` (`PluginStore` port) + NEW `infrastructure/json_plugin_store.py` (`JsonPluginStore`
     adapter, mirrors `json_harness_profile_store.py`). Forbid a new `features→infra` / `infra→features` edge.
  4. **CLI** NEW `cli/commands/plugin.py` (`install <pack>`/`list`/`doctor`) registered in `cli/main.py`; bad pack →
     Click `BadParameter` (width-independent stderr, `_norm_stderr`-normalized per QA-7).
  - Tests: AC-1 golden (a) committed; AC-2 seam (import-linter clean, ignore-cap unchanged); AC-3 CLI surface +
    bad-value stderr (RED-first: no `plugin` command pre-fix). **W1 mutation-sanity NOW (QA-6):** <!-- AMEND:QA-6 -->
    AC-11(0a) make `install` accept any pack ⇒ AC-3 exit-2 test FAILS; AC-11(0b) drop a `JsonPluginStore` ledger field ⇒
    the adapter round-trip FAILS — captured on the T-60-11 line, not blanket-deferred. AC-13 file-enumerated ledger. NO
    `specs/backlog/**`.

- **W2 — FR3 pack projection + ledger + manifest + precedence (sequential on `public_assets.py`).**
  0. **Golden (b) capture (Ruling 14 / ARCH-4).** <!-- AMEND:ARCH-4 --> With the W1 pack descriptors present but BEFORE
     any projection/precedence code, capture the durable **"descriptors-present, zero-plugin-installed"** golden (b)
     (same three-leak normalization as golden (a)). The added `stage:plugins/...` descriptor-source parity lines are
     captured INTO golden (b) (not a violation); AC-5 byte-equality is scoped to the runtime-projection + install-set
     lines against golden (b).
  1. **`dadaia plugin install`** projects the pack's agents/skills/rules from `.dadaia/agentic/plugins/<pack>/` into the
     runtime projections, hash-compare; records `installed_plugins.json` via the W1 adapter; idempotent.
  2. **Profile-scoped projection (Ruling 13 / ARCH-3, blocking).** <!-- AMEND:ARCH-3 --> Projection, precedence AND
     plugin doctor scope to the workspace harness profile via the same `_profile_harnesses` seam already in
     `public_assets` (absent profile ⇒ all targets, v0.1.58 back-compat): a claude-only workspace projects only the
     claude agent (no `.codex/` orphan); a later out-of-profile pack asset on disk surfaces via the v0.1.58 A3
     never-silent law. `installed_plugins.json` records the pack (not per-harness).
  3. **Stub replacement (ADR-4)** — pack agent body overwrites the projected core stub.
  4. **Projection precedence (blocking)** — core `public_assets.install` reads `installed_plugins.json` and projects the
     pack body (not the stub) for installed plugins, within the profile scope.
  5. **Manifest tracking** of pack-projected files; **doctor** (`plugin doctor` / folded `public doctor`) reports
     `[ok]`/`[drift]`/`[missing]` per pack file; a stale installed-pack file is never silent.
  - Tests: AC-3 real-body install (RED-first) + idempotent; AC-4 clobber-safety (RED-first: core install re-writes stub
    pre-fix); AC-5 **byte-equality vs golden (b)** + non-silent stale file; **AC-15 profile×pack** (claude-only projects
    no `.codex/` orphan; precedence honors the scope). AC-11(a)(b)(c) sabotages. AC-13 ledger. NO `specs/backlog/**`.

- **W3 — FR4/FR5 enumerated pack content + plugin-scope rewrite + plugin tier (ai-engineer, `public/**`).**
  1. **3 real agent bodies** at `public/plugins/<pack>/agents/<name>.md` — full frontmatter
     (`name`/`description`/`tier: 3`/`model: claude-sonnet-4-6`/tools) + real SDD-role body.
  2. **Enumerated skills — ONE per pack, no more (Ruling 12 / ARCH-5).** <!-- AMEND:ARCH-5 --> `frontend-design` →
     `public/plugins/frontend-design/skills/browser-frontend-implementation/SKILL.md`; `devops` →
     `public/plugins/devops/skills/github-actions-cicd/SKILL.md`. **Zero** new rules beyond FR5. Reference (do NOT
     duplicate) the existing codex `frontend-ctx`/`design-ctx` adapters. Everything beyond → `plugin-pack-content-libraries`.
  3. **Rewrite `public/rules/plugin-scope.md`** + the `[PLUGIN REQUIRED]` response to install-gated wording; record the
     retired `panel-ux-overhaul` deviation class (doc note).
  - Tests: AC-6 content generic + **Codex `model`-field tiered** (`.codex/agents/<name>.toml` renders `gpt-5.3-codex`,
    NOT `gpt-5.5`; the `model_reasoning_effort` is NOT the discriminator — ARCH-2) + `[ok] public-privacy` + exactly the
    two named skills present; AC-7 install-gated grep (RED-first) — retired wording gone from the projected rule.
    AC-11(d) + **AC-11(f) Codex `model`-field sabotage** (opus ⇒ `gpt-5.5` ⇒ FAILS). <!-- AMEND:ARCH-2 --> AC-13 ledger.
    NO `specs/backlog/**`.

- **W4 — FR6/FR7 tier-taxonomy fix + efficiency-audit trigger (software-engineer, disjoint files).**
  1. **Efficiency-audit trigger — `DoctorIssue` EFF-1, NOT a `[warn]` token (Rulings 10/11 / ARCH-6/7 / QA-3).**
     <!-- AMEND:ARCH-6 --> <!-- AMEND:ARCH-7 --> <!-- AMEND:QA-3 --> Add a `DoctorService` check emitting
     `DoctorIssue(code="EFF-1", fixable=False, description=...)` reading `.dadaia/states/last_efficiency_audit.json`
     (schema `{schema_version,last_efficiency_audit,by,report}`) against the named constant
     `EFFICIENCY_AUDIT_STALE_DAYS = 30`. Matrix: absent ⇒ no issue (preserves fresh-workspace happy path); fresh ⇒ no
     issue; stale ⇒ EFF-1; malformed ⇒ EFF-1 "malformed marker" (no crash). The bare `dadaia doctor` exit stays 0
     (already never exits non-zero on issues). **Writer:** add `dadaia reports mark-efficiency-audit --report <path>
     [--by <agent>]` (one verb under the existing `reports` group) that writes the marker with the current RFC3339
     timestamp — the production clear path.
  2. **Tier-taxonomy — MANDATORY contract (Ruling 17 / ARCH-9 / QA-8a).** <!-- AMEND:ARCH-9 --> <!-- AMEND:QA-8 -->
     NON-OPTIONAL `tests/contract/test_agent_tier_taxonomy.py` asserting every non-plugin core agent carries a numeric
     `tier` + a registry-known `model`, and the 3 plugin agents carry `tier: 3` + `model: claude-sonnet-4-6`.
     Documentation lands in memory at W7; the eventual rename is `tier-taxonomy-rename` (W7 backlog return).
  - Tests: AC-8 EFF-1 4-case matrix (absent/fresh/stale/malformed — RED-first: no `DoctorService` EFF-1 check pre-fix);
    AC-9 MANDATORY taxonomy contract; **T-60-40 fate ledger must enumerate the existing doctor tests exposed to the
    default-on signal (QA-3) — and prove they stay green because absent ⇒ no issue** (e.g. `tests/integration/test_cli_doctor.py`,
    fresh-workspace e2es). AC-11(e) sabotage (skip the EFF-1 check ⇒ AC-8 stale test FAILS). AC-13 ledger. NO
    `specs/backlog/**`.

- **W4B — FR9 provenance-gated consumer-repo fan-out (HIGH bug fix; AMENDS v0.1.58 Ruling L; software-engineer).**
  Disjoint file (`infrastructure/workspace_guardrail.py`) — independent of the `public_assets.py` plugin path.
  1. **Banner discriminator = MODULE CONSTANT + contract test (Ruling 15 / QA-1).** <!-- AMEND:QA-1 --> Add
     `_CANONICAL_AGENTS_BANNER` (fixed literal, the `public/data/AGENTS.md` banner block) to `workspace_guardrail.py` +
     the contract test `test_agents_banner_constant_matches_public_data` asserting byte-equality with the actual
     `public/data/AGENTS.md` banner (NO runtime read of `public/data`). In `_write_one`, gate the divergent-consumer
     overwrite on a match against the constant: banner-match → restore + `[updated]`; no banner → `[foreign] <path> —
     left untouched`; absent → create + `[ok]`. The `CLAUDE.md` bridge is written only when its sibling `AGENTS.md` is
     created/restored (no orphan drop).
  2. **Doctor provenance-aware ON THE PAIR (Ruling 16 / ARCH-1 — CRITICAL).** <!-- AMEND:ARCH-1 --> `_doctor_guardrail_pair`
     makes BOTH lines provenance-aware: when the consumer `AGENTS.md` is `[foreign]` (no banner), the paired `CLAUDE.md`
     line is **also `[foreign]`** whether the CLAUDE.md is absent OR a foreign non-stub — never `[missing]`/`[drift]`,
     so `public doctor` (which exits 1 on any `[missing]`/`[drift]`, `public.py:161-172`) **exits 0** for a hand-authored
     repo. A banner-bearing (canonical) copy keeps `[ok]`/`[drift]`/`[missing]` on both lines.
  - **RED-first (against the pre-fix `workspace_guardrail.py`):** a **registered** hand-authored consumer `AGENTS.md`
    is overwritten with the generic copy (`[updated] ... (overwrote divergent workspace-law copy)`, the bug); post-fix
    it survives byte-identical with both paired doctor lines `[foreign]` + `public doctor` exit 0. A **stale canonical**
    (banner-bearing) fixture still gets `[updated]`.
  - **v0.1.58 test-pin adjudication — FULL FLIP SET (Ruling 15 / QA-1; QA-gate flag, do not silently rewrite):**
    <!-- AMEND:QA-1 --> under the module-constant banner, EVERY consumer copy projected from a **synthetic bannerless
    source** reclassifies `[foreign]`. Enumerate per file the concrete affected cases (not one case per file), each
    adjudicated INVARIANT-or-amended with rationale (re-fixture the source to EMBED `_CANONICAL_AGENTS_BANNER` to keep
    a canonical classification):
    - `tests/unit/infrastructure/test_consumer_fanout.py`: `test_doctor_reports_ok_for_fresh_consumer` (`[ok]`→`[foreign]`
      unless bannered), `test_doctor_flags_drift_for_stale_consumer` (`[drift]`→`[foreign]`),
      `test_divergent_consumer_root_restored_with_updated_line` (bannerless divergent → `[foreign]`; re-fixture WITH the
      banner to keep `[updated]`).
    - `tests/unit/features/public/test_workspace_guardrail_pair.py`: **Case 6 `test_doctor_four_line_output`** — a
      **doctor-`[ok]`-parity** flip (`[ok]`→`[foreign]`), NOT an `[updated]`-on-divergent case (the ledger's earlier
      description was misattributed — QA-1 correction).
    - `tests/unit/infrastructure/test_public_assets.py::TestInstallConsumerReposGuardrailPair::test_force_false_overwrites_divergent_consumer_with_updated_line`
      (@ L748) — the **real `[updated]`-on-divergent INSTALL pin**; re-fixture the source WITH the banner to keep the
      `[updated]` assertion.
    - `tests/integration/test_public_doctor_parity.py` (consumer fan-out `[ok]`/`[drift]` doctor cases → `[foreign]`
      unless bannered; also add the PAIRED CLAUDE.md `[foreign]` assertion).
    A byte diff on a Ruling-L pin is a **deliberate amendment**, recorded, never a silent regeneration. Frozen v0.1.50
    no-steal suite untouched — confirm zero-diff.
  - Tests: AC-14 (**registered** fixture — QA-4; hand-authored survives byte-identical, BOTH paired doctor lines
    `[foreign]`, `public doctor` exit 0; stale canonical → `[updated]`; absent → `[ok]`) + the banner contract test.
    AC-11(g) sabotage (drop the banner discriminator ⇒ AC-14 FAILS against the registered fixture). AC-13
    file-enumerated ledger (incl. the full-flip-set adjudication). NO `specs/backlog/**`.

- **W5 — FR (all) per-pack sandboxed E2E (qa-engineer).** <!-- AMEND:QA-4 --> <!-- AMEND:QA-5 -->
  1. A sandboxed E2E scaffolding in-process via `CliRunner.invoke`: (a) fresh no-plugin → stubs +
     descriptors-present-zero-plugin doctor green + golden (b) byte-lock; (b) `plugin install frontend-design` → both
     agents real + ledger + doctor green; (c) `plugin install devops` → `devops-engineer` real; (d) following core
     `public install --target all` keeps pack bodies (AC-4); **(e/FR9)** a **registered** (in `spec_contexts.json` via
     `_register_context`/`_write_registry` — QA-4) consumer repo with a hand-authored root `AGENTS.md` survives
     byte-identical (**BOTH** paired doctor lines `[foreign]`), and a real `dadaia public doctor` run **EXITS 0** (the
     v0.1.58 perpetual-`[drift]`+exit-1 guard) while a stale-canonical fixture gets `[updated]`; **(f)** double
     `plugin install frontend-design` no-ops (`installed_plugins.json` unchanged — ledger idempotency); **(g)**
     `installed_plugins.json` coexists with `harness_profile.json`/overlay state (profile×pack). `tmp_path` isolation +
     `-p no:cacheprovider`; **wall-time ≤ ~10s** (v0.1.58 ~6s precedent — a concrete bound, not a placeholder).
  - Tests: AC-10 (a)-(g) scenarios. AC-11 discriminating sabotage (projection/precedence/banner) against the registered
    fixture. AC-13 ledger. NO `specs/backlog/**`.

- **W6 — gates + ship.** Full local gates (AC-12): unpiped `pytest` + `ruff format --check` + `ruff check --no-cache` +
  `mypy --strict` + `lint-imports --no-cache` (8 kept / 0 broken; ignore-cap UNCHANGED — the new `core` leaf + adapter
  add no edge) + `dadaia specs doctor` + `dadaia backlog doctor`. **Self-hosting reconcile:** `dadaia public stage` →
  `dadaia public doctor` → `dadaia public install --target all` → confirming `dadaia public doctor`
  (`[ok] public-privacy`, exit 0); confirm the v0.1.50 frozen no-steal suite is **zero-diff**. **FR9 ship note:** the
  v0.1.58 ship reconcile fanned `[updated]` to 6 on-disk consumer repos; under FR9 the pre-install `public doctor` must
  now surface `[foreign] repos/<slug>:AGENTS.md` for any consumer repo carrying a hand-authored (no-banner) root
  `AGENTS.md`, and the install must leave those byte-identical (no `[updated]`, no CLAUDE.md drop) — PM records the
  surfaced `[foreign]`/`[updated]`/`[ok]` split in the ship evidence, and any repo whose root `AGENTS.md` was
  hand-authored is proven untouched. QA ship-gate; security push-gate keyed to the pushed sha; push; **watch CI until
  every job green**; PR; merge. *(PE runs no shell — surfaces the stage/doctor/install/doctor + git commands to
  PM/operator or requests devops-engineer.)*

- **W7 — closure (CLOSURE phase).** `ACTIVE.md` phase = `CLOSURE`; CLOSURE.md (Summary, Tasks + SHAs, Validations
  triples, Drifts, Memory updates, Dispositions, Backlog returns, Archive). MEMORY (§SPEC 8):
  `public-asset-distribution.md` (plugin staging/projection/ledger/doctor — primary); `agent-orchestration.md` (plugin
  agents carry behavior; plugin tier; two tier axes); assess a NEW `plugin-packs.md` atom vs fold; `tech-stack.md`
  (two tier axes + efficiency marker cadence); `architecture.md` (module map + `public/plugins/` + precedence +
  efficiency check); `quality-assurance.md` (absent-pack golden + plugin-install E2E — assess). Regen `catalog.json` +
  `index.md` only if `tldr`/`summary`/`area` change — keep regenerated `tldr` within the length cap. `release_origin` →
  v0.1.60 on each edited atom. **Backlog returns:** file `plugin-pack-content-libraries`, `plugin-uninstall`,
  `fast-tier-persona-validation`, **`tier-taxonomy-rename`** (Ruling 17) (route through PM curation). **Dispositions:**
  archive
  `plugin-packs-and-install-command` + `model-tier-efficiency-and-fast-tier-utilization` →
  `specs/_archive/v0.1.60/consumed-backlog/` + `consumed_backlog.json` (`DELIVERED — v0.1.60`; both anchors survive →
  CLOSURE archival); **append the bug terminal event** `dadaia bugs append --bug-id
  public-install-clobbers-consumer-repo-agents-md --event resolved --release v0.1.60` (never dropped — solved by FR9).
  `dadaia specs doctor` clean; request `git mv specs/releases/v0.1.60 → specs/_archive/releases/`
  (devops/operator); set `ACTIVE.md` → `release: none`; mark candidates R12 row **SHIPPED — v0.1.60**.

## Write sets (disjoint per wave; shared files force sequential order)

| Wave | Files |
|---|---|
| W1 | NEW `core/models/plugin_pack.py`; NEW `core/protocols/plugin_store.py`; NEW `infrastructure/json_plugin_store.py`; NEW `cli/commands/plugin.py`; `cli/main.py` (register); NEW `public/plugins/{frontend-design,devops}/pack.json` (+ empty dirs); NEW golden test `tests/unit/infrastructure/test_plugin_install_goldens.py` + golden (a) (three-leak-normalized); NEW `tests/unit/core/test_plugin_pack.py`, `tests/unit/infrastructure/test_json_plugin_store.py`, `tests/unit/cli/test_plugin_cli.py` |
| W2 | `infrastructure/public_assets.py` (plugin projection + **profile-scope (ARCH-3)** + precedence + doctor); `infrastructure/public_assets_common.py` (only if a plugin route constant is needed); NEW `tests/integration/test_plugin_projection.py` (real stage/install → integration layer, QA-8b) + golden (b) |
| W3 | NEW `public/plugins/frontend-design/agents/{frontend-engineer,design-specialist}.md` + `public/plugins/frontend-design/skills/browser-frontend-implementation/SKILL.md`; NEW `public/plugins/devops/agents/devops-engineer.md` + `public/plugins/devops/skills/github-actions-cicd/SKILL.md`; `public/rules/plugin-scope.md` (rewrite); NEW `tests/unit/infrastructure/test_plugin_content.py` (frontmatter/tier/Codex-model-field) |
| W4 | the workspace-`doctor` service module (`features/spec_context/doctor.py` — new EFF-1 `DoctorIssue` check) + `EFFICIENCY_AUDIT_STALE_DAYS` constant; `cli/commands/reports.py` (NEW `mark-efficiency-audit` verb) + its marker-writer helper; NEW `tests/unit/.../test_efficiency_audit_trigger.py` (absent/fresh/stale/malformed) + `tests/unit/cli/test_reports_mark_efficiency_audit.py`; **MANDATORY** `tests/contract/test_agent_tier_taxonomy.py` |
| W4B | `infrastructure/workspace_guardrail.py` (`_CANONICAL_AGENTS_BANNER` constant + `_write_one` banner-match gate + `_doctor_guardrail_pair` **PAIRED** `[foreign]`); NEW `tests/unit/infrastructure/test_consumer_fanout_provenance.py`; NEW contract `tests/contract/test_agents_banner_constant_matches_public_data.py`; ADJUDICATED (QA-gate, full flip set — QA-1): `tests/unit/infrastructure/test_consumer_fanout.py`, `tests/unit/features/public/test_workspace_guardrail_pair.py` (Case 6 doctor-parity flip), `tests/unit/infrastructure/test_public_assets.py::TestInstallConsumerReposGuardrailPair` (`test_force_false_overwrites_divergent_consumer_with_updated_line`), `tests/integration/test_public_doctor_parity.py` |
| W5 | `tests/e2e/features/test_plugin_pipeline.py` (or a sibling of `test_public_pipeline.py` reusing its helpers) — incl. the FR9 **registered** hand-authored/stale-canonical consumer fixtures + double-install + profile×pack + doctor-exit-0 |
| W6 | (gates + `public stage/install/doctor`; self-hosting reconcile; no `specs/**` change) |
| W7 | `specs/releases/v0.1.60/CLOSURE.md` + `specs/memory/**` + `specs/_archive/v0.1.60/consumed-backlog/` + `ACTIVE.md` |

**`public_assets.py` shared W2 only** (W1 does not touch it beyond the CLI wiring; the projection lives in W2) —
still sequenced after W1's adapter lands (W2 reads `JsonPluginStore`). **`public/**` content is W3 only** (ai-engineer).
**The workspace-doctor efficiency check is W4 only.** **No parallel `[-]`** on `public_assets.py`.

## Test strategy

- **Golden-first — TWO goldens, three-leak normalization from day one (Ruling 14 / ARCH-4 / QA-2).**
  <!-- AMEND:ARCH-4 --> <!-- AMEND:QA-2 --> golden (a) = pre-descriptor refactor-lock (W1, retired at ship); golden (b)
  = durable descriptors-present zero-plugin baseline (W2). BOTH carry the **consolidated platform-invariance
  normalization** the `public_assets.doctor()` surface needs: v0.1.55 path/version + clock-freeze PLUS the v0.1.58
  three leak classes — (1) host-state cwd-walk (`_check_public_privacy` denylist) → canonicalized; (2)
  directory-iteration order (`.pi/` lines) → sorted-multiset lock; (3) OS-phrased exec-probe text → OS-phrase
  canonicalization. Silence on normalization is a finding (axis-2). Fix-the-consumer-never-the-golden.
- **RED-first for new behaviour (FR2–FR9).** Each new capability's test asserts the post-fix behaviour and is shown to
  FAIL against the pre-fix tree: no `plugin` command; core install re-clobbers the stub; stale installed-pack file
  reads silent; plugin-scope still says "no install command exists"; no `DoctorService` EFF-1 check; pre-fix
  `_write_one` clobbers a registered hand-authored consumer `AGENTS.md`.
- **Width-independent stderr asserts (QA-7).** `plugin install bogus` asserted via `_norm_stderr`-normalized
  `result.stderr` substring + `exit_code == 2` + empty `result.stdout`; no `mix_stderr` kwarg on `CliRunner` (v0.1.57
  QA-atom law / Click 8.2+).
- **Byte-golden scope.** The descriptors-present zero-plugin doctor path asserts **byte-equality vs golden (b)** on the
  runtime-projection + install-set lines (the `stage:plugins/...` descriptor-source lines are captured into golden (b)).
- **Test-layer taxonomy (QA-8b).** <!-- AMEND:QA-8 --> real stage/install/doctor exercises belong in the
  `integration` layer, not `unit` (5-layer taxonomy). `test_plugin_projection.py` and the golden tests are
  `integration`; the banner-constant and tier-taxonomy checks are `contract`; `test_plugin_pack.py`/`test_json_plugin_store.py`
  stay `unit`. Confirm the layer marker on each new test or explicitly ratify any infra-`unit` precedent.
- **AC-11 mutation-sanity per new test** (0a,0b,a–g): one-line sabotage ⇒ FAIL, captured on the task line, reverted.
  W1 seam/CLI tests are born falsifiable NOW (QA-6), not blanket-deferred.
- **AC-13 surviving/dead ledger per wave — FILE-ENUMERATED**; greps include `tests/` + textual/docstring refs.
- **Frozen suite:** the v0.1.50 no-steal lease/gate suite is untouched (this release never enters
  `spec_context`/lease/gate) — confirm zero-diff.
- **E2E (W5) — in-process.** the per-pack E2E scaffolds in-process via `CliRunner.invoke` (NOT a subprocess); `tmp_path`
  isolation (no `.dadaia/` inside a repo) + `-p no:cacheprovider`; **wall-time ≤ ~10s** (concrete bound, QA-5); the FR9
  consumer fixture is **registered** in `spec_contexts.json` (QA-4) so the fan-out reaches it and AC-11(g) can go RED.
- Full **unpiped** `pytest` + ruff + `mypy --strict` + `lint-imports --no-cache` + `specs doctor` + `backlog doctor` +
  `public doctor` locally before push (AC-12).

## Platform seam note (3-OS CI)

Any filesystem/path work (pack staging/projection, `installed_plugins.json` read/write, efficiency marker) respects the
platform seam: paths via `pathlib`, `os.sep` normalization in goldens, the `core/platform.py` singleton for any OS
branch, stdlib `json` for the ledger/marker. No symlink work is introduced. The E2E `tmp_path` scaffolds are OS-agnostic.

## Rollback

Single feature branch `feature/v0.1.60` (base v0.1.59 closure). FR1/FR2 add a new command group + core model + port +
adapter + pack descriptors (revert = remove the new files). FR3 makes `public_assets` plugin-aware behind the no-plugin
byte-golden (revert = remove the plugin projection + precedence; no-plugin behaviour is unchanged by construction). FR4/
FR5 add `public/plugins/**` content + rewrite one rule (revert restores the stub language). FR6 adds a mandatory tier
contract test; FR7 adds an EFF-1 `DoctorIssue` check + the `mark-efficiency-audit` writer (revert = remove both). No
data migration; `installed_plugins.json` + `last_efficiency_audit.json` are additive-optional (absent ⇒ no plugins /
no EFF-1). The only irreversible-ish step is `public install` on the live
instance (re-run stage/install/doctor to reconcile). CLOSURE dispositions are recoverable by reverting the closure
commit.
