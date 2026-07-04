# Backlog candidates

Curated index of surviving backlog items. Rebuilt 2026-07-02 after the operator-ordered
backlog sanitization + architectural deep review (post-v0.1.48); **pruned 2026-07-04** after
R1–R11 (v0.1.49–v0.1.59) shipped. This index lists **only** surviving open candidates —
consumed, superseded, and stale entries were removed per removal-on-release and the
never-keep-the-past law. R10 (v0.1.58) consumed `harness-isolation-profiles` +
`consumer-agents-md-fanout-redesign` (both anchors survive → archived at CLOSURE to
`specs/_archive/v0.1.58/consumed-backlog/`) and returned four items (indexed below). R11
(v0.1.59) consumed `panel-ux-overhaul` (anchor survives → archived at CLOSURE to
`specs/_archive/v0.1.59/consumed-backlog/`) and returned one item
(`response-guard-chip-presence-hardening`, indexed below).

Architecture baseline: two-layer model, Layer-1 entry harnesses `{claude, codex, pi}`,
Layer-2 = `dadaia lifecycle` Python workflow bodies driving pi/codex workers.

**Open-bug debt (outranks plain backlog at pick):** none — the last open bug
(`bugs-append-bound-session-falls-through-to-cwd-specs`) was resolved by R2/v0.1.50.

---

## Release sequence (grilled 2026-07-02)

Operator-approved conversion order — every surviving entry and every open bug placed
exactly once. Grill decisions: (1) the backlog becomes git-tracked repository truth
(R1); (2) panel plumbing runs EARLY (R4); (3) panel-ux precedes plugin packs — the
recorded `plugin-scope` deviation stands. Suggested ids v0.1.49–v0.1.60; actual ids
are assigned at each `release define`, and each release still runs its own mandatory
grill on the picked set before SPEC.

| # | Release theme | Consumes (backlog / bugs) | Why this position |
|---|---|---|---|
| R1 | **SHIPPED — v0.1.49** (merged `3743cb06`, PR #87, 2026-07-02) | bugs `backlog-gitignored-governance-vacuous` + `backlog-subject-registry-invariant-content-scan`; `memory-heading-allowlist-extension` (all consumed) | Fix the release machine first: git-tracked backlog makes the BL-* chokepoint/CI real; fail-closed registry stops docstring/test junk anchors. |
| R2 | **SHIPPED — v0.1.50** (merged `7b198d49`, PR #89, 2026-07-02) | `lease-kernel-identity-hardening`; `context-dead-exit-path`; bug `bugs-append-bound-session-falls-through-to-cwd-specs` (all consumed/resolved) | The single deterministic lock, session attribution, and the context exit path are the safety spine; removes the reproduced self-block pain. |
| R3 | **SHIPPED — v0.1.51** (merged `5329cd96`, PR #91, 2026-07-02) | `e2e-journey-coverage-and-test-canon` (consumed) | Safety net BEFORE the refactor chain; the master lifecycle E2E can only assert correct bind attribution after R2. Residue-test disposition aligns the suite with the no-slop law. |
| R4 | **SHIPPED — v0.1.52** (merged `fd23ea5e`, PR #93, 2026-07-03) | `panel-sessions-cost-dashboard-only` → `panel-runtime-reliability` (both consumed; archived at ship — dead-anchor BL-SCHEMA) | Operator-elected, fully independent; kills the SQLite corruption bug; reliability lands on the post-removal route surface; every later release runs a smaller suite. |
| R5 | **SHIPPED — v0.1.53** (merged `d3f46360`, PR #95, 2026-07-03) | `legacy-surface-retirement`; `hygiene-and-dead-code-cleanup`; `centralize-release-semver-canon`; `telemetry-tier2-chmod-unguarded-on-windows` (all consumed; archived at ship — dead-anchor BL-SCHEMA) | Delete before refactoring: shrinks the surface R6–R9 must restructure and the import contracts must cover. |
| R6 | **SHIPPED — v0.1.54** (merged `aeaa3c66`, PR #97, 2026-07-03) | `import-boundary-enforcement`; `features-import-infrastructure-direct-debt`; `pid-probe-seam-consolidation` (all consumed; archived at ship — dead-anchor BL-SCHEMA) | Contracts green + CI-wired + `workflows ↔ lifecycle` cycle broken; silent erosion stops here so all later structure lands under enforcement. |
| R7 | **SHIPPED — v0.1.55** (merged `a1fc29f4`, PR #99, 2026-07-03) | `architecture-uml-decomposition` + bugs `bugs-append-ignores-persisted-bind`, `backlog-new-stub-readme-lag-intents-schema` (all consumed/resolved; archived at SHIP — dead-anchor BL-SCHEMA) | SpecsDoctor/api.py splits + reports_* merge landed under the now-enforced contracts; shipped the committed UML assets + the two open-bug fixes. |
| R8 | **SHIPPED — v0.1.56** (merged `3a02f758`, PR #101, 2026-07-04) | `lifecycle-verb-governance-uniformity` (consumed; archived at CLOSURE — both anchors survive) | Resolver on EVERY run verb + audit/research/bug_report invocable + implement/review loop fixed (digest + runner gate + CLI caller) + TRANSITIONS reconciliation. Final release of the R6→R8 mandate. |
| R9 | **SHIPPED — v0.1.57** (merged `8bab315a`, PR #104, 2026-07-04) | `context-injection-role-phase-canon`; `fragment-workflow-base-dedup`; `hard-remove-model-flag-across-run-verbs` (all consumed; the two injection-canon anchors survive → archived at CLOSURE; the `--model` dead anchor archived at SHIP — BL-SCHEMA) | The dedup base created the ONE prompt-assembly seam; role→atom map + phase threading + coherence doctor landed there; `--model` hard-removed across the 12 run verbs; `TransitionDecision.advanced` fixed the illegal-transition bug. First release of the R9→R12 mandate. |
| R10 | **SHIPPED — v0.1.58** (merged `b0bd8217`, PR #106, 2026-07-04) | `harness-isolation-profiles`; `consumer-agents-md-fanout-redesign` (both consumed; both anchors survive → archived at CLOSURE) | `init --harness` profiles + typed `core/harness_registry.py` (4 L1 + 3 L2 sites, contract-locked to `harness_models.harnesses()`) + profile-aware install/doctor (absent ⇒ all-four) + consumer AGENTS.md fan-out redesign (spec_contexts.json detection, `[updated]` restore, doctor flagging). First projection/install release after the structural chain; the workflow-spawn auto-default deferred (FR6). |
| R11 | **SHIPPED — v0.1.59** (merged `e6634996`, PR #108, 2026-07-04) | `panel-ux-overhaul` (consumed; anchor survives → archived at CLOSURE) | Visual redesign on the stabilized post-R4 panel, under the recorded `plugin-scope` deviation (operator 2026-07-02). Token-driven design system + uniformly styled controls + single-line header/control rows + `<header>` IA density + theme polish + two-category dead-CSS purge; behavior-locked golden-first (DOM-contract lock never re-baselined + api-golden zero-diff + CSP hashes frozen). Returned one QA LOW item. |
| R12 | Capability tail | `plugin-packs-and-install-command`; `model-tier-efficiency-and-fast-tier-utilization` | Pure new capability, zero debt: packs + install command, then Layer-1 fast-tier assignments. |

---

## HIGH

### `layer1-selfpull-handoff-audit-line` — Layer-1 self-pull handoff audit line *(2026-07-04)*
Returned at v0.1.57 closure (FR4 Ruling A). R9 ratified Layer-1 **self-pull** for
constitution/architecture/quality-assurance (`ctx_inject.py` byte-identical) and made
**Layer-2** grounding mechanically checkable (role→atom map refs + `FRAG-COH-4`). This
entry tracks the deferred **Layer-1** verifiability: a handoff-v1.1 schema audit line
(+ validator) proving the self-pull atoms were actually read, turning the L1 discipline
into a checkable contract. Anchored at `hooks/ctx_inject.py#main` + the handoff schema
surface. Override: bounded phase-aware L1 digests reopen FR4.

---

## MEDIUM

### `workflow-spawn-entry-harness-autodefault` — Workflow-spawn entry-harness auto-default *(2026-07-04)*
Returned at v0.1.58 closure (FR6 / Ruling F). Auto-default the Layer-2 worker harness from
the entry harness (enter codex ⇒ `--harness codex`, enter pi ⇒ `--harness pi`; explicit flag
wins). Deferred because PI has no session env var (`core/session_env.py` carries only
`CLAUDE_CODE_SESSION_ID` + `CODEX_SESSION_ID`) and claude is L1-only. Override: codex-only
best-effort default now.

### `golden-platform-normalization-layer` — Consolidated golden platform-normalization layer *(2026-07-04)*
Returned at v0.1.58 closure (three-round CI saga). Consolidate the per-test golden-normalization
helpers into ONE shared platform-invariance layer (host-state canonicalization + sorted-multiset
report-list locks + OS-phrase canonicalization) so a byte-golden is cross-platform-stable by
construction. Anchored at the v0.1.58 golden helpers in `test_install_target_goldens.py` + the
v0.1.55 golden-authoring law.

### `plugin-packs-and-install-command` — Plugin packs + `dadaia plugin install`
Distribute frontend-design + devops packs; referenced by the `plugin-scope` rule.
(File recreated 2026-07-02 — the entry existed only as an index line.)

### `model-tier-efficiency-and-fast-tier-utilization` — Layer-1 model-tier efficiency (P2)
Fast-tier assignments for mechanical sub-tasks + recurring efficiency-audit trigger.

---

## LOW

### `response-guard-chip-presence-hardening` — Response-guard e2e chip-presence assertion (QA) *(2026-07-04)*
Returned at v0.1.59 closure (W5 AC-9(e) finding). `tests/e2e/panel/response-guard.spec.ts:76-77`
null-guards a missing `.memory-chip` (`if (firstChip) {…}`) and degrades gracefully, so a dropped
chip is caught only by the FR1 DOM-contract unit lock, not the browser tour. Assert chip presence
(`expect(firstChip).not.toBeNull()`) as defence-in-depth behind the DOM contract. Anchored at
`tests/e2e/panel/response-guard.spec.ts`.

### `fanout-repo-slug-containment` — Consumer fan-out repo-slug containment guard *(2026-07-04)*
Returned at v0.1.58 closure (FR4 hardening, security). The redesigned fan-out writes the
workspace-law pair to `repos/<repo_slug>/` derived from `spec_contexts.json`; assert each
resolved dir is `is_relative_to(repos/)` or reject a multi-component / traversal slug. Anchored
at `workspace_guardrail.py#_install_guardrail_pair`. Override: `REJECTED — trusted-input` if
`spec_contexts.json` is deemed fully first-party.

### `selfrepo-agents-md-doubled-header` — Self-repo AGENTS.md doubled header (doc-pass) *(2026-07-04)*
Returned at v0.1.58 closure (doc-pass). `repos/dadaia-workspace/AGENTS.md` carries a doubled
workspace-law header (v0.1.47 hand-sync artifact); the retained `_is_self_repo` fan-out skip
means it is never auto-rewritten, so it needs a sanctioned hand-sync to collapse to one header.
Anchored at `workspace_guardrail.py#_is_self_repo` + the self-repo AGENTS.md.

