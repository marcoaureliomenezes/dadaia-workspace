# PLAN — v0.1.64 — Platform Ergonomics & Tiering

**Status:** Aprovado

Six waves (W0–W5). **Ordering law (SPEC §7): W1 (FR1/FR2 shared normalization layer, zero-golden-regen) lands
FIRST**; the W3 rename's deliberate golden regens ride that layer. W2 (harness auto-default + PI seam) is
file-disjoint from W1/W3 and may run between them, but stays sequential (single implementer, no parallel `[-]`).
FR6 is definition + closure work only (no implementation wave).

## Strategy

- **Golden-first, twice.** W1's acceptance IS the golden set: adoption is correct iff every committed
  `_golden/*.json` is byte-unchanged and the suite is green without `UPDATE_INSTALL_GOLDENS`. W3 then performs the
  only sanctioned regens (panel/API-field goldens), each enumerated as a pure `tier`→`dispatch_band` token diff
  (AC-7) via the shared `assert_golden` mechanism.
- **One resolver, twelve sites.** FR3 centralizes default resolution in one helper (`core/session_env.entry_harness`
  + one lifecycle-CLI shim); the 12 `--harness` option sites change only their default literal (`"fake"` → `"auto"`)
  and help text — no per-verb logic.
- **Tolerate-then-strip (v0.1.53 precedent).** W3 renames all shipped bodies + parser/model/renderer in one wave,
  keeps the silent legacy fallback + `MissingTierError` alias, and files the strip as a dated backlog return.
- **No fast-tier code.** FR6 is a disposition + the §8 recorded protocol; the operator decision is carried in the
  definition handoff (`decisions_required`), ratified or overridden before CLOSURE.

## Layers affected

- `tests/helpers/` (NEW — outside import-linter `root_package`; no contract change), 5 golden test files,
  8 `_norm_stderr` CLI test files (W1).
- `core/session_env.py` (core leaf, stdlib-only), `cli/commands/lifecycle.py` (12 option sites + 1 resolver shim),
  `tests/fixtures/harness_env.py` (+ conftest wiring), `public/pi/extensions/dadaia-sdd-gate.ts` (W2).
- `public/agents/*.md` (9) + `public/plugins/*/agents/*.md` (3) (ai-engineer surface), `features/agents/reader.py`
  + `__init__.py`, `core/models/agent.py`, `features/panel/views/api_agents.py`, contract/unit/golden tests (W3).
- `specs/**` memory + backlog dispositions (W5, CLOSURE phase only).

## Wave map

- **W0 — definition (this document set).** SPEC/PLAN/TASKS from the 2026-07-07 code read; inspection-first grill on
  the picked set (findings F-1..F-4 + ADR-1..5 in SPEC §9; two stale dossier premises corrected); FR6 REJECT
  recommendation surfaced to PM as a handoff decision. **Review fold (2026-07-07, APPROVE-with-amendments):**
  QA64-1..3 + ARCH64-2 + ARCHX/QAX folded with `<!-- AMEND:… -->` markers; PM Rulings 64-A/64-B in SPEC §0
  (fixed order — this release LAST; W3 rebases the 12 bodies onto v0.1.62/63 and re-verifies BOTH greps;
  shared-atom closure merge order). `Aprovado` after re-verify; definition commit.
  Owner: product-engineer (orchestrated).

- **W1 — FR1/FR2 shared golden platform-invariance module + byte-identical adoption (golden-first).**
  1. NEW `tests/helpers/__init__.py` + `tests/helpers/golden_platform.py` — the FR1 surface (`norm_path_line`,
     `norm_panel_body`, `canon_env_line`, `sort_line_lists`, `is_env_doctor_line`, `assert_golden`, `norm_stderr`)
     with the leak-class taxonomy docstring. Unit tests against known leak fixtures (AC-2).
  2. Re-point the 5 trio files (kill the `test_public_assets_profile.py` cross-test import; delete local copies) +
     the 8 `_norm_stderr` copies. **Proof: zero bytes changed under `tests/**/_golden/`** (AC-1), full suite green,
     `UPDATE_INSTALL_GOLDENS` unset.
  - Sabotages AC-9(a)(b)(f). Fate ledger enumerates every deleted local helper + its adopter, **and pins the
    branch-point `pytest --collect-only -q` count (QA64-2/QAX-4 — first implementation wave; re-validated at
    closure).** <!-- AMEND:QA64-2 --> Owner: software-engineer.

- **W2 — FR3/FR4 entry-harness auto-default + PI seam (file-disjoint from W1).**
  1. `core/session_env.entry_harness()` — precedence `DADAIA_ENTRY_HARNESS` (codex|pi) > `CODEX_SESSION_ID` ⇒ codex
     > `None`. Unit matrix incl. precedence + claude-entry ⇒ None.
  2. Lifecycle CLI: default literal `"auto"` at the 12 sites + ONE shared `_resolve_default_harness()` shim feeding
     the existing `_resolve_harness`; loud echo line on any real-worker auto-default; help text updated.
  3. Hermeticity: autouse env scrub (extend `tests/fixtures/harness_env.py`) over the lifecycle CLI test envelope;
     AC-4 test simulates a developer `CODEX_SESSION_ID`.
  4. `dadaia-sdd-gate.ts`: guarded `if (!process.env.DADAIA_ENTRY_HARNESS) process.env.DADAIA_ENTRY_HARNESS = "pi"`
     at factory load + header note (post-trust, no secrets); grep-level contract test on the staged source.
  - Tests: AC-3 matrix (resolver unit + ≥2 verb CLI levels, RED-first vs the literal `"fake"` default), AC-4
    (**both halves — the autouse pytest scrub AND the CI-scoped GHA-env assert active under `GITHUB_ACTIONS`,
    skipped locally; QA64-1** <!-- AMEND:QA64-1 -->), AC-5.
    Sabotages AC-9(c)(d). Owner: software-engineer (TS edit is a one-line lib-asset change: software-engineer with
    ai-engineer sign-off on the `public/**` surface; the extension header carries the ARCH64-2 security-posture
    note — session-wide credit-affecting pin, set-only-when-unset, loud echo, never telemetry-derived).

- **W3 — FR5 `tier:` → `dispatch_band:` rename (strictly after W1; LAST writer of the 12 bodies — Ruling 64-A).**
  <!-- AMEND:ARCHX-1 --> Rebase onto v0.1.62 W3 (handoff prose) + v0.1.63 W2/W3 (`skills:` frontmatter) landed
  states; after the rename, re-run the `^tier:` grep AND verify v0.1.62's AC-6 adoption grep stays satisfied.
  1. ai-engineer: rename the frontmatter key in the 12 bodies (values unchanged).
  2. software-engineer: reader (prefer `dispatch_band`, silent legacy fallback, allowlist both keys, warning text,
     `MissingDispatchBandError` + alias), `AgentDTO.dispatch_band`, `api_agents` field, contract test rewrite
     (pinned model/effort map UNCHANGED), reader fallback tests.
  3. Deliberate golden regens via the W1 `assert_golden` mechanism: enumerate each regenerated file with a multiset
     diff proving EXACTLY the token rename (AC-7); `install_target_resolution`/`doctor` goldens expected untouched
     (no agent-body bytes) — verify, don't assume.
  - Tests: AC-6 (RED-first), AC-7. Sabotage AC-9(e). Sequential inside the wave (bodies before parser tests
    finalize). Owners: ai-engineer (bodies) → software-engineer (code), sequential, no parallel `[-]`.

- **W4 — gates + projection ship.** Full gates (AC-10): ruff both, mypy --strict, unpiped pytest, lint-imports 8/0
  ignore-cap unchanged, specs doctor, backlog doctor; frozen no-steal suite zero-diff check; `public stage` →
  `install --target all` → confirming `public doctor` (`[ok] public-privacy`) so the live instance carries the
  renamed bodies + the PI extension line. Reviews per release-governance cadence; push gated by the security
  verdict chokepoint. Owner: software-engineer (orchestrated; shell commands surfaced by PM/operator).

- **W5 — CLOSURE (MEMORY phase).** CLOSURE.md with Validations triples + Drifts + Dispositions sweep (3×
  `DELIVERED — v0.1.64`; `fast-tier-persona-validation` `REJECTED — premise-dead post-2026-07-06 retier` **after**
  the operator ratifies/overrides the handoff decision); backlog return `dispatch-band-legacy-fallback-removal`
  (+ optional `golden-normalizer-residual-consolidation`); memory updates per SPEC §10 + catalog regen; archive
  `git mv`. **Merge order (Ruling 64-B): this release closes LAST — rebase `quality-assurance.md`,
  `tech-stack.md`, `agent-orchestration.md`, `dadaia-workflows.md`/`lifecycle-foundation.md` on the siblings'
  closed state (never revert their corrections); catalog regen includes all prior deltas.**
  <!-- AMEND:ARCHX-2 --> Owner: product-engineer.

## Validation plan

| Gate | Proof |
|---|---|
| W1 exit | zero-byte `_golden/**` diff + suite green (no regen flag) + AC-2 unit fixtures + sabotages a/b/f |
| W2 exit | AC-3 matrix green (RED-first shown) + AC-4 scrub test + AC-5 grep/privacy + sabotages c/d |
| W3 exit | AC-6 grep-zero `^tier:` + contract test on `dispatch_band` + fallback test + AC-7 enumerated diffs + sabotage e |
| W4 exit | AC-10 full-gate transcript + frozen-suite zero-diff + confirming `public doctor` exit 0 |
| W5 exit | disposition sweep complete + memory truth updated + `dadaia specs doctor` exit 0 + archive |

## Technical risks (mitigations in SPEC §7)

1. Stale inherited `CODEX_SESSION_ID` auto-spends codex credits → loud echo + `DADAIA_ENTRY_HARNESS` pin +
   explicit-flag override + hermetic tests.
2. A W3 golden regen hides a real behavior change → AC-7 multiset-diff enumeration is a hard stop.
3. Consumer stale projections still carrying `tier:` → silent legacy fallback (no warn-spam, correct band).
4. PI pre-trust sessions get no signal → documented honest degradation to `fake`; never faked from telemetry.
5. Suite non-hermeticity spawning real workers from developer env → AC-4 autouse scrub, asserted not assumed.
