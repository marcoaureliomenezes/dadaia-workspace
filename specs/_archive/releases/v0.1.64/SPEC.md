# SPEC — v0.1.64 — Platform Ergonomics & Tiering

**Status:** Aprovado
**Branch:** `feature/v0.1.64` (base: current main; parallel-defined with v0.1.61/62/63 — PM sequences implementation)
**Origin:** PM dispatch 2026-07-07, theme "platform ergonomics + the tiering tail". Pure ergonomics/consolidation:
no new product capability, no bug debt, no audit debt in the pick.
**Definition-time inspection** (product-engineer code read, 2026-07-07) — every claim below is a read fact from the
current post-v0.1.60/retier source, not a restatement of the backlog dossiers (two dossier premises are stale and
corrected in §1 + §9).
**Release-definition grill** (mandatory, from-backlog) run inspection-first on the picked set before this SPEC;
findings and ADRs recorded in §9 (operator not live at definition — every ADR is operator-overridable; the FR6
REJECT recommendation is explicitly surfaced as a `decisions_required` item in the definition handoff).
**Consumes:** backlog `golden-platform-normalization-layer` (MEDIUM) + `workflow-spawn-entry-harness-autodefault`
(MEDIUM) + `tier-taxonomy-rename` (LOW) + `fast-tier-persona-validation` (MEDIUM — **re-baselined; recommended
REJECTED as premise-dead**, §9 ADR-5 / FR6).
**Bug debt at pick:** none. **Audit debt at pick:** none.

## 0. PM binding rulings — review fold (2026-07-07)

Dual DEFINITION review: qa-engineer **APPROVE-with-amendments** (QA64-1..3; report
`.dadaia/reports/dadaia-workspace/qa-engineer/2026-07-07T020000Z-v0161-64-definition-review.md`);
software-architect returned ARCH64-2 (LOW) + cross-release ARCHX-1..3 inline to PM. Folds carry
`<!-- AMEND:… -->` markers. PM binding rulings, numbered per release:

- **Ruling 64-A (RULING A — ARCHX-1 + QAX-1).** <!-- AMEND:ARCHX-1 --> Implementation order is **FIXED:
  v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64** (this release lands LAST). **Symmetric cross-reference for the 12
  agent bodies:** v0.1.62 W3 writes their body prose (handoff-v1.2 instructions) and v0.1.63 W2/W3 the plugin
  agents' `skills:` frontmatter — BEFORE this release's W3 renames `tier:` → `dispatch_band:` in the SAME 12
  files. W3 (T-64-30/31) therefore **REBASES onto the siblings' landed state, re-runs its `^tier:` grep, AND
  verifies v0.1.62's AC-6 adoption grep stays satisfied post-rename** (the frontmatter rename must not disturb
  the handoff-instruction prose). Any undeclared collision is a STOP-and-rescope to PM.
- **Ruling 64-B (RULING B — ARCHX-2 + QAX-2).** <!-- AMEND:ARCHX-2 --> CLOSURE sequencing follows the same
  order (this release closes LAST); §10 carries the shared-atom merge-order clause (`quality-assurance.md` +
  `tech-stack.md` + `agent-orchestration.md` shared with siblings). `ACTIVE.md` is a single pointer — the four
  releases never hold DEFINITION/CLOSURE phases concurrently; PM owns the phase schedule.
- **Sibling note (ARCHX-3):** <!-- AMEND:ARCHX-3 --> v0.1.62 ships before this release — agent handoffs emitted
  during this release's implementation/closure phases carry `handoff-v1.2` + `self_pull.refs`.
- **Mechanical folds:** ARCH64-2 security-posture note at FR4 + the `harness-pi` §10 memory item; QA64-1 CI
  hermeticity assert in FR3/AC-4; QA64-2/QAX-4 branch-point `pytest --collect-only -q` count pinned in the W1
  fate ledger; QA64-3 W0 marker normalized to `[x]`.

## 1. Problem

Four ergonomics debts, each already ratified in principle but unconsolidated at source:

**Read facts (source, 2026-07-07):**

1. **The golden platform-invariance helpers exist five times.** The canonical trio
   (`_norm_path_line` L78, `_canon_env_line` L251, `_sort_line_lists` L263, plus `_norm_panel_body` L96,
   `_is_env_doctor_line` L104, `_assert_golden` L280 with the `UPDATE_INSTALL_GOLDENS` regen mechanism) lives in
   `tests/unit/infrastructure/test_install_target_goldens.py`; byte-similar copies live in
   `tests/integration/test_plugin_install_goldens.py` (L81/118/129), `tests/integration/test_plugin_projection.py`
   (L60/78/82), and `tests/e2e/features/test_plugin_pipeline.py` (L83/96/100);
   `tests/unit/infrastructure/test_public_assets_profile.py` (L40-45) **imports the helpers from the golden test
   module** — a fragile cross-test-module import. Adjacent same-family duplication: `_norm_stderr` (ANSI-strip +
   Rich box-drawing collapse, the v0.1.57 QA-atom law) is copied in **8** CLI test files
   (`test_plugin_cli.py`, `test_init_harness.py`, `test_lifecycle_cli.py`, `test_model_flag_removed_ac9.py`,
   `test_implement_review_cli.py`, `test_lifecycle_fr2_wire_verbs.py`, `test_lifecycle_verb_governance.py`,
   + `test_lifecycle_policy_cli.py`'s `_norm`). A new byte-golden must re-discover the three v0.1.58 leak classes
   (host-state cwd-walk, directory-iteration order, OS-phrased exec text) unless it happens to copy the right file.
2. **The entry-harness auto-default is a ratified convention with no implementation.** Root `AGENTS.md` ("Harness
   preference (convention)") already states: enter codex ⇒ prefer `--harness codex`, enter pi ⇒ prefer
   `--harness pi`, explicit flag wins. But all **12** `--harness` option sites in `cli/commands/lifecycle.py`
   (L346, 475, 645, 950, 983, 1016, 1049, 1178, 1235, 1289, 1447, 1528) hard-default to `"fake"`, and
   `core/session_env.py` resolves only `CLAUDE_CODE_SESSION_ID` + `CODEX_SESSION_ID` — **PI exports no session env
   var** (confirmed: `infrastructure/pi_runtime.py` reads none; PI telemetry is file-based via
   `~/.pi/agent/sessions/`). The PI entry-signal seam is the open design (§9 ADR-3).
3. **Two "tier" axes still collide on the word at source.** v0.1.60 FR6 (Ruling 17) documented the split and added
   the mandatory `tests/contract/test_agent_tier_taxonomy.py`, deferring the rename. Blast radius (read):
   frontmatter `tier:` lines in **12 agent bodies** (9 `public/agents/*.md` cores + 3
   `public/plugins/*/agents/*.md` pack bodies; the 3 stubs carry `plugin: true`, no tier); parser
   `features/agents/reader.py` (allowlist L76, parse L157-176, `MissingTierError` L93 + L368 catch, re-export in
   `features/agents/__init__.py`); model `core/models/agent.py` (`AgentDTO.tier`); renderer
   `features/panel/views/api_agents.py:301` (`"tier": dto.tier` — **no panel JS consumer reads it**; the Agentic
   tab is deleted, only dead-ish CSS accent tokens remain); tests `test_agent_tier_taxonomy.py`, `test_reader.py`,
   `test_api_agents.py`, `test_api_golden.py`, `test_plugin_content.py`, plus the v0.1.58 install/panel byte-goldens
   whose captured JSON bodies embed `"tier": 3`. **Correction:** the Codex projection does NOT read the numeric
   `tier:` — `runtime_transforms/codex_assets.py` L118 derives effort from the registry `Tier` via `model:` only;
   the dossier's "e.g. the Codex frontmatter parser" is stale.
4. **The `fast` (haiku) registry tier is defined-but-unassigned — and the item's premise is dead.** The dossier
   premise ("all 9 core forced to opus") is stale since the **2026-07-06 operator retier**: 5 core agents now run
   `claude-fable-5` (registry `deep`) with pinned per-agent `effort` (PE/auditor high, ai-eng medium, SE/QA low)
   and 4 keep `claude-opus-4-8` — machine-pinned in `test_agent_tier_taxonomy.py`'s `_CORE_MODEL_EFFORT` map. The
   v0.1.60 read-fact stands: the "mechanical sub-task classes" are deterministic CLI calls carrying no model;
   Layer-1 has only whole-persona `model:` assignment. §9 ADR-5 / FR6.

## 2. Goals

1. **One shared platform-invariance module** for golden capture (`tests/helpers/golden_platform.py`) so a new
   byte-golden is cross-platform-stable **by construction**; the 5 trio-carrying files + the 8 `_norm_stderr`
   copies adopt it **byte-identically** (zero golden regen — the proof of behavior preservation).
2. **Implement the ratified entry-harness auto-default**: enter codex ⇒ `--harness codex`, enter pi ⇒
   `--harness pi` (via a new dadaia-owned PI entry signal), explicit flag always wins, everything else keeps
   `fake` — loudly echoed, never silent, hermetic under test.
3. **Resolve the tier-word collision at source**: `tier:` → `dispatch_band:` across the 12 bodies + parser/model/
   renderer/tests, tolerate-then-strip per the v0.1.53 `agent_tier` precedent.
4. **Close the fast-tier question honestly**: disposition `fast-tier-persona-validation` **REJECTED** as
   premise-dead post-retier (operator-overridable), while recording the operator-checkpoint validation protocol so
   any future fast-tier assignment has its non-self-approvable AC design ready (§8).

## 3. Functional requirements

### FR1 — Shared golden platform-invariance module (`tests/helpers/golden_platform.py`)

- **NEW package `tests/helpers/`** (`__init__.py` + `golden_platform.py`) under the already-packaged `tests` root
  (`tests/__init__.py` exists; `root_package = dadaia_workspace` in `setup.cfg`, so import-linter contracts are
  untouched — §9 ADR-1).
- **Public surface (consolidating the v0.1.55/58 golden-authoring law into code):**
  - `norm_path_line(line, ws)` — workspace-root scrub (`as_posix` + `str`), host-state canonicalization (the
    public-privacy denylist marker variant), separator canonicalization;
  - `norm_panel_body(body, ws)` — root scrub incl. JSON-escaped form + ISO-8601 timestamp scrub (`<TS>`);
  - `canon_env_line(line)` — OS-phrased exec-probe canonicalization (the D-CX-9 wrapper regex);
  - `sort_line_lists(obj)` — recursive sorted-multiset lock for lists-of-strings (order-insensitive,
    count-preserving), composing `canon_env_line`;
  - `is_env_doctor_line(line)` — environmental (git-dirty) line exclusion;
  - `assert_golden(path, obj, what, *, update_env="UPDATE_INSTALL_GOLDENS")` — the compare/update mechanism
    (sorted, `sort_keys`, trailing newline), regen only under the env flag, "fix the consumer, never the golden"
    message;
  - `norm_stderr(output)` — ANSI-strip + Rich box-drawing collapse (the v0.1.57 QA-atom `_norm_stderr` law).
- **Docstring carries the leak-class taxonomy** (host-state, iteration-order, OS-phrase, path/version, clock,
  Rich-width) with the v0.1.58 three-round-saga commits as the rationale record. The module is pure functions,
  stdlib + `re`/`json` only, no fixtures.

### FR2 — Byte-identical adoption (golden-first; zero golden regen)

- The **5 trio-carrying files** re-point to `tests.helpers.golden_platform`:
  `tests/unit/infrastructure/test_install_target_goldens.py`,
  `tests/unit/infrastructure/test_public_assets_profile.py` (killing the cross-test-module import),
  `tests/integration/test_plugin_install_goldens.py`, `tests/integration/test_plugin_projection.py`,
  `tests/e2e/features/test_plugin_pipeline.py`. Per-file local wrappers are deleted; genuinely test-local logic
  (e.g. golden-file constants, capture functions) stays local.
- The **8 `_norm_stderr` copies** re-point to `golden_platform.norm_stderr` (pure function move).
- **AC-1 proof:** every committed `_golden/*.json` file is **byte-unchanged** in the adoption commit, and the full
  suite is green with `UPDATE_INSTALL_GOLDENS` **unset**. Adoption that requires a golden regen is a defect.
- The bespoke normalizers in `test_api_golden.py`, `test_fragment_gate_goldens.py`, `test_doctor_golden.py` are
  **NOT force-migrated** this release (each carries test-specific scrubs); they may adopt shared primitives where
  drop-in. Residual consolidation → backlog note at CLOSURE if skipped.

### FR3 — Workflow-spawn entry-harness auto-default (implements the AGENTS.md convention)

- **NEW `core/session_env.entry_harness() -> str | None`** (stdlib-only, same core leaf): resolution order
  (§9 ADR-3) — (1) `DADAIA_ENTRY_HARNESS` env var when it holds `codex`/`pi` (the operator/PI-seam pin);
  (2) `CODEX_SESSION_ID` present ⇒ `"codex"`; (3) otherwise `None` (covers Claude entry — Layer-1-only, never a
  workflow harness — and plain shells/CI).
- **CLI default becomes the sentinel `"auto"`** at all 12 `--harness` option sites in
  `cli/commands/lifecycle.py`, resolved by ONE shared helper: explicit value ⇒ unchanged behavior; `auto` ⇒
  `entry_harness() or "fake"`. The `--step-harness` overrides and the LAW-1 rejection of `claude` are untouched.
- **Never silent (loud echo).** Whenever the harness was auto-defaulted to a real worker, the verb prints one line
  BEFORE spawning: `[harness] auto-default: <name> (from entry session; pass --harness to override)`. Resolving to
  `fake` prints nothing (current behavior preserved).
- **Hermetic under test.** A shared autouse guard (extending `tests/fixtures/harness_env.py`) scrubs
  `DADAIA_ENTRY_HARNESS` + `CODEX_SESSION_ID` + `CLAUDE_CODE_SESSION_ID` for the lifecycle CLI test envelope, so
  the suite resolves `fake` regardless of the developer's entry harness — a developer running pytest inside a
  codex TUI must never trigger a real worker spawn from a defaulted test.
- **Help text updated** at all 12 sites: `"auto (entry session) | fake | codex | pi (claude is Layer-1 only)"`.

### FR4 — PI entry-signal seam (dadaia-owned, post-trust)

- PI exposes **no native session env var** (read fact). The seam is dadaia-owned: the Ring-1 extension
  `public/pi/extensions/dadaia-sdd-gate.ts` sets `process.env.DADAIA_ENTRY_HARNESS = "pi"` **at factory load**
  (guarded: only when unset, so an operator pin wins). PI tool subprocesses (bash → `dadaia lifecycle …`) inherit
  the pi process env, so FR3 step (1) resolves `pi`.
- **Post-trust honesty:** pre-trust (extension not loaded) there is no signal and the default stays `fake` —
  documented in the extension header + `harness-pi` memory at CLOSURE. No secrets, no operator paths (public-privacy
  law); re-projected via `public stage/install`.
- **Security posture (ARCH64-2):** <!-- AMEND:ARCH64-2 --> the `DADAIA_ENTRY_HARNESS` pin is **session-wide and
  credit-affecting** — every child process of the PI session inherits it, and an auto-defaulted `pi` worker
  spends real credits. The guardrails are structural: **set-only-when-unset** (an operator pin always wins),
  the FR3 **loud echo** on every real-worker auto-default (never silent), and the signal is **never derived
  from telemetry** (no session-file/mtime heuristics — the pin is the extension's explicit, post-trust act).
  The extension header documents all three.
- **Assertable without a TS runtime:** a contract test asserts the projected/staged extension source contains the
  guarded export line (grep-level), and the FR3 unit matrix covers `DADAIA_ENTRY_HARNESS=pi` ⇒ `pi`.

### FR5 — `tier:` → `dispatch_band:` source rename (tolerate-then-strip, v0.1.53 precedent)

- **Bodies (ai-engineer surface):** the `tier:` line becomes `dispatch_band:` in the 12 agent bodies
  (9 `public/agents/*.md` non-stub cores + 3 `public/plugins/*/agents/*.md`). Values unchanged (1/2/3).
- **Parser (software-engineer):** `features/agents/reader.py` prefers `dispatch_band`, **silently tolerates**
  legacy `tier:` as a deprecated fallback (a consumer workspace's stale projection must not warn-spam);
  missing-both keeps today's default-3 + warning (text updated to name `dispatch_band`). `MissingTierError` →
  `MissingDispatchBandError` with a module-level alias `MissingTierError = MissingDispatchBandError` kept for the
  deprecation window; `features/agents/__init__.py` re-exports both. The frontmatter allowlist carries both keys
  during the window.
- **Model + renderer:** `core/models/agent.py` `AgentDTO.tier` → `dispatch_band`;
  `features/panel/views/api_agents.py` renders `"dispatch_band"` (no JS consumer — read fact).
- **Contract test:** `tests/contract/test_agent_tier_taxonomy.py` asserts `dispatch_band` (numeric, 1/2/3) —
  the pinned `_CORE_MODEL_EFFORT` model/effort map and the roster counts are **unchanged** by this release.
- **Deliberate golden regens, enumerated (fate ledger):** the v0.1.58 panel golden
  (`panel_runtime_validation_v0158.json`) and any plugin golden embedding agent-body bytes or the API field are
  regenerated via their own `UPDATE_INSTALL_GOLDENS` mechanism, riding the FR1 layer, with the diff enumerated as
  EXACTLY the `tier`→`dispatch_band` token change (multiset diff, zero other delta). This lands strictly AFTER
  W1 (ordering law — §7).
- **Strip window recorded:** the legacy `tier:` fallback + alias are removed in a later release; backlog return
  `dispatch-band-legacy-fallback-removal` filed at CLOSURE with the dated expiry (deprecation-expiry law).

### FR6 — Fast-tier item re-baseline: disposition REJECTED (operator-overridable)

- `fast-tier-persona-validation` is dispositioned **`REJECTED — premise-dead post-2026-07-06 retier`** at CLOSURE
  (never deleted; reason recorded in the entry). Grounds (§9 ADR-5): the retier already delivers the off-uniform
  cost lever operator-live (5×fable-5 with effort bands + 4×opus + 3×sonnet plugin); no Layer-1 lane in the
  12-agent roster is honestly "mechanical" (v0.1.60 read-fact 3 re-verified); the `fast` tier remains
  registry-defined for telemetry pricing of historical haiku events — defined-but-unassigned is an honest state,
  not a defect.
- **The operator-checkpoint protocol is recorded anyway** (§8) so a future override or revival ships with its
  non-self-approvable validation design ready. No code change in this FR.

## 4. Non-goals

- **No forced migration** of the bespoke normalizers (`test_api_golden.py`, `test_fragment_gate_goldens.py`,
  `test_doctor_golden.py`) — shared primitives adopted only where drop-in (FR2).
- **No golden semantic change**: FR1/FR2 must not alter what any golden locks; FR5's regens are token-renames only.
- **No Layer-2 policy change**: the WorkflowModelProfile registry/overlay/resolver, `--step-model`, and the
  per-harness model catalog are untouched. The auto-default authors only the *default* of `--harness`.
- **No fast-tier assignment, no model/REGISTRY change, no roster change, no effort-map change** (the pinned
  2026-07-06 retier map is invariant this release).
- **No pi-native env dependency**: the PI seam is dadaia-owned (`DADAIA_ENTRY_HARNESS`); we do not parse pi
  internals or session files for entry detection.
- **No CSS token rename** (`--color-tier-1..3` accent tokens are panel styling, possibly dead post-Kanban —
  out of scope; noted for a future hygiene pass).
- **No lease/gate/spec_context change**; the v0.1.50 frozen no-steal suite is expected **zero-diff**.
- **No constitution amendment.**

## 5. Acceptance criteria

- **AC-1 (byte-identical adoption — golden-first):** the FR2 adoption commit changes **zero bytes** in every
  committed `tests/**/_golden/*.json`; full suite green with `UPDATE_INSTALL_GOLDENS` unset; the cross-test import
  in `test_public_assets_profile.py` is gone (grep: no `from tests.unit.infrastructure.test_install_target_goldens
  import`).
- **AC-2 (module contract):** `tests/helpers/golden_platform.py` exposes exactly the FR1 surface with the
  leak-class taxonomy docstring; unit tests cover each function against the known leak fixtures (denylist-marker
  variant, D-CX-9 Linux/Windows phrasings, unsorted list multiset, Rich box-wrapped stderr, JSON-escaped ws path,
  timestamp scrub). Import-linter untouched: `lint-imports --no-cache` = **8 kept / 0 broken**, ignore-cap
  UNCHANGED (tests are outside `root_package`).
- **AC-3 (auto-default matrix — RED-first):** with no `--harness` flag: `CODEX_SESSION_ID` set ⇒ resolved harness
  `codex` + the loud echo line; `DADAIA_ENTRY_HARNESS=pi` ⇒ `pi` + echo; `DADAIA_ENTRY_HARNESS=codex` beats a
  stale `CODEX_SESSION_ID`; only `CLAUDE_CODE_SESSION_ID` ⇒ `fake`, NO echo; no signal ⇒ `fake`, NO echo; explicit
  `--harness fake|codex|pi` always wins with NO auto-default echo. RED-first: pre-change the default is the literal
  `"fake"` at every site. Covered at the resolver unit level AND at ≥ 2 verb CLI levels (one single-step verb + the
  pipeline).
- **AC-4 (hermeticity guard — pytest envelope AND CI job env; QA64-1):** <!-- AMEND:QA64-1 --> with the
  developer env carrying `CODEX_SESSION_ID` (simulated), the lifecycle CLI test envelope still resolves `fake`
  via the autouse scrub — asserted by a test that sets the var around the guard. No test may spawn a real worker
  from a defaulted harness. **CI-side:** a trivial CI-scoped assert (active only when `GITHUB_ACTIONS` is set)
  proves the GHA quality jobs' env carries NONE of the three entry-signal vars (`DADAIA_ENTRY_HARNESS`,
  `CODEX_SESSION_ID`, `CLAUDE_CODE_SESSION_ID`) — so no CI shell step can auto-default a real worker outside
  pytest either; skipped locally (a developer inside a codex TUI legitimately carries the var).
- **AC-5 (PI seam):** the staged + projected `dadaia-sdd-gate.ts` contains the guarded
  `DADAIA_ENTRY_HARNESS = "pi"` export (set-only-when-unset); `public doctor` stays green incl.
  `[ok] public-privacy`; the FR3 matrix covers the `pi` value end-to-end.
- **AC-6 (rename completeness — RED-first):** post-FR5, `grep -rn "^tier:" dadaia_workspace/public/agents
  dadaia_workspace/public/plugins/*/agents` returns **zero** lines; the renamed contract test asserts
  `dispatch_band` on all 12 bodies with the pinned model/effort map byte-unchanged; `api_agents` renders
  `"dispatch_band"`; the reader fallback test proves a legacy `tier:`-only body still resolves its band silently
  (and missing-both still defaults 3 + warning). RED-first: pre-change the contract test reads `tier`.
- **AC-7 (deliberate regen enumeration):** every golden regenerated by FR5 is listed in the task's fate ledger with
  a multiset diff proving the delta is EXACTLY the `tier`→`dispatch_band` token change (zero other delta, zero
  removals) — never a silent regen.
- **AC-8 (disposition sweep):** CLOSURE dispositions `golden-platform-normalization-layer`,
  `workflow-spawn-entry-harness-autodefault`, `tier-taxonomy-rename` as `DELIVERED — v0.1.64` and
  `fast-tier-persona-validation` as `REJECTED — premise-dead post-2026-07-06 retier (operator-ratified or
  operator-overridden per handoff decision)`; backlog return `dispatch-band-legacy-fallback-removal` filed.
- **AC-9 (mutation-sanity — sabotage → FAIL → revert, per new test class):** (a) break `sort_line_lists` (drop the
  sort) ⇒ an adopted golden test FAILS on the iteration-order fixture; (b) break `canon_env_line` (return input) ⇒
  the D-CX-9 phrasing unit test FAILS; (c) make the auto-default resolver ignore `DADAIA_ENTRY_HARNESS` ⇒ the AC-3
  precedence test FAILS; (d) drop the loud echo ⇒ the AC-3 echo assert FAILS; (e) make the reader reject legacy
  `tier:` ⇒ the AC-6 fallback test FAILS; (f) point one adopter back at a local stale copy ⇒ the AC-1 grep test
  FAILS. Each captured on its task line, then reverted.
- **AC-10 (full gates):** `ruff format --check`, `ruff check --no-cache`, `mypy --strict`, full **unpiped**
  `pytest` (real exit), `lint-imports --no-cache` (8/0, ignore-cap unchanged), `dadaia specs doctor` (exit 0),
  `dadaia backlog doctor` (exit 0); ship wave runs `dadaia public stage` → `install --target all` → confirming
  `public doctor` (`[ok] public-privacy`, exit 0); v0.1.50 frozen no-steal suite **zero-diff**. *(PE runs no
  shell — commands surfaced to PM/operator or devops-engineer.)*
- **AC-11 (fate ledger, per wave):** each wave records concrete files + fates (NEW/EDIT/DELETE-local-helper/
  REGEN-golden); every move/repoint grep includes `tests/` AND non-import textual references. No implementation
  wave stages `specs/backlog/**` (dispositioned at CLOSURE).

## 6. Consumed backlog

| Item | Kind | Priority | Consumed → FR | Disposition intent (CLOSURE) |
|---|---|---|---|---|
| `golden-platform-normalization-layer` | backlog (candidate) | MEDIUM | shared module → FR1; byte-identical adoption → FR2 | `DELIVERED — v0.1.64` |
| `workflow-spawn-entry-harness-autodefault` | backlog (candidate) | MEDIUM | auto-default → FR3; PI seam → FR4 | `DELIVERED — v0.1.64` |
| `tier-taxonomy-rename` | backlog (candidate) | LOW | source rename → FR5 | `DELIVERED — v0.1.64` |
| `fast-tier-persona-validation` | backlog (candidate) | MEDIUM | re-baseline → FR6 (no code) | `REJECTED — premise-dead post-2026-07-06 retier` (operator-overridable — handoff `decisions_required`) |

**Backlog returns (filed at CLOSURE):** `dispatch-band-legacy-fallback-removal` (strip the legacy `tier:` reader
fallback + `MissingTierError` alias after the window); optionally `golden-normalizer-residual-consolidation` if the
bespoke normalizers adopt nothing.

**Frozen-suite check — NO interaction.** No `spec_context`/lease/gate path is entered. Expect zero frozen-file diff.

## 7. Risks & ordering laws

- **Ordering law: FR1/FR2 land FIRST.** FR5's deliberate golden regens must ride the shared layer, so the
  rename wave is strictly after the normalization wave (one regen mechanism, one normalization truth).
- **Auto-default cost risk (stale inherited `CODEX_SESSION_ID`).** `session_env` documents ids may be inherited
  stale from a parent shell — an auto-defaulted `codex` could spend real credits from a non-codex shell.
  Mitigations: the loud echo (never silent), `DADAIA_ENTRY_HARNESS` pin beats it, explicit `--harness fake`
  always available, AC-4 hermeticity for the test suite. Residual risk accepted and documented in help text.
- **Rename blast into consumer projections.** A consumer workspace's stale `.claude/agents/*.md` still carries
  `tier:` until re-projection; the silent legacy fallback (FR5) prevents warning-spam and wrong-band regressions.
- **Golden regen discipline.** Any FR5 regen whose diff is not exactly the token rename indicates an unintended
  behavior change — AC-7 makes that a hard stop, not a shrug.
- **PI seam is post-trust only.** Pre-trust PI sessions get no auto-default (resolve `fake`); honest and
  documented — not a defect. Do NOT fake the signal from telemetry files.
- **Self-hosting instance write at ship (AC-10).** Reconciled only via stage → install → doctor, never hand-edits.

## 8. Recorded protocol — operator-checkpoint AC for any future fast-tier assignment

Recorded as a design artifact (FR6; no code this release). If the operator overrides ADR-5 (or a future release
revives a fast-tier assignment), its SPEC MUST carry this AC verbatim-in-spirit:

> **AC-OPCHECK (operator-live equal-quality checkpoint — non-self-approvable):** the release selects ONE bounded
> candidate lane and produces a **side-by-side evidence pair**: the SAME task input executed on the incumbent
> model and on the `fast` (haiku) model, both transcripts + artifacts committed as report evidence under
> `.dadaia/reports/<ctx>/…`. The release then **BLOCKS at an explicit operator checkpoint**: the operator (live)
> compares the pair and records an explicit verdict line (`equal-quality: yes|no + rationale`) that is pasted into
> CLOSURE §Validations with evidence type `operator-live`. **No agent, reviewer, or workflow may self-approve
> equal-quality**; absent the operator verdict the assignment reverts and the item re-dispositions `DEFERRED`.
> The assignment ships only behind `equal-quality: yes`.

## 9. Grill record — findings + ADRs (inspection-first; operator-overridable)

Findings resolved via inspection (no operator question needed): the five helper-copy sites and the cross-test
import (F-1, → FR1/FR2); the 12 `--harness` sites + the absence of any PI-native env signal (F-2, → FR3/FR4); the
exact rename blast radius incl. the **stale dossier claim** that the Codex frontmatter parser reads `tier` (it
does not — registry-Tier-only) (F-3, → FR5); the **stale dossier premise** on fast-tier (uniform opus) vs the
pinned 2026-07-06 retier map (F-4, → FR6).

- **ADR-1 — shared-module location = NEW `tests/helpers/` package.** `tests` is a real package (`__init__.py`
  everywhere) and cross-test imports already occur — formalize into `tests/helpers/golden_platform.py`.
  Outside `setup.cfg` `root_package = dadaia_workspace`, so the 8 import-linter contracts are untouched.
  REJECTED: `tests/_golden_lib` (underscore collides with the `_golden` fixture-data dirs; helpers are code, not
  fixtures); `tests/fixtures/` (namespace dir without `__init__`, hosts env fixtures — keep single-purpose).
- **ADR-2 — adoption scope = 5 trio files + 8 `_norm_stderr` copies, byte-identical; bespoke normalizers optional.**
  Zero-golden-regen is the acceptance proof; forced migration of test-specific scrubs is churn without payoff.
- **ADR-3 — entry-signal design = `DADAIA_ENTRY_HARNESS` pin > `CODEX_SESSION_ID` > fake; PI via the Ring-1
  extension exporting the pin (FR4).** Grounded: PI exports no session env var; the extension runs in the pi
  process pre-tool, so children inherit. Claude entry maps to `fake` (Layer-1-only). Loud echo mandatory.
  REJECTED: parsing `~/.pi/agent/sessions/` mtimes for entry detection (heuristic, races, telemetry-coupled);
  codex-only with no PI story (the seam is cheap and dadaia-owned, so take it now — this ALSO satisfies the
  backlog's sanctioned codex-only fallback if the operator strips FR4).
- **ADR-4 — rename back-compat = tolerate-then-strip (v0.1.53 `agent_tier` precedent).** Reader prefers
  `dispatch_band`, silently accepts legacy `tier:`; all 12 shipped bodies renamed NOW; alias
  `MissingTierError = MissingDispatchBandError`; strip tracked by the `dispatch-band-legacy-fallback-removal`
  return with a dated expiry. REJECTED: hard cut (stale consumer projections would warn-spam/default-3 until
  re-install); renaming only docs (that was v0.1.60 — the item exists to fix the source).
- **ADR-5 — fast-tier recommendation = REJECT as premise-dead (operator-overridable; surfaced to PM).** Grounds in
  §1 read-fact 4 + FR6. The operator-checkpoint protocol is recorded (§8) so an override loses nothing.

## 10. Memory files affected at CLOSURE

- `specs/memory/quality-assurance.md` — golden-authoring law now points at the ONE shared module (code truth).
- `specs/memory/tech-stack.md` — `dispatch_band` taxonomy wording; entry-harness auto-default resolution chain.
- `specs/memory/product/agents/agent-orchestration.md` — numeric band key renamed; taxonomy-test pointer.
- `specs/memory/product/sdd/dadaia-workflows.md` + `lifecycle-foundation.md` — harness default = auto-from-entry.
- `specs/memory/product/harness/harness-pi.md` — the `DADAIA_ENTRY_HARNESS` post-trust seam **including the
  ARCH64-2 security-posture note: the pin is session-wide and credit-affecting; set-only-when-unset; loud echo
  on auto-default; never derived from telemetry.** <!-- AMEND:ARCH64-2 -->
- `specs/memory/product/harness/harness-codex.md` — entry-signal note (`CODEX_SESSION_ID` → auto-default).
- `specs/memory/product/catalog.json` regen if any tldr/summary changes (`dadaia memory catalog generate`).
- **Shared-atom merge order (Ruling 64-B / RULING B — ARCHX-2 + QAX-2):** <!-- AMEND:ARCHX-2 --> shared with
  siblings: `quality-assurance.md` (v0.1.61 ×2, v0.1.62, this release), `tech-stack.md` (v0.1.61, this release),
  `agent-orchestration.md` (v0.1.61, this release), `dadaia-workflows.md`/`lifecycle-foundation.md` (v0.1.61
  pass A / v0.1.62, this release). **This release closes LAST: REBASE each shared atom on the siblings' closed
  state (never revert a sibling's correction); the `catalog.json` regen includes all prior tldr/summary
  deltas.**
