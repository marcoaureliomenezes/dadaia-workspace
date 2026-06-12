# Closure: Release — v0.1.13

> **Status:** Aprovado
> **Release ID:** v0.1.13
> **Owner:** product-engineer
> **Closed:** 2026-06-12

## Summary

v0.1.13 makes the Codex runtime surface of dadaia-workspace honest, teachable, and
verifiable. The release shipped in two segments. **alpha-1** delivered the full English
`07_codex` Academy course, refined Codex harness skills, documented `prefix_rule(...)`
command policy, read-only sandbox boundaries for evidence-only reviewers, explicit
dispatcher/subagent honesty, and a panel Academy tab that finally browses the shipped
knowledge_basis modules and lessons. **alpha-2** (Codex Runtime Fidelity residuals)
resolved every UNVERIFIED cell of the fidelity audit against a live Codex binary
(codex-cli 0.139.0) via a scripted, repeatable harness, fixed the four projection-tail
bugs, and replaced the Claude-centric MODEL_MAP prose substitution with registry-derived
Codex-native model tiering (model id × `model_reasoning_effort`).

The single most load-bearing truth this release established: **Codex executes command
hooks only in interactive sessions — `codex exec` (headless) never fires them.** The
workspace now documents Codex deterministic enforcement as interactive-only and the
Codex automation path as discipline-only, instead of claiming enforcement it does not
have. The upstream defect remains Open as `codex-exec-hooks-do-not-fire-headless`.

## Tasks completed

12/12 tasks `[x]` DONE across the two segments. Per-task commits live on the feature
branch history aggregated in PR #55 (stacked on #54 → #53; merge operator-held).

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-013-01 | Rewrite the English Codex Academy module (07_codex) | PR #55 |
| T-013-02 | Refine Codex harness skills (ai-harness-codex, harness-primitives) | PR #55 |
| T-013-03 | Fix generated Codex Rules shape (`prefix_rule(...)`, no `command_allowed`) | PR #55 |
| T-013-04 | Codex custom-agent sandbox boundaries (evidence-only reviewers read-only) | PR #55 |
| T-013-05 | Make Codex dispatcher/subagent behavior explicit (no auto-execution claims) | PR #55 |
| T-013-07 | Panel Academy tab browses knowledge_basis modules/lessons (traversal-guarded route) | PR #55 |
| T-013-06 | Project and verify Codex parity (public doctor 0, module 7 visible) | PR #55 |
| T-013-08 | WS-CDX-VERIFY: live Codex contract harness + fact recording (F-1/F-6/F-8 resolved) | PR #55 |
| T-013-09 | Description-field transform + D-CX-4 tool-name patterns | PR #55 |
| T-013-10 | Venv-path prefix rules + real-form `match=` proofs | PR #55 |
| T-013-11 | Delete/invert the stale T-35 roster lint | PR #55 |
| T-013-12 | Codex-native model strategy (per-runtime tier rendering, collapse guard) | PR #55 |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full test suite green | `pytest` | `2952 passed` (coordinator-reported, pre-closure run) |
| Specs/public doctor clean | `.dadaia/.venv/bin/dadaia specs doctor` / `dadaia public doctor` | exit 0 (coordinator-reported, pre-closure run) |
| CI on PR #55 | GitHub Actions checks | 16/18 green, 0 failures (2 pending) at closure time; coordinator keeps the watch per watch-ci-until-green |
| rc ship gate — qa-engineer APPROVE | handoff review | `.dadaia/handoff/dadaia-workspace/2026-06-12T030500Z-qa-engineer-v0113-rc-ship-gate.handoff.json` |
| rc ship gate — security-reviewer APPROVE | handoff review | `.dadaia/handoff/dadaia-workspace/2026-06-12T002500Z-security-reviewer-v0113-ship-gate.handoff.json` |
| rc ship gate — code-reviewer APPROVE | handoff review | `.dadaia/handoff/dadaia-workspace/2026-06-11T235900Z-code-reviewer-v0113-rc-ship-gate.handoff.json` |
| Live Codex contract facts (P1..P5 + headless-no-hooks) | `DADAIA_CODEX_LIVE=1 pytest tests/integration/codex_live/` (opt-in) | `tests/integration/codex_live/` harness + facts recorded in bug `codex-exec-hooks-do-not-fire-headless` and `ai-harness-codex` skill |
| Venv-form rules projected | inspect `.codex/rules/dadaia-command-policy.rules` | `prefix_rule(pattern = [".dadaia/.venv/bin/dadaia", ...])` with real-form `match=` examples present in projected file |
| Academy tab browses knowledge_basis | panel live review | bug `academy-tab-cannot-browse-knowledge-basis-modules` Resolution note (verified live in browser + unit suites green) |
| alpha-1 / alpha-2 segment gates | qa-engineer segment reviews | `.dadaia/handoff/dadaia-workspace/2026-06-11T062709Z-qa-engineer-v0113-alpha1-review.handoff.json`; `.dadaia/handoff/dadaia-workspace/2026-06-12T020346Z-qa-engineer-v0113-alpha2-review.handoff.json` |

## Drifts

### pm-codex-reasoning-effort-registry-derived

**Description:** `project-manager`'s Codex projection changed `model_reasoning_effort`
high → medium. Flagged INFO by code-reviewer at the ship gate.

**Resolution:** Intended behavior — the value is now registry-derived
(`codex_tier_views()`: dispatch tier → medium effort), not hand-set. No spec change
needed.

**Memory updates:** covered by `specs/memory/product/platform/multi-platform-parity.md`
and `specs/memory/tech-stack.md` (registry-derived tiering).

### api-academy-acceptance-superseded

**Description:** The original SPEC acceptance wired `/api/academy` to the
CourseStore-based course list. T-013-07 superseded it: the API now serves the
knowledge_basis module catalog directly (qa MINOR-2).

**Resolution:** Intended behavior — the CourseStore view could never show the shipped
courses (bug `academy-tab-cannot-browse-knowledge-basis-modules`); the SPEC's Panel
acceptance is satisfied by the stronger browsing surface. CLI copy-from-template
management is unchanged.

**Memory updates:** `specs/memory/product/distribution/academy.md`,
`specs/memory/product/panel/panel.md`.

### e2e-specs-reconciled-post-trio

**Description:** Playwright e2e specs were reconciled after the trio reviews to match
the operator-approved kanban-v2/agent-card panel redesign (commit `6fb057b`).

**Resolution:** Intended behavior — the redesign was operator-approved live; the e2e
suite was updated to assert the approved UI, not reverted. The trio verdicts predate
the reconcile commit; CI on PR #55 covers the final state.

**Memory updates:** none in this release (the broader panel redesign/no-auth atom
refresh belongs to the v0.1.12 reconciliation the operator already flagged).

### panel-bugs-fixed-outside-folded-table

**Description:** Two panel bugs (`panel-cookie-auth-theater-browser-apis-unreachable`,
`panel-memory-view-unreachable-and-incomplete`) were fixed by live-review commits
(`9d02f7f`, `ab859c7`) during this release window without being in the folded bug
table (qa MINOR-1).

**Resolution:** Fixes verified present in the working tree at closure (panel auth
removed in favor of Host-header allowlist; memory chips now include Constitution and
Quality; `constitution.md` served via explicit single-file allowlist in
`views/memory.py`). Both bugs dispositioned Closed with `resolved_in: v0.1.13` and a
note that they were solved outside the folded table.

**Memory updates:** none beyond the panel Academy edits — full panel-auth atom rewrite
deferred to the v0.1.12 reconciliation.

### codex-config-inert-keys-still-emitted

**Description:** WS-CDX-VERIFY proved `approved_commands` and `[skills] paths` are
invalid (inert) Codex config keys, yet the projected `.codex/config.toml` still emits
them.

**Resolution:** Removal is part of the deferred WS-CDX-HYGIENE workstream
(operator-decided), tracked in `specs/backlog/codex-runtime-fidelity.md`. Memory now
documents the keys as live-verified inert so no consumer relies on them.

**Memory updates:** `specs/memory/product/platform/multi-platform-parity.md`,
`specs/memory/product/agents/ai-harness-codex.md`.

## Memory updates

- `specs/memory/product/agents/ai-harness-codex.md` — live-verified Codex contract
  facts (interactive-only hooks, block envelope, anchored matcher, shell-exec,
  invalid config keys, `config_file` real, codex_tier_views tiering, codex_live
  harness); knowledge_basis 07_codex as authoring source.
- `specs/memory/product/platform/multi-platform-parity.md` — honest Codex projection
  contract: venv-form `prefix_rule` policy, read-only reviewers, description
  transform, registry-derived tiering, interactive-only hook execution, inert config
  keys flagged.
- `specs/memory/product/sdd/sdd-gate-v3.md` — Codex hook-injection row now carries the
  interactive-only enforcement boundary (headless `codex exec` = discipline-only).
- `specs/memory/product/distribution/academy.md` — Academy primary surface is direct
  knowledge_basis browsing in the panel (catalog API + traversal-guarded lesson
  route); 07_codex full English course; stale "modules not created" note removed.
- `specs/memory/product/panel/panel.md` — Academy tab flow and route table updated
  (`GET /api/academy` catalog + `GET /academy/<module>/<lesson>`).
- `specs/memory/tech-stack.md` — Codex agent-runtime row: D-CX-1..8, registry-derived
  tiering, venv-form rules, interactive-only hooks, codex_live opt-in harness.
- `specs/memory/architecture.md` — no change: the release altered projection content
  and panel views inside existing layers/modules; no layer boundary or dependency
  contract moved.
- `specs/memory/product/catalog.json` — NOT regenerated in this session (generated
  artifact; regeneration command requires shell). Coordinator: regenerate the catalog
  so updated frontmatter summaries (academy, multi-platform-parity, ai-harness-codex)
  are reflected.

## Dispositions

| File | Kind | Terminal status | Evidence |
|------|------|-----------------|----------|
| `specs/bugs/codex-rules-generated-with-undocumented-command-allowed.md` | bug | `Closed` | T-013-03; projected `.codex/rules/dadaia-command-policy.rules` uses `prefix_rule(...)` |
| `specs/bugs/codex-reviewer-agents-projected-workspace-write.md` | bug | `Closed` | T-013-04; reviewers project `sandbox_mode = "read-only"` |
| `specs/bugs/academy-tab-cannot-browse-knowledge-basis-modules.md` | bug | `Closed` | T-013-07; resolution note in bug file (live-verified in browser) |
| `specs/bugs/codex-agent-description-claude-ism-leak.md` | bug | `Closed` | T-013-09; description runs body replacement table, D-CX-4 tool-name lint |
| `specs/bugs/codex-rules-dadaia-prefix-never-matches-venv-invocation.md` | bug | `Closed` | T-013-10; venv-form patterns with real-form `match=` proofs |
| `specs/bugs/stale-legacy-software-engineer-lint-inverts-roster.md` | bug | `Closed` | T-013-11; lint no longer flags canonical `software-engineer` |
| `specs/bugs/codex-personas-claude-model-tiering-leak.md` | bug | `Closed` | T-013-12; `codex_tier_views()` per-runtime rendering + collapse guard |
| `specs/bugs/panel-cookie-auth-theater-browser-apis-unreachable.md` | bug | `Closed` | commits `9d02f7f`/`ab859c7` (outside folded table); no-auth + Host-guard verified in `features/panel/handler.py` |
| `specs/bugs/panel-memory-view-unreachable-and-incomplete.md` | bug | `Closed` | commits `9d02f7f`/`ab859c7` (outside folded table); constitution/quality chips + allowlist verified in `views/index.py`/`views/memory.py` |
| `specs/backlog/codex-runtime-fidelity.md` | backlog | `CONSUMED — v0.1.13 (WS-CDX-VERIFY/BUGFIX/MODEL); WS-CDX-PROTOCOL + WS-CDX-HYGIENE remain CANDIDATE` | SPEC amendment alpha-2 (operator grill decisions) |

Bugs explicitly left **Open** (not solved by this release):

- `codex-exec-hooks-do-not-fire-headless` — upstream Codex defect (codex-cli 0.139.0);
  this release made the workspace docs honest about it, but the headless path still
  fires no hooks.
- `sdd-gate-apply-patch-multi-file-first-header-only` — gate parsing gap; out of scope.
- `bug-guardrail-template-omits-required-session-id` — guardrail template defect; out
  of scope.
- `context-dead-nonwritable-guard-rejects-standard-git-objects` and
  `context-release-leaves-lease-heartbeat-renewing` — filed from the concurrent
  session; not picked into this release.
- `agents-md-instructs-html-report-validation-unsupported` — docs/CLI contract gap;
  out of scope.
- All other pre-existing Open bugs in `specs/bugs/` were untouched by this release and
  retain their prior status.

## Backlog returns

- `specs/backlog/codex-runtime-fidelity.md` ← WS-CDX-PROTOCOL (F-2/F-11 rule-corpus
  visibility on Codex) and WS-CDX-HYGIENE (F-3/F-7/F-9/F-12 — trust surfacing,
  adapter-skill rework, `.codex/workflows/` decision, inert-config-key removal, doc
  cleanup) remain CANDIDATE by operator decision.

## Archive decision

**MOVE** — release directory moves to `specs/_archive/releases/v0.1.13/` via
`git mv specs/releases/v0.1.13 specs/_archive/releases/v0.1.13` (Bash path — file
tools are gate-blocked on `_archive/`). ACTIVE.md is freed to `release: none`.
