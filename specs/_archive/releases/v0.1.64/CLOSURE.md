# Closure: Release — v0.1.64 — Platform Ergonomics & Tiering

> **Status:** Aprovado
> **Release ID:** v0.1.64
> **Owner:** product-engineer
> **Closed:** 2026-07-07
> **Branch:** `feature/v0.1.64` · **Base:** post-v0.1.63 `main` (`457e4e10` lineage) · **Merged:** `d8bcdff7` (PR #122, squash of `feature/v0.1.64`, 2026-07-07) · **Closure branch:** `chore/v0.1.64-closure`
> **Ship gates:** qa-engineer **APPROVED** (ship-gate handoff, 3 findings: the `golden-platform-normalization-layer` anchor repoint adjudicated legitimate; the CI-scoped hermeticity assert noted as self-proving-only-on-GHA — discharged green on PR #122's first pass; the SPEC/TASKS "8 kept / 0 broken" figure stale vs the actual 9/0 → see Drifts) · security-reviewer **APPROVED** (push-gate keyed to the pushed ref sha `94c24d5a`; credit-spend posture of the entry-harness auto-default + Ring-1 extension minimality — one guarded set-only-when-unset line, no telemetry reads — verified) · CI **ALL 35 checks green on the FIRST pass** at merge — the new CI-scoped hermeticity assert (AC-4, active only under `GITHUB_ACTIONS`) executed and proved itself on GHA.
> **Mandate:** LAST of the fixed four-release queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 (Rulings 61-A/61-B, 64-A/64-B). Pure ergonomics/consolidation — no bug debt, no audit debt in the pick. **With this closure the queue is complete.**

## Summary

v0.1.64 retires four ergonomics debts at source. **One shared platform-invariance module**
(`tests/helpers/golden_platform.py`) is now the single capture-time normalization layer for
byte-goldens — the code home of the v0.1.55/58 golden-authoring laws (host-state, iteration-order,
OS-phrase, path/version, clock, and Rich-width leak classes in one taxonomy docstring) — adopted
**byte-identically** by all 14 former duplicate sites (the 13 enumerated + the rebase-discovered
`test_plugin_uninstall.py`): zero golden bytes changed, and a tests-wide grep contract keeps any
consolidated helper from ever being re-declared locally.

The **ratified entry-harness auto-default convention is now implemented**: every `dadaia lifecycle`
run verb defaults `--harness` to the sentinel `auto`, resolved by `core/session_env.entry_harness()`
(`DADAIA_ENTRY_HARNESS` pin > `CODEX_SESSION_ID` ⇒ codex > fake), with a loud
`[harness] auto-default:` echo on every real-worker default (never silent), a hermetically scrubbed
test envelope AND a CI-env assert, and the dadaia-owned **post-trust PI entry-signal seam** — the
Ring-1 extension exports `DADAIA_ENTRY_HARNESS = "pi"` set-only-when-unset, with the ARCH64-2
security posture (session-wide, credit-affecting, never telemetry-derived) documented in the
extension header and in memory.

The **tier-word collision is resolved at source**: the numeric frontmatter key is `dispatch_band:`
across the 12 agent bodies + reader/DTO/renderer/tests (tolerate-then-strip per the v0.1.53
precedent; the silent legacy `tier:` fallback and the `MissingTierError` alias are a dated strip
window). And the **fast-tier question is closed honestly**: `fast-tier-persona-validation` is
dispositioned REJECTED as premise-dead after the 2026-07-06 retier, PM-ratified per the SPEC §8
operator-checkpoint protocol, with the revival path (DEFERRED + AC-OPCHECK) recorded.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-64-01 | W0 definition — SPEC/PLAN/TASKS from the 2026-07-07 code read + mandatory grill (F-1..F-4, ADR-1..5, two stale dossier premises corrected); dual-review fold QA64-1..3 + ARCH64-2 + ARCHX/QAX; PM Rulings 64-A/64-B; FR6 REJECT surfaced in the definition handoff `decisions_required` | `977593cf` (queue definition) · phase flip `8020d117` |
| T-64-10 | W1 FR1 — NEW `tests/helpers/golden_platform.py` (7-function surface + 6-class leak-taxonomy docstring) + 20 unit fixtures; AC-9(a)(b) sabotages; branch-point collect pin **4795** (QA64-2/QAX-4) | `5797a1de` |
| T-64-11 | W1 FR2 — byte-identical adoption by the 13 enumerated sites **+ the rebase-discovered 14th** (`test_plugin_uninstall.py`, landed v0.1.63); cross-test import killed; AC-1 grep contract `test_no_local_helper_copies.py`; ZERO golden regen; AC-9(f) sabotage | `1ddae485` |
| T-64-20 | W2 FR3 — `core/session_env.entry_harness()` + `auto` default at the 12 `--harness` sites via ONE shim + loud stderr echo + hermeticity (autouse scrub + CI-scoped GHA assert); AC-3 matrix RED-first; AC-9(c)(d) sabotages | `b4d744bd` |
| T-64-21 | W2 FR4 — PI Ring-1 extension guarded pin (set-only-when-unset) + ARCH64-2 posture header; grep-level contract `test_pi_entry_signal.py` | `3ed64aac` |
| T-64-30 | W3 FR5(a) — `tier:` → `dispatch_band:` in the 12 bodies (values unchanged; Ruling 64-A rebase: v61 AC-1 line-diff re-verified + v62 AC-6 12/12 `handoff-v1.2`/`self_pull` greps re-verified post-rename); RED window recorded for T-64-31 | `5c1a7f1b` |
| T-64-31 | W3 FR5(b) — reader (prefer `dispatch_band`, silent legacy fallback, `MissingDispatchBandError` + alias), `AgentDTO.dispatch_band`, `api_agents` field, contract/reader/panel tests; 2 deliberate golden regens with multiset diffs = EXACTLY the token rename; AC-9(e) sabotage | `521deb01` |
| — | recorded backlog-anchor repoint — `golden-platform-normalization-layer` intents ref repointed to `tests/helpers/golden_platform.py#norm_path_line` after T-64-11 deleted the recorded helper (backlog doctor red → clean; QA-adjudicated legitimate) | `dc3a5c8b` |
| T-64-40 | W4 — AC-10 full gates + frozen-suite zero-diff + instance re-projection (`stage → install --target all → doctor`, `[ok] public-privacy`); reviews + push + PR #122 + merge `d8bcdff7` | `94c24d5a` |
| T-64-50 | W5 — this CLOSURE.md + memory rebase (7 atoms + heading-allowlist) + disposition sweep (3 delivered + 1 rejected) + backlog return + archive handoff to PM | (this closure) |

## Validations

Each row is a triple: description, command, evidence (SHA / stdout snippet / handoff path).
Gate evidence captured at the ship tree (`94c24d5a`) and merged as PR #122 (`d8bcdff7`).

| Description | Command | Evidence |
|-------------|---------|----------|
| AC-10 full suite green | unpiped `pytest` (real exit) | `4837 passed, 18 skipped, exit 0` — `94c24d5a` (branch-point pin 4795 collected at `8020d117`, T-64-10; growth = this release's new tests) |
| AC-10 format + lint clean | `ruff format --check` · `ruff check --no-cache` | both exit 0 — `94c24d5a` |
| AC-10 types clean | `mypy --strict dadaia_workspace` | exit 0 — `94c24d5a` |
| AC-10 import contracts | `lint-imports --no-cache` | **9 kept / 0 broken**, ignore-cap **36** == base pins (`tests/helpers/` is outside `root_package`; no layer edge added) — the SPEC's "8/0" predates v0.1.61's 9th contract, see Drifts — `94c24d5a` |
| AC-10 SDD + backlog doctors | `dadaia specs doctor` · `dadaia backlog doctor` | both clean/exit 0 — backlog doctor after the recorded anchor repoint `dc3a5c8b` (see Drifts) — T-64-40 |
| AC-1 byte-identical adoption (golden-first) | `git diff --stat -- 'tests/**/_golden'` in the adoption commit + full suite with `UPDATE_INSTALL_GOLDENS` unset | diff EMPTY (zero golden regen); suite exit 0 `4800 passed / 17 skipped`; cross-test import grep = none — `1ddae485` |
| AC-2 module contract | `pytest tests/unit/helpers/test_golden_platform.py` | 20/20 green over the known leak fixtures (denylist marker; D-CX-9 `exited 127` + `[WinError 193]` → one canonical line; sorted multiset count-preserving; Rich box-wrap; `<WS>`/`<TS>`); lint-imports 9/0 cap 36 unchanged — `5797a1de` |
| AC-3 auto-default matrix (RED-first) | resolver unit matrix + `implement` + `pipeline` verb-level CLI tests | RED pre-change (literal `"fake"` at all 12 sites); post-change: pin > `CODEX_SESSION_ID` > fake precedence, echo present on real-worker default / absent on fake+explicit, echo on stderr (`--json` stdout pure); 12 sites grep `"auto",` = 12, `"fake", "--harness"` = 0 — `b4d744bd` |
| AC-4 hermeticity, both halves (QA64-1) | autouse scrub test + CI-scoped env assert | simulated developer `CODEX_SESSION_ID` still resolves `fake` in the lifecycle envelope; the `GITHUB_ACTIONS`-gated assert (skipped locally) ran on PR #122 and passed — the GHA quality-job env carries none of the three entry-signal vars, proven on the first CI pass — `b4d744bd` + PR #122 |
| AC-5 PI seam | `pytest tests/contract/test_pi_entry_signal.py` + `dadaia public doctor` | guarded pin + exactly-one-assignment + ARCH64-2 posture needles green on the canonical source; `[ok] public-privacy` at W4 — `3ed64aac` / `94c24d5a` |
| AC-6 rename completeness (RED-first) | `grep -rn "^tier:"` over both agent dirs + contract/fallback tests | grep = ZERO, `^dispatch_band:` = exactly 12; contract asserts `dispatch_band` with `_CORE_MODEL_EFFORT` + roster counts BYTE-UNCHANGED; `test_legacy_tier_only_body_resolves_band_silently` green (stderr EMPTY); RED-first shown (2 contract failures pre-T-64-31) — `5c1a7f1b` + `521deb01` |
| AC-7 deliberate regen enumeration | multiset diffs on the 2 regenerated goldens | `api_golden_v0155.json` removed {tier: 1} added {dispatch_band: 1}; `panel_runtime_validation_v0158.json` removed {tier: 4} added {dispatch_band: 4}; zero other delta; `install_target_resolution_v0158.json` + `doctor_all_four_v0158.json` VERIFIED byte-unchanged under the regen env — `521deb01` |
| Ruling 64-A cross-release re-verification | v61 AC-1 line-diff + v62 AC-6 greps post-rename | `git diff -U0` = only the tier→dispatch_band line per body (model/effort untouched: opus×4, fable-5×5 w/ effort, sonnet×3); `handoff-v1.2` 12/12 AND `self_pull` 12/12 — `5c1a7f1b` |
| AC-9 mutation-sanity (a–f) | one-line sabotages per task line | (a) sort dropped ⇒ 4F; (b) `canon_env_line` identity ⇒ 7F; (c) pin ignored ⇒ 6F; (d) echo dropped ⇒ 4F; (e) legacy `tier` rejected ⇒ fallback test F; (f) stale local copy re-added ⇒ grep contract F — each captured then reverted; T-64-10/11/20/31 evidence blocks |
| Frozen v0.1.50 no-steal suite | `git diff` vs main on the lease/gate test files | **zero-diff** — `94c24d5a` |
| Self-hosting reconcile | `dadaia public stage` → `install --target all` → `public doctor` | all exit 0 incl. `[ok] public-privacy`; renamed frontmatter + the `.pi/` guarded pin projected via the pipeline only — T-64-40 |
| QA ship gate | `dadaia reports validate <handoff>` | **APPROVED** — 3 findings (anchor repoint legitimate; CI assert self-proof — now discharged; "8/0" stale → Drifts) |
| Security push gate (per push-cycle) | pre-push security-verdict chokepoint | **APPROVED** — keyed to pushed ref sha `94c24d5a`; credit-spend posture + Ring-1 extension minimality verified |
| CI (PR #122) | GitHub Actions | **ALL 35 checks green on the FIRST pass** at merge `d8bcdff7` — incl. the AC-4 CI-scoped hermeticity assert executing (not skipping) on GHA |
| FR6 operator checkpoint (SPEC §8) | definition handoff `decisions_required` + in-session report | evidence type **operator-present**: the operator did not exercise the override when the queue definition and this implementation were reported — REJECT stands PM-ratified (see Dispositions) |

## Drifts

### spec-8-0-lint-imports-predates-v0161-ninth-contract (QA finding)

**Description:** SPEC AC-2/AC-10 and the pre-evidence TASKS text pinned `lint-imports` at
"8 kept / 0 broken" — authored at the parallel queue definition, before v0.1.61 merged the 9th
contract (`cli-no-infrastructure`). The actual gate result throughout this release is
**9 kept / 0 broken**, ignore-cap 36 unchanged. Same drift class as v0.1.62's (adjudicated
there as a Ruling 62-A rebase note).

**Resolution:** Rebase note, not a regression — recorded on the T-64-10/11/40 evidence blocks
("rebase-true base, supersedes the stale 8/0 text") and flagged by the QA ship gate. No spec
re-edit post-approval.

**Memory updates:** none — `architecture.md` has documented the 9 contracts since v0.1.61's
closure (rebased, never reverted).

### rebase-discovered-14th-duplicate-site

**Description:** The SPEC enumerated 13 adoption sites from the 2026-07-07 definition-time
read. `tests/integration/test_plugin_uninstall.py` landed with v0.1.63 (after the enumeration)
carrying verbatim copies of `_norm_path_line`/`_is_env_doctor_line`/`_canon_env_line`/`_DCX9`
— a 14th duplicate site.

**Resolution:** Adopted alongside the 13 in T-64-11 (its bespoke `_norm_doctor` composition
stays local, consistent with FR2's bespoke-exemption rule); the AC-1 grep contract now guards
tests-wide, so a future 15th copy fails CI instead of waiting for a human read.

**Memory updates:** `specs/memory/quality-assurance.md` (the shared-module paragraph counts
all 14 sites).

### golden-platform-backlog-anchor-repoint (QA-adjudicated)

**Description:** The `golden-platform-normalization-layer` backlog entry's typed intent was
anchored at `test_install_target_goldens.py#_norm_path_line` — a helper T-64-11 deliberately
**deleted** (the consolidation IS the deletion). `dadaia backlog doctor` correctly went red on
the dead anchor mid-release.

**Resolution:** Recorded repoint commit `dc3a5c8b`: the anchor moved to the consolidated home
`tests/helpers/golden_platform.py#norm_path_line` — the same subject at its new address, not a
scope change. QA adjudicated the repoint legitimate (the alternative — keeping a stale copy
alive to satisfy an anchor — would sabotage the item's own goal). Note the TASKS "NO
`specs/backlog/**` paths staged in implementation waves" rule bent for exactly this one
mechanical repoint, forced by the doctor gate, and is recorded here rather than silently.

**Memory updates:** none (backlog metadata, not product truth).

### tech-stack-truth-edits-at-rebase (beyond SPEC §10's expectation)

**Description:** SPEC §10 scoped `tech-stack.md` to the `dispatch_band` wording + the
auto-default chain. At the CLOSURE rebase read, two rows were false memory outside that scope:
the "Schema handoff-v1.1" section still declared "current version **v1.1**" (stale since
v0.1.62 shipped v1.2 — that closure recorded tech-stack "no change" and missed the row), and
the canonical-commands block still showed `--model <id>` on `backlog define` (hard-removed in
v0.1.57).

**Resolution:** Minimal truth edits (v0.1.63 precedent — memory truth outranks the
prediction): the section renamed to "Schema handoff-v1 family" with current token v1.2
(heading change allowlisted in `specs/memory/.heading-allowlist`, the sanctioned workspace
union mechanism — the lint script's Group-C list is a lib source outside the PE write set),
and the stale command line corrected to the `--step-model` + `auto`-default truth.

**Memory updates:** `specs/memory/tech-stack.md` + `specs/memory/.heading-allowlist`.

## Memory updates

Memory describes the product **as it is now**; the change history lives here and in
`_archive/`. All edits landed in this CLOSURE phase (MEMORY gate open), **rebased on the
v0.1.61 + v0.1.62 + v0.1.63 closed states per Ruling 64-B** (this release closes LAST — each
atom's current text was read before editing; no sibling correction reverted: v0.1.61's
9-contract/warning-clean truths, v0.1.62's v1.2 contract + required-presence e2e law, and
v0.1.63's uninstall/corpora rows all preserved). `release_origin: v0.1.64` +
`last_updated: 2026-07-07` set on every edited atom. **Catalog regen required** (PM follow-up:
`dadaia memory catalog generate`) — tldr changed on `dadaia-workflows` and `harness-pi`; regen
accumulates the v0.1.61/62/63 prior deltas per Ruling 64-B.

- `specs/memory/quality-assurance.md` — **primary (golden law → code truth).** NEW
  "Shared platform-invariance module (v0.1.64)" paragraph: `tests/helpers/golden_platform.py`
  as the ONE capture-time layer (7-function surface, 6-class leak taxonomy, `assert_golden`
  mechanism, 14-site adoption, the no-local-copies grep contract + bespoke exemptions); the
  v0.1.58 meta-lesson's "tracked by the backlog return" pointer retired (delivered); the CLI
  stderr law now names `golden_platform.norm_stderr` as the one home; live-scale bracket
  re-validated (4,755/v0.1.62 → **4,837 passed + 18 skipped at v0.1.64 ship**).
- `specs/memory/tech-stack.md` — two-axis disambiguation at source (`dispatch_band:` renamed,
  legacy `tier:` silently tolerated during the tracked strip window; registry `Tier` keeps its
  name); NEW workflow `--harness auto` bullet (full resolution chain + loud echo + hermeticity);
  fast-tier row → registry-defined-but-unassigned by design with the REJECTED disposition +
  §8 revival pointer; PLUS the two drift-recorded truth edits (handoff family token v1.2;
  canonical-commands line).
- `specs/memory/product/agents/agent-orchestration.md` — the two-axes section renamed key
  (`dispatch_band: 1/2/3`, silent legacy fallback + strip pointer), taxonomy-test pointer now
  asserts `dispatch_band` with the pinned map unchanged; plugin-stub line `dispatch_band: 3`;
  the retired `tier-taxonomy-rename` tracked-return sentence removed.
- `specs/memory/product/sdd/dadaia-workflows.md` — usage-flow step 1 carries the `auto`
  default (resolution chain, explicit-flag wins, loud echo, hermetic envelope); tldr updated.
- `specs/memory/product/sdd/lifecycle-foundation.md` — CLI-surface paragraph gains the
  12-site `auto` sentinel + ONE shared resolver shim + stderr echo + both hermeticity halves +
  the harness-pi pin cross-reference.
- `specs/memory/product/harness/harness-pi.md` — NEW usage-flow step: the post-trust
  entry-signal seam **including the ARCH64-2 security-posture note verbatim in spirit
  (session-wide credit-affecting pin; set-only-when-unset; loud echo guards every
  auto-default; never derived from telemetry; pre-trust honestly stays `fake`)**; tldr updated.
- `specs/memory/product/harness/harness-codex.md` — entry-signal note (`CODEX_SESSION_ID` ⇒
  auto-default `codex`; pin beats it; stale-id credit risk + mitigations).
- `specs/memory/.heading-allowlist` — `Schema handoff-v1 family` allowlisted (see Drifts).
- `specs/memory/architecture.md` — **no change: assessed.** `tests/helpers/` is outside
  `root_package`; no layer, contract, port, or module-roster change (lint-imports pins
  unchanged); `core/session_env.py` was already an enumerated core leaf.
- `specs/memory/product/catalog.json` — PM regen (`dadaia memory catalog generate`) picks up
  the two tldr deltas + all prior sibling deltas.

## Dispositions

Disposition sweep per the ADR-11 vocabulary — the four consumed backlog items (SPEC §6).
**Bug debt: none picked** (pure-backlog set per the queue definition), **none filed
mid-release** → no bug terminal events. The two open LOW bugs
(`backlog-doctor-yaml-parse-misdiagnosis`, `e2e-panel-harness-toggle-ci-flake`) were filed
outside this queue's pick and stay **open** — they outrank plain backlog at the next
release-definition pick (recorded in `candidates.md` and the PM ACTIVE.md handoff).

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/backlog/golden-platform-normalization-layer.md` | backlog | `delivered` (`delivered_in: v0.1.64`) | FR1/FR2, `5797a1de` + `1ddae485`; anchor deliberately REPOINTED to the consolidated home `tests/helpers/golden_platform.py#norm_path_line` (`dc3a5c8b`, QA-adjudicated — see Drifts); flipped this closure; PM `git mv` → `specs/_archive/v0.1.64/consumed-backlog/` |
| `specs/backlog/workflow-spawn-entry-harness-autodefault.md` | backlog | `delivered` (`delivered_in: v0.1.64`) | FR3/FR4, `b4d744bd` + `3ed64aac`; anchor `core/session_env.py#harness_session_id` SURVIVES (the module gained `entry_harness()` beside it); the item's sanctioned codex-only fallback was exceeded — the PI seam shipped too (ADR-3); flipped this closure; PM `git mv` → archive |
| `specs/backlog/tier-taxonomy-rename.md` | backlog | `delivered` (`delivered_in: v0.1.64`) | FR5, `5c1a7f1b` + `521deb01`; anchor `test_agent_tier_taxonomy.py#test_core_agents_carry_numeric_tier_and_pinned_model_effort` SURVIVES (function names deliberately kept — BL-SCHEMA anchors pin them; assertions now read `dispatch_band`); the dossier's stale "Codex frontmatter parser" claim corrected at definition (§9 F-3); flipped this closure; PM `git mv` → archive |
| `specs/backlog/fast-tier-persona-validation.md` | backlog | `rejected` (`rejected_in: v0.1.64` — premise-dead post-2026-07-06 retier) | FR6 (no code), SPEC §9 ADR-5; disposition + override path recorded in the entry body; **stays in `specs/backlog/`** with its terminal status (see Archive decision) |

### FR6 operator checkpoint record (SPEC §8 protocol)

The REJECT recommendation was surfaced as a `decisions_required` item in the definition
handoff (the operator was not live at definition). The operator **was present in-session**
when the queue definition and this release's implementation were reported, and **did not
exercise the override** — the disposition therefore stands as **PM-ratified** per the SPEC §8
protocol. **Override path, documented and permanently open:** an operator revival
re-dispositions the item `DEFERRED`, and the reviving release MUST carry the SPEC §8
**AC-OPCHECK** verbatim-in-spirit — the operator-live, non-self-approvable equal-quality
side-by-side checkpoint (`equal-quality: yes|no + rationale` pasted into that release's
CLOSURE §Validations with evidence type `operator-live`); the assignment ships only behind
`equal-quality: yes`.

**Consumed-backlog archive payload** (PM writes this as
`specs/_archive/v0.1.64/consumed-backlog/consumed_backlog.json` — PE does not write
`_archive`. Per the v0.1.60 precedent the ledger carries **delivered items only**; the
REJECTED disposition lives in this CLOSURE + the entry's frontmatter, never in the ledger):

```json
{
  "release": "v0.1.64",
  "consumed": [
    {
      "slug": "golden-platform-normalization-layer",
      "shipped_anchors": [
        "tests/helpers/golden_platform.py#norm_path_line"
      ],
      "note": "DELIVERED — v0.1.64 (archived at CLOSURE; anchor deliberately repointed dc3a5c8b to the consolidated home — the consolidation IS the deletion of the old per-test helpers, QA-adjudicated). NEW tests/helpers/golden_platform.py: norm_path_line / norm_panel_body / canon_env_line / sort_line_lists / is_env_doctor_line / norm_stderr(wide_glyphs) / assert_golden(update_env='UPDATE_INSTALL_GOLDENS', update_env=None for never-regen sites) with the six-class leak-taxonomy docstring (host-state, iteration-order, OS-phrase, path/version, clock, Rich-width) citing the v0.1.58 three-round commits. Byte-identical adoption by all 14 duplicate sites (13 enumerated + rebase-discovered test_plugin_uninstall.py): zero bytes changed under tests/**/_golden, suite green with the regen flag unset, cross-test import killed; tests-wide grep contract test_no_local_helper_copies.py pins that no consolidated helper is re-declared (bespoke exemptions cited: test_fragment_gate_goldens.py, test_api_golden.py, specs/test_doctor_golden.py). AC-9 sabotages a/b/f captured then reverted. Ship PR #122, squash d8bcdff7.",
      "commits": ["5797a1de", "1ddae485"]
    },
    {
      "slug": "workflow-spawn-entry-harness-autodefault",
      "shipped_anchors": [
        "dadaia_workspace/core/session_env.py#harness_session_id"
      ],
      "note": "DELIVERED — v0.1.64 (archived at CLOSURE, anchor survives — session_env gained entry_harness() beside it). Implements the ratified AGENTS.md convention: --harness defaults to the sentinel 'auto' at all 12 lifecycle run-verb option sites, resolved by ONE shared shim via core/session_env.entry_harness() — DADAIA_ENTRY_HARNESS in {codex, pi} (operator/PI-seam pin) > CODEX_SESSION_ID => codex > None => fake (Claude entry is Layer-1-only). Explicit --harness unchanged; loud '[harness] auto-default: <name> (from entry session; pass --harness to override)' stderr line on every real-worker auto-default (fake prints nothing; --json stdout pure). Hermetic both halves (QA64-1): autouse scrub of the three entry-signal vars over the lifecycle CLI test envelope + a CI-scoped assert (GITHUB_ACTIONS-gated, skipped locally) that proved itself green on PR #122's first pass. PI seam (FR4/ADR-3, exceeding the item's sanctioned codex-only fallback): the Ring-1 extension dadaia-sdd-gate.ts exports the pin set-only-when-unset at factory load, with the ARCH64-2 posture (session-wide credit-affecting; loud echo; never telemetry-derived; pre-trust honestly fake) in the header + memory; grep-level contract test_pi_entry_signal.py. AC-3 matrix RED-first vs the literal 'fake'; AC-9 sabotages c/d captured then reverted. Ship PR #122, squash d8bcdff7.",
      "commits": ["b4d744bd", "3ed64aac"]
    },
    {
      "slug": "tier-taxonomy-rename",
      "shipped_anchors": [
        "tests/contract/test_agent_tier_taxonomy.py#test_core_agents_carry_numeric_tier_and_pinned_model_effort"
      ],
      "note": "DELIVERED — v0.1.64 (archived at CLOSURE, anchor survives — test function names deliberately kept for BL-SCHEMA anchoring; assertions now read dispatch_band). Source rename tier: -> dispatch_band: across the 12 agent bodies (values unchanged; 3 stubs tier-less, untouched; Ruling 64-A: LAST writer of the bodies — v61 AC-1 line-diff + v62 AC-6 12/12 handoff-v1.2/self_pull greps re-verified post-rename) + reader (prefer dispatch_band, SILENT legacy tier fallback for stale consumer projections, missing-both default-3 warning renamed, MissingDispatchBandError + MissingTierError alias, allowlist carries both keys for the window) + AgentDTO.dispatch_band + api_agents renders 'dispatch_band' (no JS consumer — read fact) + contract/reader/panel tests. Tolerate-then-strip per the v0.1.53 agent_tier precedent; strip filed as dispatch-band-legacy-fallback-removal (eligible 2026-08-01). Two deliberate golden regens via the W1 assert_golden mechanism, each multiset-diff-proven EXACTLY the token rename (api_golden_v0155: tier x1; panel_runtime_validation_v0158: tier x4; install/doctor goldens VERIFIED regen-free). Definition corrected the dossier's stale claim that the Codex projection reads numeric tier (it derives effort from the registry Tier via model: only). AC-6 RED-first; AC-9 sabotage e captured then reverted. Ship PR #122, squash d8bcdff7.",
      "commits": ["5c1a7f1b", "521deb01"]
    }
  ]
}
```

## Backlog returns

One tracked return filed this closure (`status: candidate`, BL-SCHEMA intent anchored at a
top-level Python symbol), routed through PM curation and indexed in `candidates.md`:

- `backlog/candidates.md` (LOW) ← **`dispatch-band-legacy-fallback-removal`** — strip the
  v0.1.64 tolerate window: the silent legacy `tier:` fallback in
  `features/agents/reader.py#_raw_to_dto` (the second read `band_raw = raw.get('tier')`),
  the `tier` entry in `_ALLOWED_FIELDS`, and the `MissingTierError = MissingDispatchBandError`
  alias + `__init__.py` re-export; invert the AC-6 fallback test. **Dated expiry: eligible
  from 2026-08-01** (one consumer re-projection window, deprecation-expiry law). Anchored at
  `dadaia_workspace/features/agents/reader.py#_raw_to_dto`.

**`golden-normalizer-residual-consolidation` — assessed, NOT filed.** The SPEC's conditional
return applies only if it is genuinely valuable. Verdict: the three bespoke normalizers
(`test_fragment_gate_goldens.py`, `test_api_golden.py`, `specs/test_doctor_golden.py`) each
carry test-specific scrubs the shared module deliberately does not absorb (FR2/ADR-2:
"churn without payoff"), and the exemption list is now **explicitly cited and contract-pinned**
in `test_no_local_helper_copies.py` — drift toward new duplication fails CI. A consolidation
item would re-open a decision this release already made with a guard in place; not filed.

## Cross-release closure order (Ruling 64-B) — queue complete

This release closes **LAST** in the fixed queue v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64. Every
shared memory atom edited here (`quality-assurance.md`, `tech-stack.md`,
`agent-orchestration.md`, `dadaia-workflows.md`, `lifecycle-foundation.md`, the harness atoms)
was **rebased on all three siblings' closed states** — read before editing, no correction
reverted — and the closure `catalog.json` regen accumulates every prior tldr/summary delta.
**With this closure the four-release queue is complete**: 41 audit dispositions (v61), the
v1.2 injection contract + containment (v62), the complete plugin platform (v63), and the
ergonomics/tiering tail (v64) are all shipped, closed, and archived. `ACTIVE.md` advances to
`release: none`; the next pick starts from the two open LOW bugs (which outrank plain
backlog) + the three surviving LOW candidates.

## Archive decision

**MOVE** — `specs/releases/v0.1.64/` moves to `specs/_archive/releases/v0.1.64/` via `git mv`
(PM/operator; PE issues no git mutations and runs no shell). PM then executes, in order:

1. `git mv` the 3 delivered backlog files (`golden-platform-normalization-layer.md`,
   `workflow-spawn-entry-harness-autodefault.md`, `tier-taxonomy-rename.md`) →
   `specs/_archive/v0.1.64/consumed-backlog/` and write `consumed_backlog.json` there
   (payload above, verbatim). **The rejected `fast-tier-persona-validation.md` stays in
   `specs/backlog/`** with its terminal `status: rejected` — my precedent read: no sibling
   release archives rejected entries (v0.1.60's non-delivered dispositions never entered an
   archive), terminal statuses are exempt from the backlog stale check, and the entry body
   carries the live override path a future operator pick must find. PM MAY relocate it to
   `specs/backlog/_archive/` later under the terminal-entry precedent
   (`selfrepo-agents-md-doubled-header`) if curation prefers a leaner live dir.
2. `dadaia memory catalog generate` (**required** — tldr changed on `dadaia-workflows` +
   `harness-pi`; regen accumulates the v0.1.61/62/63 prior deltas per Ruling 64-B).
3. `dadaia specs doctor` + `dadaia backlog doctor` (both must exit 0).
4. the release-dir `git mv specs/releases/v0.1.64 specs/_archive/releases/v0.1.64`.
5. advance `ACTIVE.md` → `release: none`, `phase: none` (**queue complete**), noting the two
   open LOW bugs (`backlog-doctor-yaml-parse-misdiagnosis`,
   `e2e-panel-harness-toggle-ci-flake`) as the next pick's outranking debt.

**Order law honored: the memory rebase + this disposition sweep land BEFORE `ACTIVE.md`
leaves CLOSURE; the catalog regen (step 2) runs BEFORE the ACTIVE advance (step 5).**
