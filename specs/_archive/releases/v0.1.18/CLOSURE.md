# Closure: Release — v0.1.18

> **Status:** Aprovado
> **Release ID:** v0.1.18
> **Owner:** product-engineer
> **Closed:** 2026-06-25

## Summary

v0.1.18 (pi-operational-two-layer) makes PI a **fully operational fourth harness at both
agentic layers** and, just as importantly, names the **two-layer agentic model** that two
prior shipped releases (`multiharness-engine-v0116`, `pi-fourth-harness-v1`) delivered in
code but left undocumented. From the product owner's view: an operator can now `pi` in the
workspace terminal and get a minimal `.pi/` projection that orients PI to the dadaia law +
the `dadaia` CLI (Layer 1), and continues to drive `dadaia lifecycle … --harness pi` so any
lifecycle step runs on the `PI_HEADLESS` worker behind `AgentRuntimePort` (Layer 2, already
shipped). The constitution, memory, and the AI-entity surface now all describe the four
entry harnesses, the five worker runtimes, and the Layer-1/Layer-2 distinction.

The release is the remediation mandated by the `20260625T130028Z-ecddfd86` drift audit,
which scored agent-surface 3/10 (floor breach). It applies the audit's full F1–F12 fix set:
the constitution two-layer amendment (Thread A), the new `.pi/` first-layer projection
target mirroring OpenCode plus its root-whitelist allowance (Threads B+C), the public-surface
de-staling of the `ai-engineer` persona / `harness-primitives` skill / closed-3 enumerations
(Thread D public half), the memory atom two-layer documentation (Thread D memory half), the
`lint-memory-atoms.py` heading allowlist + `dadaia memory catalog generate` index.md emission
tooling fixes, and the `dadaia-pi-workspace` deprecation pointer (Thread E). PI and the
two-layer model are now represented across both layers, both the law and the surface that
orients the agent fleet.

WS-PI-4 (Ring-1 `.pi/` pre-disk gate), WS-PI-6 (telemetry), the RPC/SDK transports, and the
formal `dadaia-pi-workspace` context DEAD-mark remain deferred (see Backlog returns / Dispositions).

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| (release definition) | Define release v0.1.18 (SPEC/PLAN/TASKS; grill satisfied by design doc + drift audit) | `f980cd7` |
| T-PIO-01 | Constitution amendment blocks 1.1–1.6 (two-layer §0 + `.pi/` layout + §4 PI row + §8 split matrix); operator sign-off | `97cd5f6` |
| T-PIO-02 | Author `public/pi/` source tree (`SYSTEM.md` points-at-law, `settings.json`, `prompts/`) | `97cd5f6` |
| T-PIO-03 | Wire `pi` install target (`_install_pi`, `_VALID_TARGETS`, `_PI_DIRS`, `all` tuple) — TDD | `97cd5f6` |
| T-PIO-04 | `dadaia public doctor` `[ok] pi:` lines + manifest tracking — TDD | `97cd5f6` |
| T-PIO-05 | Add `.pi/` to `pre_gate` root-whitelist hook + doctor ROOT check — TDD | `97cd5f6` |
| T-PIO-06 | Projected root-law surface for `.pi/` (`tmp-file-guardrail.md`, `data/AGENTS.md`) | `97cd5f6` |
| T-PIO-07 | Live `--target pi` projection smoke + clean idempotent re-install | `97cd5f6` |
| T-PIO-08 | Public-surface drift F6–F8 (`ai-engineer.md`, `harness-primitives/SKILL.md`, closed-3 enumerations, `--harness` help) | `97cd5f6` |
| T-PIO-09 | `lint-memory-atoms.py` heading allowlist (F9, Group D) — TDD | `97cd5f6` |
| T-PIO-10 | `dadaia memory catalog generate` emits `index.md` (F10/M-4) — TDD | `97cd5f6` |
| T-PIO-11 | Regenerate `index.md` from catalog via the fixed CLI (F11) | `f5f22c7` (coordinator) |
| T-PIO-12 | Memory atom drift fixes F1–F4 (architecture two-layer section + Layer-2 table; multi-platform-parity Layer-2 note; harness-primitives "9 core" + two-layer) | this closure |
| T-PIO-13 | product-vision (F2) two-layer summary + 4-worker reality (operator confirmed PI as 4th harness) | this closure |
| T-PIO-14 | `token_estimate` frontmatter refresh (F5) | this closure |
| T-PIO-15 | Global gates (preflight 4/4 + lint-imports 6/0 + public doctor + specs doctor + live `--target pi` smoke) | `57539a2` |
| T-PIO-16 | CLOSURE (this document) + memory finalization + drift re-audit + archive | this closure / coordinator |
| T-PIO-17 | Deprecation README pointer for `repos/dadaia-pi-workspace/` | `97cd5f6` |

> Commit map: release definition `f980cd7`; implementation `97cd5f6`; review fixes `f5f22c7`;
> CI fix `57539a2`; this CLOSURE (memory finalization). T-PIO-11/T-PIO-16 are coordinator-finalized.

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Format + lint + strict-type + tests (4 checks) | `dadaia ci preflight` | ```text
preflight 4/4 PASS (ruff format --check; ruff check; mypy --strict; pytest)
``` |
| Architecture contracts (layering) | `lint-imports` | ```text
Contracts: 6 kept, 0 broken.
``` |
| Public projection consistency incl. PI target | `dadaia public stage && install --target all && public doctor` | ```text
exit 0; [ok] pi:SYSTEM.md, [ok] pi:settings.json (+ prompts); [ok] public-privacy
``` |
| Live `--target pi` projection smoke + idempotent re-install | `dadaia public install --target pi` (×2) | `.pi/` tree produced; second run drift-free; `public doctor` exit 0 |
| SDD structural health | `dadaia specs doctor` | ```text
0 errors (warnings reduced after token_estimate refresh + heading allowlist)
``` |
| Branch push + GitHub Actions CI | CI for `57539a2` | all jobs green |
| QA gate | qa-engineer APPROVE handoff | `.dadaia/handoff/dadaia-workspace/…-qa-engineer-v0.1.18-*.handoff.json` |
| Code review | code-reviewer APPROVE-WITH-NITS (nits fixed in `f5f22c7`) | `.dadaia/handoff/dadaia-workspace/…-code-reviewer-v0.1.18-*.handoff.json` |
| Security verdict (push gate, ×3) | security-reviewer APPROVE handoff | last keyed to `57539a2` (`metrics.commit_sha = 57539a2`) |
| PR | `gh pr create` | PR #66 opened |

## Drifts

### release-renamed-pi-operational-two-layer-to-v0.1.18

**Description:** The release was scoped/named `pi-operational-two-layer-v1` during definition,
but `dadaia specs doctor` (SPEC-DOC-027) requires release directory names to match the SemVer
form `^v\d+\.\d+\.\d+$`. The descriptive name failed that check, so the release was renamed to
`v0.1.18` (the next PATCH after the v0.1.x line). This exposed a tooling contradiction:
`dadaia release new` rejects a SemVer-form id while `specs doctor` *requires* one.

**Resolution:** Renamed the release to `v0.1.18`; the descriptive label survives in the SPEC
objective and this closure. The `release new` vs `doctor` naming contradiction is filed as the
workspace bug `release-new-rejects-semver-but-doctor-requires-it` (carried forward Open —
release-tooling).

**Memory updates:** none — naming is a release-lifecycle artifact, not product state.

### pre-existing-pycache-hygiene-flake-fixed

**Description:** A pre-existing public-source hygiene flake (bug
`public-source-hygiene-flaky-pycache-pollution`) intermittently polluted the source tree with
`__pycache__` during the stage/install/doctor cycle, occasionally flaking the public-privacy
and hygiene checks. It surfaced again while running this release's projection gates.

**Resolution:** Fixed within the release; `dadaia public doctor` is stable at `[ok]
public-privacy`. Bug `public-source-hygiene-flaky-pycache-pollution` → Closed.

**Memory updates:** none — internal tooling hygiene, no product-state change.

### code-review-catalog-docstring-nit-fixed

**Description:** code-reviewer returned APPROVE-WITH-NITS, flagging a stale/inaccurate
docstring on the catalog-generation surface (the `dadaia memory catalog generate` index.md
emission added in T-PIO-10).

**Resolution:** Docstring corrected in the review-fix commit `f5f22c7`.

**Memory updates:** none — code docstring, not memory.

## Memory updates

- `specs/memory/architecture.md` — F1/D-1/D-2: added a "Two-layer agentic model" subsection
  (Layer 1 entry harness vs Layer 2 worker harness behind `AgentRuntimePort`; named the three
  transports SDK / CLI-headless / RPC and the five `AgentRuntimeKind`s); scoped the existing
  parity table to **Layer-1 entry-harness enforcement** + added a PI row; added a **Layer-2
  worker-runtime posture** table (FAKE / CODEX_EXEC / CLAUDE_SDK / OPENCODE_RUN / PI_HEADLESS,
  with only CLAUDE_SDK carrying a real Ring-1 boundary); rewrote the "três runtimes" injection
  framing to "três runtimes de entrada (Layer 1)"; added `.pi/` (target `pi`) to the asset-chain
  projection inventory. `infrastructure/pi_runtime.py` and the `PI_HEADLESS` factory branch were
  already in the inventory (pi-fourth-harness-v1) — confirmed.
- `specs/memory/product/philosophy/product-vision.md` — F2: added a "Two-layer agentic model
  (summary)" subsection; updated the seven-element list (item 5) and design pillar 1 to name PI
  as the fourth entry harness and the four worker harnesses. Operator confirmed PI is an
  officially supported fourth harness.
- `specs/memory/product/platform/multi-platform-parity.md` — F3/G-2: added a "Two-layer scope:
  projection-parity vs worker-runtime parity" subsection distinguishing Layer-1 projection
  parity (`.X/` trees incl. `.pi/`) from Layer-2 worker-runtime parity (no projection tree); added
  the `.pi/` post-trust-executable surface note; tldr/summary scope unchanged.
- `specs/memory/product/agents/harness-primitives.md` — F4: "all 15 default agents" → "all 9 core
  agents"; added a two-layer/4-harness orientation paragraph.
- `token_estimate` frontmatter refresh (F5): `tech-stack.md` (1200→1800),
  `product/sdd/lifecycle-foundation.md` (760→1500), `product/platform/multi-platform-parity.md`
  (606→1300), `product/philosophy/spec-context-project.md` (700→885); plus the atoms edited in
  this release: `architecture.md` (7000→7600), `product-vision.md` (950→1080),
  `harness-primitives.md` (495→620). LINT-1 token-estimate-drift WARNs cleared for the audit-flagged
  four.
- `specs/memory/product/index.md` — regenerated by the coordinator via the fixed `dadaia memory
  catalog generate` (T-PIO-11); the stale lifecycle-foundation row corrected. NOT hand-edited by
  product-engineer.
- `specs/memory/product/catalog.json` — NOT hand-edited; the coordinator regenerates it after
  these atom edits. No feature atom added or removed (the catalog set is unchanged; PI remains a
  value of the existing `lifecycle-foundation` / `multi-platform-parity` surfaces).
- `specs/memory/tech-stack.md` — no body change beyond `token_estimate` (PI runtime already
  documented by pi-fourth-harness-v1).
- `specs/memory/quality-assurance.md` — no change: release did not alter test architecture.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/memory-catalog-cli-skips-index-md.md` | bug | `Closed` | Fixed in T-PIO-10 (`dadaia memory catalog generate` now emits `index.md`), commit `97cd5f6`; index.md regenerated T-PIO-11. |
| `specs/bugs/public-source-hygiene-flaky-pycache-pollution.md` | bug | `Closed` | Fixed within release; `[ok] public-privacy` stable. See Drifts → pre-existing-pycache-hygiene-flake-fixed. |
| `specs/bugs/release-new-rejects-semver-but-doctor-requires-it.md` | bug | `Open` (carried forward) | Release-tooling contradiction surfaced by the rename (Drifts → release-renamed-…); not in this release's scope. Left Open for PM re-curation. |
| `specs/backlog/pi-agent-fourth-harness.md` | backlog (EPIC) | `PARTIALLY CONSUMED — v0.1.18` | WS-PI-3 (`.pi/` first-layer projection) + WS-PI-5 (deprecation pointer) delivered; WS-PI-1/2 delivered in pi-fourth-harness-v1; memory + constitution two-layer documentation done. WS-PI-4 (Ring-1), WS-PI-6 (telemetry), RPC/SDK transports, and the formal `dadaia-pi-workspace` DEAD-mark deferred — left in place for PM re-curation (do not close the EPIC). |

Never-delete law honored: no bug or backlog file deleted; each carries a terminal token + reason.

## Backlog returns

The EPIC `specs/backlog/pi-agent-fourth-harness.md` is **PARTIALLY CONSUMED**; the following
remaining scope is deferred and left in the EPIC for PM re-curation:

- `backlog/candidates.md` ← WS-PI-4: Ring-1 `.pi/extensions/dadaia-sdd-gate.ts` pre-disk
  `tool_call` gate (post-trust; High risk; Ring-2 + chokepoints remain the backstop).
- `backlog/candidates.md` ← WS-PI-6: telemetry adapter + academy doc — only with a real local
  PI session source (anti-slop: no placeholder telemetry).
- `backlog/candidates.md` ← `pi --mode rpc` transport + the TypeScript SDK in-process path —
  deferred behind a concrete future need (engine is one-shot-per-step).
- `backlog/candidates.md` ← formal `dadaia context` DEAD-marking of `dadaia-pi-workspace`
  (deprecation README already added in T-PIO-17; the DEAD-mark touches another repo and has
  known `dead()` bugs — operator/closure follow-up, never delete the repo).

## Archive decision

**MOVE** — the release directory will be moved to `specs/_archive/releases/v0.1.18/` via
`git mv`, and `specs/releases/ACTIVE.md` reset to `release: none` / `phase: none`. The
**coordinator executes the `git mv` and the `ACTIVE.md` reset** (and re-runs `dadaia memory
catalog generate` to regenerate `product/index.md` + `catalog.json`) after this closure;
product-engineer does not run git or archive. The `dadaia-pi-workspace` `dadaia context`
DEAD-mark is recorded as an operator follow-up.
