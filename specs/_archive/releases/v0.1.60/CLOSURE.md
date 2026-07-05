# Closure: Release — v0.1.60 — Capability Tail (plugin packs + Layer-1 model-tier efficiency)

> **Status:** Aprovado
> **Release ID:** v0.1.60
> **Owner:** product-engineer
> **Closed:** 2026-07-04
> **Branch:** `feature/v0.1.60` · **Base:** v0.1.59 closure · **Merged:** `4ccc6a21` (PR #110, squash of `feature/v0.1.60`) · **Closure branch:** `closure/v0.1.60`
> **Ship gates:** qa-engineer **APPROVED** (handoff `2026-07-05T003903Z-qa-engineer-v0160-ship-gate.handoff.json`, validated — E2E 6/6 no-xfail, AC-1..15 all live, structural single-authority verified, frozen no-steal suite zero-diff vs merge-base `96440487`) · security-reviewer **APPROVED** (push-gate keyed to the pushed ref sha) · CI **35 checks pass / 3 condition-skip, 0 failures** on PR #110.
> **Mandate:** R12 of the operator-approved 12-release plan — the **final** release of the R9→R12 continuation mandate. With this ship the **R1–R12 plan is complete.**

## Summary

v0.1.60 is the "Capability Tail" — a pure-new-capability release that turns the three
behavior-less plugin stubs (`frontend-engineer`, `design-specialist`, `devops-engineer`)
into real, installable agents and assigns a demonstrable non-opus Layer-1 model tier where
it is safe. It ships a real **`dadaia plugin install/list/doctor`** CLI backed by
in-package packs (`public/plugins/frontend-design/` + `public/plugins/devops/`), a
per-workspace **`installed_plugins.json`** ledger, profile-scoped pack projection with
core-install **precedence** (a later `public install` never reverts an installed pack back
to its stub), and a `plugin doctor` surface — all riding the v0.1.58 ports-and-adapters
precedent (`PluginPack`/`InstalledPlugins` core model + `PluginStore` port + `JsonPluginStore`
infra adapter). The `plugin-scope` rule and the three stub bodies became install-gated
wording, retiring the `panel-ux-overhaul` plugin-scope deviation class going forward.

On the model-tier axis the release stays honest to the grill's finding that Layer-1 has no
fine-grained sub-task tiering (only whole-persona `model:` assignment) and that the deep
tier (`claude-fable-5`) is region-locked: it ships the **demonstrable off-opus assignment**
(the three real plugin agents on the registry `plugin`/sonnet tier — Codex renders
`gpt-5.3-codex`, not the opus `gpt-5.5`), a **mandatory tier-taxonomy contract** that
machine-enforces the two independent "tier" axes (numeric frontmatter dispatch band vs
registry model-cost class), and a **recurring efficiency-audit trigger** (a deterministic
`DoctorIssue(code="EFF-1")` on the existing workspace doctor with a 30-day cadence constant
and a `dadaia reports mark-efficiency-audit` clear-path writer). The fast/haiku
reasoning-persona downgrade was deferred (no live operator to validate equal quality).

Mid-release a **HIGH data-loss bug reopened into the pick** — `dadaia public install`'s
consumer `AGENTS.md` fan-out (v0.1.58 FR4 Ruling L) clobbered a repo's hand-authored root
`AGENTS.md`. FR9 root-caused it: the fan-out had no discriminator between a stale canonical
projection and hand-authored content. The fix is a provenance discriminator (a byte-equal
contract-tested `_CANONICAL_AGENTS_BANNER` module constant) — banner-bearing consumer copies
are restored (`[updated]`), everything else is `[foreign]` and left untouched — extended to
the paired `CLAUDE.md` doctor line so a hand-authored consumer repo yields `[foreign]` on
both lines and `public doctor` exits 0. A **second HIGH bug surfaced by the W5 E2E** —
the FR9 provenance gate had shipped as dead code (the real `manager.doctor()` never called
it; the unit test proved nothing because it called the helper directly) — was root-caused by
extracting the consumer classification into a single authority that the real doctor calls.
Both bugs are resolved this release; the live instance's damage (found on all six consumer
repos) was remediated at ship, and the live reconcile now fans **0 `[updated]` / 12
`[foreign]` / self-repo skip** with `public doctor` exit 0.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-60-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-04 code read + mandatory grill; DEFINITION-phase `architecture.md` L63 kanban drift-correction; 9 operator-overridable ADRs; dual review REJECT (ARCH-1..10 + QA-1..8) folded via 55 `<!-- AMEND -->` markers + 8 PM Rulings 10-17; `Aprovado` after dual re-verify | (definition, squash `4ccc6a21`) |
| T-60-10 | W1 FR1/FR2 — golden (a) (pre-descriptor refactor-lock, integration layer, three-leak normalized) captured BEFORE descriptors | `a03e7474` (squash `4ccc6a21`) |
| T-60-11 | W1 — ports-and-adapters seam (`PluginPack`/`InstalledPlugins` + `PluginStore` port + `JsonPluginStore`) + `dadaia plugin` CLI + pack descriptors; W1 mutation-sanity (0a/0b); three v0.1.58 goldens amended (STOP, Drift 1) | `23eff95d` (squash `4ccc6a21`) |
| T-60-20 | W2 FR3 — golden (b) (descriptors-present baseline) + `install_plugin` projection + profile-scope + stub replacement + core-install precedence + `plugin doctor`; AC-3/4/5/15 | `fbc261bd` (golden b) · `ea665708` (projection) (squash `4ccc6a21`) |
| T-60-30 | W3 FR4/FR5 — 3 real agent bodies (`tier: 3`, `model: claude-sonnet-4-6`) + 2 enumerated skills (`browser-frontend-implementation`, `github-actions-cicd`) + install-gated `plugin-scope.md` rewrite; W5 follow-up: 3 stub bodies re-worded (Drift 4) | `7033d628` (content) · `6c5e06d6` (stub-wording follow-up) (squash `4ccc6a21`) |
| T-60-40 | W4 FR6/FR7 — EFF-1 `DoctorIssue` (`EFFICIENCY_AUDIT_STALE_DAYS = 30`, 4-case matrix) + `dadaia reports mark-efficiency-audit` writer + MANDATORY `test_agent_tier_taxonomy.py` | `2a26aca6` (squash `4ccc6a21`) |
| T-60-45 | W4B FR9 — `_CANONICAL_AGENTS_BANNER` constant + banner-match `_write_one` + PAIRED provenance-aware doctor + banner contract test + full flip-set adjudication; FIX ROUND: single consumer-classification authority wired into the real `manager.doctor()` (2nd HIGH bug) | `f6a28373` (fix) · `3f77283a` (fix-round wire) (squash `4ccc6a21`) |
| T-60-50 | W5 — per-pack in-process E2E (6 tests, ~7.7s); scenarios (a)-(g); registered hand-authored consumer fixture; strict-xfail regression lock that surfaced the 2nd HIGH bug | `b9c588b4` (squash `4ccc6a21`) |
| T-60-60 | W6 — full local gates + self-hosting reconcile (live-instance FR9 remediation: 0 `[updated]` / 12 `[foreign]`); QA ship gate; security push gate; push; CI watch; PR #110; merge | ship evidence `02d00a50` (squash `4ccc6a21`) |
| T-60-70 | W7 closure — this CLOSURE.md + memory truth (new `plugin-packs.md` atom + 5 edited atoms) + disposition sweep + 4 backlog returns + candidates R12 → SHIPPED | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the W6 ship tree (`02d00a50`) and re-verified on merged PR #110 (`4ccc6a21`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-12 full suite green (unpiped, real exit) | `pytest -p no:cacheprovider` (no pipe) | `4674 passed, 17 skipped, 0 failed, 0 xfailed, exit 0` — ship tree `02d00a50`; QA ship-gate handoff `2026-07-05T003903Z-qa-engineer-v0160-ship-gate` (one transient failure was the import-linter cache-hygiene contract catching a non-`--no-cache` run — cache removed, green: the contract working, not a bug) |
| AC-12 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 — W6 |
| AC-12 types clean | `mypy --strict dadaia_workspace` | exit 0, **312 files** — W6 |
| AC-2/AC-12 import contracts + ignore-cap unchanged | `lint-imports --no-cache` | `8 kept, 0 broken`; ignore-cap **26 UNCHANGED** every wave (the `core` leaves + same-layer `JsonPluginStore` adapter add no edge) — W1..W6 |
| AC-1 golden (a) — pre-descriptor refactor-lock (three-leak normalized) | `pytest tests/integration/test_plugin_install_goldens.py` | green on the pre-descriptor tree (`a03e7474`); byte-stable across T-60-11's `pack.json` (its `stage:plugins/*` filter holds) — W1 |
| AC-5 golden (b) — descriptors-present zero-plugin byte-lock | `pytest tests/integration/test_plugin_projection.py` | golden (b) captured BEFORE projection code (`fbc261bd`); after projection, the zero-plugin path is byte-identical (the plugin projection/doctor helpers are strict no-ops when the ledger is absent) — W2 |
| v0.1.58 goldens AMENDED (deliberate, per PM ruling) | `UPDATE_INSTALL_GOLDENS` on each test | `install_target_resolution_v0158.json` (+5 `[stage] .../plugins`) + `doctor_all_four_v0158.json` (+8 `[ok] stage:plugins/*`), rigorous Counter-diff = EXACTLY the added lines, ZERO other delta / ZERO removals; `panel_runtime_validation_v0158.json` untouched — W1 (Drift 1) |
| AC-3/AC-6 real body + off-opus Codex tier | `pytest tests/integration/test_plugin_projection.py` · `test_plugin_content.py` | installed pack agent's `.codex/agents/<name>.toml` renders `model = "gpt-5.3-codex"` (plugin/sonnet), NOT `gpt-5.5` (opus); `.claude/agents/<name>.md` carries the real body (not `[PLUGIN REQUIRED]`); `[ok] public-privacy` — W2/W3 |
| AC-4/AC-15 precedence + profile×pack | `pytest tests/integration/test_plugin_projection.py` | core `public install --target all` keeps the pack body (precedence); claude-only profile projects NO `.codex/` orphan; ledger records the pack (not per-harness) — W2 |
| AC-8 EFF-1 4-case matrix | `pytest .../test_efficiency_audit_trigger.py` · `test_reports_mark_efficiency_audit.py` | absent ⇒ no issue; fresh ≤30d ⇒ no issue; stale >30d ⇒ EFF-1; malformed ⇒ EFF-1 "malformed marker" (no crash); bare `dadaia doctor` exit 0; writer round-trip clears EFF-1 — W4 |
| AC-9 MANDATORY tier-taxonomy contract | `pytest tests/contract/test_agent_tier_taxonomy.py` | 9 core carry numeric `tier` + registry `model == claude-opus-4-8` (`dispatch`); 3 plugin bodies carry `tier: 3` + `model: claude-sonnet-4-6` (`plugin`); roster pinned 9/3 — W4 |
| AC-14 FR9 provenance (RED-first, registered fixture) | `pytest .../test_consumer_fanout_provenance.py` · banner contract | RED (fix `git stash`ed): hand-authored consumer clobbered, `[updated]`, doctor masks the loss `[ok]/[ok]`. GREEN: survives byte-identical, `[foreign] — left untouched`, no CLAUDE.md drop, doctor PAIR `[foreign]/[foreign]` — W4B |
| AC-14 PAIR + real doctor exit 0 (2nd bug fix) | `pytest tests/integration/test_public_doctor_parity.py::test_manager_doctor_foreign_pair_for_hand_authored_consumer` | the REAL `manager.doctor()` returns the `[foreign]` pair (no `[drift]`/`[missing]`) — the E2E strict-xfail was LIFTED and now PASSES (real `dadaia public doctor` exit 0) — W4B fix round |
| AC-10 per-pack E2E (in-process, ≤~10s) | `pytest tests/e2e/features/test_plugin_pipeline.py` | **6 passed / 0 xfailed** at ship, module wall-time **~7.7s** (call-time 6.1s); scenarios (a) stubs+golden(b) bytelock, (b/c/d) install-chain+precedence, (e) registered hand-authored survives + doctor exit 0, (f) double-install idempotent, (g) profile×pack coexistence — W5 + W4B fix |
| Frozen v0.1.50 no-steal suite untouched | `git diff` on `test_lock_steal.py` + `test_lease*.py` | **zero-diff** — the release never enters `spec_context`/lease/gate — every wave |
| AC-12 SDD + backlog doctor | `dadaia specs doctor` · `dadaia backlog doctor` | both exit 0 (specs doctor 0 errors) — W6 |
| AC-12 self-hosting reconcile (FR9 live) | `dadaia public stage` → `doctor` → `install --target all` → `doctor` | **0 `[updated]` / 12 `[foreign]` (6 repos × AGENTS.md+CLAUDE.md) / self-repo `[skip]`**, `[ok] public-privacy`, exit 0 — vs the v0.1.58 ship that fanned `[updated]` to 6; consumer trees verified 0 AGENTS/CLAUDE deltas — W6 (Drift 3) |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED**, zero blockers — handoff `2026-07-05T003903Z-qa-engineer-v0160-ship-gate` |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — keyed to the pushed ref sha (`02d00a50`) |
| CI (PR #110) | GitHub Actions | **35 checks pass / 3 condition-skip, 0 failures** — merge gate `4ccc6a21` |

## Drifts

### w1-v0158-goldens-under-enumerated-in-definition-fate-ledger

**Description:** The W1 STOP. The definition fate ledger declared the pre-descriptor v0.1.58
full-inventory goldens would stay "byte-identical". But FR1 legitimately adds new public
source (`public/plugins/**/pack.json` + empty-dir `.gitkeep`s), and `public_assets.stage()`
copies every `_COPY_DIRS` entry (incl. `plugins`) while `doctor()` emits a `stage:<rel>`
parity line per source file — so three v0.1.58 goldens (`install_target_resolution_v0158.json`,
`doctor_all_four_v0158.json`, and transitively `test_public_assets_profile.py`'s reuse)
legitimately grow. The definition under-enumerated this staging-inventory exposure.

**Resolution:** Adjudicated a **deliberate, recorded amendment** (never a silent regen): the
three goldens were re-captured to the descriptors-present truth via each test's own
`UPDATE_INSTALL_GOLDENS` mechanism, with a rigorous multiset (Counter) diff proving the delta
is EXACTLY `+5 [stage] .../plugins` (install) and `+8 [ok] stage:plugins/*` (doctor), ZERO
other delta, ZERO removals. **Plugin-blind filtering was REJECTED** (it would hide future
plugin-staging drift): golden (a) is the deliberately core-scoped refactor-lock, golden (b)
locks the full new baseline — three locks, three distinct roles.

**Memory updates:** none (a test-golden authoring detail; the golden-authoring law already
lives in `quality-assurance.md`).

### w5-fr9-provenance-gate-shipped-as-dead-code (2nd HIGH bug)

**Description:** The W5 E2E surfaced a HIGH bug `public-doctor-flags-hand-authored-consumer-agents-md`
(`specs/bugs/20260704T23Z-00.jsonl`): the FR9 `_doctor_guardrail_pair`/`_check_consumer_agents`
provenance logic was **dead** for the real `dadaia public doctor` — `manager.doctor()`
doctored consumers via the untouched `runtime_expectations` path, emitting
`[drift] repos/<slug>:AGENTS.md` + `[missing] repos/<slug>:CLAUDE.md` → **exit 1** (a Ruling-16
violation). The W4B **unit** test passed by calling the dead helper directly — **false
confidence**. Only the W5 **E2E strict-xfail** (exercising the real `dadaia public doctor`
process boundary) caught it.

**Resolution:** Root-cause wiring — the consumer classification was extracted into a SINGLE
authority `_doctor_consumer_pair_lines`; `manager.doctor()` now calls it after the runtime
loop, `runtime_expectations` no longer yields the `repos/<slug>:` pairs, and
`_doctor_guardrail_pair` delegates to the same authority (one classification path, no parallel
legacy path). A PRIMARY end-to-end test (`test_manager_doctor_foreign_pair_for_hand_authored_consumer`)
now exercises the real `manager.doctor()`; the E2E xfail was **lifted** and PASSES.
**Lesson (memory):** a unit test that calls a wiring-sensitive helper directly proves nothing
about the executed path — pair every wiring-sensitive fix with an executed-path test, and use
`xfail(strict=True)` as a regression lock that turns red the moment the fix lands.

**Memory updates:** `specs/memory/quality-assurance.md` (the false-confidence lesson +
strict-xfail-as-regression-lock pattern); `specs/memory/architecture.md` (the single
consumer-classification authority in `workspace_guardrail`).

### w6-live-instance-damage-found-and-remediated-at-ship

**Description:** The self-hosting reconcile at ship found the bug's clobber **live on all six
consumer repos** — working-tree `AGENTS.md` overwritten with the generic workspace copy +
untracked `@AGENTS.md` `CLAUDE.md` bridge stubs — inflicted by the v0.1.58 reconcile and
**re-inflicted by the W3 propagation running pre-fix code** (the W3 `public install` ran before
the FR9 fix was wired into the real doctor path).

**Resolution:** Remediated at ship — `git checkout -- AGENTS.md` ×6 restored the hand-authored
files + the six untracked bridge stubs were removed (tracked/operator files untouched); the
post-fix `public install --target all` then left ALL hand-authored copies byte-identical
(**0 `[updated]` / 12 `[foreign]` / self-repo `[skip]`**, `[ok] public-privacy`, exit 0),
confirming the FR9 fix on the live instance. This is the acute justification for FR9's HIGH
severity: the fan-out is a data-loss surface on real operator repos.

**Memory updates:** `specs/memory/product/distribution/public-asset-distribution.md` (the FR9
provenance law replaces the v0.1.58 lib-owned-canonical fan-out description).

### w3-stub-body-wording-scope-gap

**Description:** W3 rewrote only the plugin-scope **rule** (`public/rules/plugin-scope.md`) to
install-gated wording, but the three **stub agent bodies**
(`public/agents/{frontend-engineer,design-specialist,devops-engineer}.md`) still claimed
"plugin pack is not yet distributed (no install command exists)" — factually wrong once
v0.1.60 ships. The W5 E2E surfaced the gap.

**Resolution:** A W5 follow-up (`6c5e06d6`) rewrote the three stub `[PLUGIN REQUIRED]` bodies to
the same install-gated wording (`dadaia plugin install <pack>`, ships in v0.1.60), preserving
the E2E scenario-(a) discriminators (`plugin: true` frontmatter + `[PLUGIN REQUIRED]` marker
kept; no pack-body H1 heading added, so `_is_plugin_stub` still discriminates). Grep guard: 0
"not yet distributed" / "no install command exists" hits under `public/` source + projected
`.claude/`. Goldens did not move (line format is content-invariant).

**Memory updates:** none beyond the `plugin-packs.md` install-gated statement.

### full-suite-count-grew-across-waves (not a regression)

**Description:** The full unpiped suite grew wave over wave as each wave added tests: 4624
(after T-60-11) → 4633 (T-60-20) → 4657 (T-60-40) → 4667 (T-60-45 first) → **4674** (T-60-45
fix round / W5 / ship). This is additive coverage growth, **not a regression** — every ship
tree ran with `0 failed`.

**Resolution:** None required — documented so the count delta is not mistaken for churn. The
`quality-assurance.md` live-scale bracket ("grows with every release") already anticipates
this; the honest bracket is now ≈ 4.67k.

**Memory updates:** none (the QA atom's scale note is a bracket, re-validated at closure).

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. Written this CLOSURE (phase = CLOSURE, MEMORY gate open). **Catalog regeneration
IS triggered this closure** — a new product atom is added and two product atoms change their
`summary` (catalog-indexed) — so the orchestrator must run `dadaia memory catalog generate`
to refresh `catalog.json` + `index.md` (both are machine-generated; PE hand-edits neither, no
shell). See "which atoms changed catalog fields" below.

- `specs/memory/product/distribution/plugin-packs.md` — **NEW product atom (area:
  distribution).** Records the plugin-distribution capability as current truth: in-package
  packs, `dadaia plugin install/list/doctor`, the `installed_plugins.json` ledger,
  profile-scoped projection + core-install precedence, `plugin doctor`, and the three agents
  carrying real behavior on the `plugin`/sonnet tier once installed. **Adds a catalog entry →
  catalog regen.** `release_origin` v0.1.60. *(Decision: a NEW atom, not a fold — see below.)*
- `specs/memory/product/distribution/public-asset-distribution.md` — **edit; `summary`
  changed → catalog regen.** Added the plugin projection/ledger/precedence chain and replaced
  the v0.1.58 "consumer-repo ROOT AGENTS.md is lib-owned canonical / divergent restored"
  description with the **FR9 provenance law**: only a consumer `AGENTS.md` carrying the
  canonical `_CANONICAL_AGENTS_BANNER` block is restored (`[updated]`); a no-banner
  hand-authored copy is `[foreign]` and never overwritten, and the paired `CLAUDE.md` doctor
  line follows (so `public doctor` exits 0 for a hand-authored repo). `release_origin` →
  v0.1.60.
- `specs/memory/product/agents/agent-orchestration.md` — **edit; `summary` changed → catalog
  regen.** The three plugin agents now carry real behavior when their pack is installed (on
  the `plugin`/sonnet tier, `tier: 3`); recorded the two independent "tier" axes (Layer-1
  numeric frontmatter dispatch band vs the registry model-cost `Tier`), machine-enforced by
  the mandatory taxonomy contract. `release_origin` → v0.1.60.
- `specs/memory/tech-stack.md` — **edit (core atom; body + `release_origin`; NOT catalog-indexed →
  no catalog regen).** The plugin model-assignment rows now reflect `model: claude-sonnet-4-6`
  (registry `plugin` tier; Codex `gpt-5.3-codex`) once installed; the two "tier" axes and the
  taxonomy contract; the efficiency-audit marker schema + `EFFICIENCY_AUDIT_STALE_DAYS = 30`
  cadence + the `dadaia reports mark-efficiency-audit` writer + the EFF-1 `DoctorIssue`.
  Layer-2 catalog wording unchanged. `release_origin` → v0.1.60.
- `specs/memory/architecture.md` — **edit (core atom; body + `release_origin`; NOT catalog-indexed →
  no catalog regen).** Module map gains `cli/commands/plugin.py`, `core/models/plugin_pack.py`,
  `core/protocols/plugin_store.py`, `infrastructure/json_plugin_store.py`, and `public/plugins/`;
  `public_assets` gains plugin projection + precedence; the **single consumer-classification
  authority** `_doctor_consumer_pair_lines` in `workspace_guardrail`; the workspace-doctor EFF-1
  check. *(The L63 kanban drift-correction was already applied in DEFINITION — not a v0.1.60
  change.)* `release_origin` → v0.1.60.
- `specs/memory/quality-assurance.md` — **edit (core atom; body + `release_origin`; NOT catalog-indexed →
  no catalog regen).** Added the **false-confidence lesson** (a unit test that calls a
  wiring-sensitive helper directly proves nothing about the executed path — pair every
  wiring-sensitive fix with an executed-path test) + the **strict-xfail-as-regression-lock**
  pattern (an `xfail(strict=True)` E2E turns the suite red the moment the fix lands and the
  marker must be removed). `release_origin` → v0.1.60.

**Which atoms changed catalog-indexed fields (`tldr`/`summary`/`area`/`title`/`tags`) →
catalog regen required (orchestrator, `dadaia memory catalog generate`):** NEW
`plugin-packs.md` (new entry), `public-asset-distribution.md` (`summary`),
`agent-orchestration.md` (`summary`). Body-only / core-atom edits with NO catalog impact:
`tech-stack.md`, `architecture.md`, `quality-assurance.md`.

## Dispositions

Disposition-sweep ledger. Both consumed backlog anchors SURVIVE (kept by name / assigned) →
archived **at CLOSURE** by the orchestrator `git mv`. No consumed anchor DIED this release →
no SHIP-time backlog archival. No implementation-wave commit (W1–W6) staged any
`specs/backlog/**` (AC-13 verified). **Bug ledger: 1 open at pick (the reopened HIGH), 1 more
surfaced mid-release (W5) — both resolved this release, 0 open at close.** The two bug terminal
`resolved` events are appended by the orchestrator (`dadaia bugs append`; PE has no shell).

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/plugin-packs-and-install-command.md` → `specs/_archive/v0.1.60/consumed-backlog/` | backlog | `DELIVERED — v0.1.60` | FR1 packs + FR2 `dadaia plugin` CLI + FR3 projection/ledger/precedence/doctor + FR4 content + FR5 rewrite (T-60-10..30) → orchestrator `git mv` + `consumed_backlog.json` |
| `specs/backlog/model-tier-efficiency-and-fast-tier-utilization.md` → `specs/_archive/v0.1.60/consumed-backlog/` | backlog | `DELIVERED — v0.1.60` | FR6 mandatory tier-taxonomy contract + FR7 EFF-1 trigger + writer + FR8 off-opus plugin-tier assignment (T-60-30/40); fast/haiku persona downgrade DEFERRED → backlog return | 
| `specs/bugs/20260704T19Z-00.jsonl` `public-install-clobbers-consumer-repo-agents-md` | bug (HIGH) | `resolved --release v0.1.60` (orchestrator appends) | FR9 banner-provenance fan-out (T-60-45 `f6a28373`) + AC-14 |
| `specs/bugs/20260704T23Z-00.jsonl` `public-doctor-flags-hand-authored-consumer-agents-md` | bug (HIGH) | `resolved --release v0.1.60` (orchestrator appends) | FR9 fix-round: single consumer-classification authority wired into the real `manager.doctor()` (T-60-45 `3f77283a`) + the lifted E2E strict-xfail |

## Backlog returns

Four items discovered/deferred during the release, filed as `specs/backlog/<slug>.md` (status
`candidate`, BL-SCHEMA-valid intents anchored at real Python symbols), routed through PM
curation and indexed in `candidates.md`:

- `backlog/candidates.md` (MEDIUM) ← **`plugin-pack-content-libraries`** — full frontend/design/
  devops skill corpora beyond the two enumerated minimal-viable skills (Ruling ADR-5 / 12
  ceiling). Anchored at `core/models/plugin_pack.py#PluginPack` (the model whose `skills` tuple
  the packs populate).
- `backlog/candidates.md` (MEDIUM) ← **`plugin-uninstall`** — the inverse of install (remove a
  pack, restore the stub); v0.1.60 was additive-only (Ruling ADR-2). Anchored at
  `infrastructure/public_assets.py#install_plugin`.
- `backlog/candidates.md` (MEDIUM) ← **`fast-tier-persona-validation`** — validate a mechanical
  Layer-1 persona on the `fast` (haiku) registry tier with an operator-live equal-quality check
  (Ruling ADR-6 deferral). Anchored at `core/model_registry.py#Tier`.
- `backlog/candidates.md` (LOW) ← **`tier-taxonomy-rename`** — rename the numeric frontmatter
  `tier:` → `dispatch_band:` at source to end the two-"tier" collision that FR6 only documents +
  machine-guards (Ruling 17). Anchored at
  `tests/contract/test_agent_tier_taxonomy.py#test_core_agents_carry_numeric_tier_and_opus_dispatch_model`.

Also indexed: the candidates R12 row is flipped to **SHIPPED — v0.1.60** (`4ccc6a21`, PR #110),
the two consumed MEDIUM entries are removed from the surviving-candidates index (removal-on-release),
and the header records the **R1–R12 plan complete**.

## Archive decision

**MOVE** — `specs/releases/v0.1.60/` will be moved to `specs/_archive/releases/v0.1.60/` via
`git mv` (by the orchestrator / devops-engineer; PE issues no git mutations), together with the
two CLOSURE-archived consumed backlog entries → `specs/_archive/v0.1.60/consumed-backlog/` +
`consumed_backlog.json` (`DELIVERED — v0.1.60`). The orchestrator then: appends the two bug
`resolved` events (`dadaia bugs append`), runs `dadaia memory catalog generate` (catalog regen
trigger — new atom + 2 summary changes), and advances `specs/releases/ACTIVE.md` to
`release: none` (final release of the R1–R12 plan). (PE does not run `git mv`, `dadaia bugs
append`, `dadaia memory catalog generate`, or edit `ACTIVE.md` — no shell.)
