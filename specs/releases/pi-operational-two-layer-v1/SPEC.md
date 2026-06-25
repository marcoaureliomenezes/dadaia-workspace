# SPEC — Release `pi-operational-two-layer-v1`

> **Status:** Aprovado
> **Release ID:** pi-operational-two-layer-v1
> **Owner:** product-engineer
> **Branch:** `feature/pi-operational-v1`
> **Created:** 2026-06-25

## Objective

Make PI (`pi-coding-agent`) **fully operational** in dadaia-workspace at **both agentic
layers**, name the two-layer model in the constitution, and reach **zero
memory↔implementation drift** for the PI / two-layer reality that two prior shipped
releases (`multiharness-engine-v0116`, `pi-fourth-harness-v1`) delivered in code but left
undocumented across the doc/memory/public surface.

At the end of this release the operator can:

- **Layer 1** — launch `pi` in the workspace terminal and have PI grounded in the dadaia
  law (AGENTS.md read natively up-tree) plus a minimal `.pi/` projection that points at
  the law and names the `dadaia` CLI.
- **Layer 2** — already shipped: drive `dadaia lifecycle … --harness pi` so any lifecycle
  step runs on the `PI_HEADLESS` worker behind `AgentRuntimePort`.

…and a memory drift re-audit at CLOSURE reports the PI / two-layer surface drift resolved.

## Problem statement

PI shipped at **Layer 2** as a real fourth `AgentRuntimeKind` (`PI_HEADLESS`,
`PiHeadlessAdapter`, wired in `container.py`, selectable via `--harness pi`), and the three
*engine* memory atoms (`architecture.md`, `tech-stack.md`, `lifecycle-foundation.md`) were
updated accurately. But:

- PI is **invisible at Layer 1** — there is no `.pi/` projection tree, so an operator
  cannot "enter pi" with dadaia context the way `claude`/`codex`/`opencode` project.
- The **two-layer agentic model** (Layer 1 = entry harness; Layer 2 = worker harness
  behind `AgentRuntimePort`) — the conceptual core of both shipped releases — is named
  **nowhere** in the constitution, memory, or public surface (audit G-1, HIGH).
- The **constitution is silent** on the two layers and on PI as a worker runtime
  (constitution-consistency findings; F12).
- The **AI-entity surface** carries 0 PI references and stale closed-3-harness framing
  (audit D-4 HIGH, D-5, G-3, F6–F8), and the `ai-engineer` persona — the harness owner —
  still says "two runtime harnesses".
- Tooling drift: `lint-memory-atoms.py` WARNs on legitimate headings (F9/M-5); the
  `dadaia memory catalog generate` CLI silently skips `index.md` regeneration (F10/M-4,
  product bug `memory-catalog-cli-skips-index-md`), leaving `index.md` stale (M-1).

The drift audit (`audit.md`) scored agent-surface **3/10** (floor breach) and mandated a
remediation release. This release is that remediation, scoped to the architect design doc.

## Authoritative design inputs (do not re-derive)

1. **Architect design doc** — `specs/audits/20260625T130028Z-ecddfd86/20260625T143000Z-ecddfd86-pi-operational-two-layer-design.md`.
   Contains the **exact ready-to-apply constitution amendment** (7 blocks: §0 two-layer
   subsection + `.pi/` layout entry + widened identity line + `ai-engineer` philosophy
   clause; §4 Layer-1-scoped honesty clause + PI row; §8 split matrix Layer-1 enforcement
   + Layer-2 worker posture with PI rows) and the **minimal `.pi/` projection shape +
   wiring contract** (Deliverable 2). Both anti-slop gates: PASS.
2. **Memory drift audit** — `specs/audits/20260625T130028Z-ecddfd86/audit.md`. The
   **F1–F12 fix set** (memory + public-surface + tooling/code drift). Every F-item is
   covered by a task in this release.
3. **EPIC** — `specs/backlog/pi-agent-fourth-harness.md`. This release delivers **WS-PI-3**
   (the `.pi/` first-layer projection) and a lightweight **WS-PI-5** pointer.
   **WS-PI-4** (Ring-1 `.pi/extensions/dadaia-sdd-gate.ts`) is explicitly **OUT**.

## Refinement note (grill substitution)

The mandatory release-definition grill was satisfied by the architect's design doc and the
project-auditor's drift audit, which together constitute the refined, conflict-resolved
picked set: the design doc resolved the open questions (scaffold-stub = no change;
`.pi/SYSTEM.md` points at the law, no restatement; PI Layer-1 posture = advisory +
chokepoint with Ring-1 deferred; OpenCode is the structural mirror for the installer) and
the audit produced the precise F1–F12 fix set with owners. No unresolved open question
blocks SPEC approval. The two seams the design doc flags as **operator-environment
verified, not offline** (the live `pi` binary's Layer-1 AGENTS.md native-read behavior and
the Layer-2 `pi --mode json` schema) are recorded as risks below.

## Scope — five threads (all in this release)

### Thread A — Constitution amendment (the central operator ask: name the two layers)
Apply the architect's 7 blocks to `specs/constitution.md` verbatim (Deliverable 1,
blocks 1.1–1.6): new §0 "The two agentic layers" subsection (Layer 1 = entry harness
`claude`/`codex`/`opencode`/`pi` governed by AGENTS.md + projected `.X/` assets; Layer 2 =
worker harness behind `AgentRuntimePort`, driven by `dadaia lifecycle` via SDK /
CLI-headless / RPC per harness; five `AgentRuntimeKind`s = FAKE, CODEX_EXEC, CLAUDE_SDK,
OPENCODE_RUN, PI_HEADLESS); `.pi/` added to the layout list (now ten entries, with the
post-trust executable trust-boundary note); widened §0 identity line; §4 honesty clause
scoped to Layer-1 entry enforcement + PI row (advisory + chokepoint, no Ring-1 — honesty
clause preserved); §8 matrix split into Layer-1 entry-harness enforcement (PI row) and a
Layer-2 worker-runtime posture note (5 kinds, only CLAUDE_SDK has Ring-1); `ai-engineer`
§0-philosophy clause widened to the four harnesses + both layers. **Requires operator
sign-off** (constitution is MUTATING product law). Owner: product-engineer.
**Scaffold stub** (`public/scaffold/constitution.md`) = **NO change** (architect ruling —
consumer template; injecting workspace concepts is a §12.3 fact-in-two-sources leak).

### Thread B — WS-PI-3 first-layer `.pi/` projection
NEW `dadaia_workspace/public/pi/` source tree (minimal): `.pi/settings.json` (smallest
valid PI-native settings object, generic only) + `.pi/SYSTEM.md` that POINTS AT AGENTS.md
and names the `dadaia` CLI/lifecycle (≤~50 lines, NO law restatement, inline trust-boundary
note) + optional `.pi/prompts/dadaia-context.md` affordance. Wire a `pi` target into
`infrastructure/public_assets.py` mirroring OpenCode (`_VALID_TARGETS` adds `"pi"`,
`_PI_DIRS` = `("prompts",)`, `_install_pi` mirroring `_install_opencode`, `"pi"` in the
`all` targets tuple + install dispatch), `[ok] pi:` doctor lines, register in
`.dadaia/agentic/manifest.json` (lib-originated), keep `[ok] public-privacy` green.
Owners: ai-engineer (author `public/pi/` assets), software-engineer (installer/doctor/
manifest wiring).

### Thread C — Root-whitelist update (CRITICAL sequencing — gates Thread B)
`.pi/` is a NEW top-level root entry; the `pre_gate` root-whitelist hook
(`dadaia_workspace/hooks/root_whitelist.py` `_WHITELIST`) currently blocks new root
entries, so without this thread the `.pi/` projection write is **mechanically gate-blocked**.
Add `.pi/` to `_WHITELIST`; update the projected `tmp-file-guardrail` rule
(`public/rules/tmp-file-guardrail.md`) root-whitelist table; update the Workspace Root Law
text in `public/data/AGENTS.md`; update any `dadaia doctor` ROOT check that enumerates the
whitelist. Owners: software-engineer (hook code + doctor ROOT check + tests),
ai-engineer (projected rule + AGENTS.md surface).

### Thread D — Memory + public-surface drift fixes (F1–F12, reach zero drift)
- **Memory atoms (F1–F5, F11; owner product-engineer):** `architecture.md` two-layer
  section + Layer-2 worker table (5 kinds) + scope parity table to Layer-1 + fix "três
  runtimes" framing; `product-vision.md` two-layer summary + 4-worker reality (gated on
  operator confirming `docs/01_medium_codex.md` stance — see risks); `multi-platform-parity.md`
  Layer-2 worker note distinguishing projection-parity from worker-runtime parity +
  PI post-trust-executable surface note; `harness-primitives.md` atom "15 agents" → "9
  core" + 4-harness/two-layer awareness; refresh `token_estimate` frontmatter (tech-stack,
  lifecycle-foundation, multi-platform-parity, spec-context-project); regenerate `index.md`
  (depends on F10).
- **Public surface (F6–F8; owner ai-engineer):** `public/agents/ai-engineer.md` ("two
  runtime harnesses" → four + PI row + two-layer + PI skill ref); `public/skills/
  harness-primitives/SKILL.md` (4-harness + two-layer, "9 core"); closed-3 enumerations in
  `rules/bug-registration-guardrail.md`, `data/AGENTS.md`, `plugins/sdd-gate.ts`,
  `skills/project-orchestration` made 4-aware or explicitly Layer-1-scoped.
- **Tooling/code (F9, F10; owner software-engineer):** `lint-memory-atoms.py` curated
  heading allowlist (add legitimate headings, resolve EN/PT canon, kill the heading
  WARNs); fix `features/specs/catalog.py` so `dadaia memory catalog generate` ALSO emits
  `index.md` (closes product bug `memory-catalog-cli-skips-index-md`).

### Thread E — "no 2 projects" pointer (lightweight WS-PI-5)
Add a deprecation `README.md` to `repos/dadaia-pi-workspace/` pointing at this release /
the EPIC (PI now lives in dadaia-workspace). Do **NOT** delete the repo. The formal
`dadaia context` DEAD-marking of `dadaia-pi-workspace` is a CLOSURE/operator follow-up (it
touches another repo and has known `dead()` bugs) — noted as a closure follow-up, not a
hard task. Owner: product-engineer (README, minimal/ADDITIVE-ish).

## Product deltas

- **Layer-1 PI affordance (new):** an operator can `pi` in the workspace and get a `.pi/`
  projection that orients PI to the dadaia law + CLI. (`dadaia public install --target pi`
  produces `.pi/`; `--target all` includes it.)
- **No new Layer-2 capability** — Layer-2 PI (`--harness pi`) already shipped; this release
  only documents it. No engine-spine change.

## Architecture deltas

- New per-target install branch (`_install_pi`) and target member (`pi`) in the public-asset
  distribution machinery, structurally mirroring the OpenCode target. No new mechanism.
- `.pi/` becomes an allowed workspace-root projection directory (root-whitelist + law text).
- The two-layer model and the Layer-2 worker-runtime set become explicitly documented in
  `architecture.md` (memory) — no code/layer change, documentation of existing reality.

## Tech-stack deltas

None material. PI runtime (`pi --mode json`, optional external Node binary) is already in
`tech-stack.md`; this release only refreshes its `token_estimate` frontmatter (F5).

## Security / operations deltas

- `.pi/**` is documented as a **post-trust, unsandboxed, executable-TypeScript** surface
  (a real privilege grant) in the §0 layout entry, `.pi/SYSTEM.md` inline note, and the
  relevant memory atom (multi-platform-parity / public-asset-distribution). No secrets, no
  operator-local paths in `public/pi/**`; the `[ok] public-privacy` gate must stay green.
- PI Layer-1 enforcement posture is honestly stated as **advisory + chokepoint-protected,
  no Ring-1** (the `pi` CLI exposes no pre-disk hook); the honesty clause of §4/§8 is
  preserved. Ring-1 (WS-PI-4) is deferred — the law and the shipped surface agree.

## Memory files affected at closure

- `specs/memory/architecture.md` — F1, D-1, D-2 (two-layer section, Layer-2 table, parity
  scope, "três runtimes" framing).
- `specs/memory/product/philosophy/product-vision.md` — F2 (gated on operator vision-doc
  confirmation).
- `specs/memory/product/platform/multi-platform-parity.md` — F3, G-2 (Layer-2 note + PI
  post-trust surface).
- `specs/memory/product/agents/harness-primitives.md` — F4 ("9 core" + 4-harness/two-layer).
- `token_estimate` frontmatter — `tech-stack.md`, `lifecycle-foundation.md`,
  `multi-platform-parity.md`, `spec-context-project.md` (F5).
- `specs/memory/product/index.md` — F11 (regenerated from catalog via F10).
- (Possibly a `public-asset-distribution` atom touch for the PI projection target + trust
  surface — confirmed at CLOSURE.)

## Acceptance criteria

1. **Constitution (Thread A):** §0 carries the "two agentic layers" subsection; the layout
   list has `.pi/` (ten entries) with the trust-boundary note; the §0 identity line names
   the four entry harnesses + both layers; §4 honesty clause is Layer-1-scoped with a PI
   row; §8 has a Layer-1 enforcement matrix (PI row) + a Layer-2 worker-runtime posture
   note (5 kinds, only CLAUDE_SDK Ring-1); the `ai-engineer` §0 clause names the four
   harnesses + both layers. `dadaia specs doctor` stays 0-error and SPEC-DOC-028 passes.
   Scaffold stub unchanged. Operator signed off on the constitution edit.
2. **`.pi/` projection (Threads B+C):** `dadaia public install --target pi` produces a
   `.pi/` tree (`SYSTEM.md` + `settings.json` [+ optional `prompts/`]); `--target all`
   includes `pi`; `dadaia public doctor` exits 0 with `[ok] pi:` lines and `[ok]
   public-privacy`; re-running install is idempotent; `.pi/**` is manifest-tracked
   (lib-originated); no private leak. A Write creating `.pi/...` is **not** blocked by the
   root-whitelist policy; AGENTS.md Workspace Root Law and the `tmp-file-guardrail` rule
   list `.pi/`; root-whitelist hook unit tests cover the `.pi/` allow.
3. **Zero drift (Thread D):** all F1–F12 applied; `lint-memory-atoms.py` no longer WARNs on
   the legitimate headings; `dadaia memory catalog generate` emits `index.md` and the
   lifecycle-foundation row is current; `token_estimate` frontmatter refreshed; the public
   surface (ai-engineer persona, harness-primitives skill, closed-3 enumerations) is
   4-harness / two-layer aware. A CLOSURE memory drift **re-audit** confirms the PI /
   two-layer surface drift resolved.
4. **Pointer (Thread E):** `repos/dadaia-pi-workspace/README.md` points at this release /
   the EPIC; the repo is not deleted; DEAD-marking recorded as a closure follow-up.
5. **Global gates:** `dadaia ci preflight` 4/4 + `lint-imports` 6/0 + `dadaia public doctor`
   exit 0 (`[ok] public-privacy` + `[ok] pi:`) + `dadaia specs doctor` 0 errors + a live
   `dadaia public install --target pi` smoke producing `.pi/` then a clean re-install.
6. **Gate ladder:** quality (qa-engineer) + security (security-reviewer) + code (code-reviewer)
   review APPROVE; commit + push + PR.

## Out of scope (explicit non-goals)

- **WS-PI-4** — the Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` pre-disk gate. PI Layer-1
  stays advisory + chokepoint. Deferred.
- **RPC / SDK transports** for PI (`pi --mode rpc`, a Python↔Node SDK bridge) — the engine
  is one-shot-per-step; deferred behind a concrete future need (EPIC anti-slop guard).
- **Deleting `repos/dadaia-pi-workspace/`** — never deleted (history/evidence). Only a
  deprecation README; DEAD-mark is an operator/closure follow-up.
- **WS-PI-6** telemetry adapter + academy doc — optional, gated on a real PI session
  source; not in this release.
- **`docs/01_medium_codex.md` amendment** — the normative vision doc is operator-owned;
  this release does not edit it. `product-vision.md` (F2) only proceeds after the operator
  confirms the doc's PI / 4-harness stance (risk below).
- **No engine-spine change** — `core/scope_match.py`, `agent_runner.py`, `phase_workflow.py`,
  `pipeline.py` are untouched (PI Layer-2 already shipped).
- **A dedicated `ai-harness-pi` deep skill** — the skill-vs-section decision (audit open
  question b) is deferred; this release makes `harness-primitives` 4-aware, not a new skill.

## Dependencies and risks

- **[HIGH — sequencing] Thread C BEFORE/WITH Thread B.** `.pi/` is a new root entry; the
  root-whitelist hook blocks new root dirs. If `.pi/` is not added to `_WHITELIST` first,
  `dadaia public install --target pi` (a write creating `.pi/`) is gate-blocked. Thread C's
  hook edit must land before the live `--target pi` smoke in Thread B.
- **[MEDIUM — operator-environment seam] Live `pi` Layer-1 AGENTS.md native-read.** The
  design assumes PI reads `AGENTS.md` up-tree natively (operator-confirmed, same as Codex/
  OpenCode). If PI needs an explicit import bridge, `.pi/SYSTEM.md` carries a one-line
  pointer-bridge (still a pointer, never a restatement). The `.pi/` *content* is
  faked/structural-tested + privacy/doctor-gated offline; the live PI load is the
  **unverified seam**. Verify at implement time.
- **[MEDIUM — operator-environment seam] Layer-2 `pi --mode json` schema.** Already shipped
  and faked-tested; the live schema is `tests/integration/pi_live/` opt-in
  (`DADAIA_PI_LIVE=1`), not offline-verified. Not changed by this release.
- **[MEDIUM — operator decision] product-vision (F2) gated on `docs/01_medium_codex.md`.**
  Memory must not unilaterally invent a 4th harness the vision doc omits. F2 proceeds only
  after the operator confirms the vision doc's stance; if unconfirmed at CLOSURE, F2 is
  deferred with a recorded reason and the constitution amendment (which documents
  implemented reality) lands independently.
- **[LOW] `--harness` help text (audit M-4/M-6).** The CLI `--harness` help omits `pi`
  though `_HARNESS_KINDS["pi"]` is wired — a trivial stale-text fix folded into Thread D
  surface honesty.
