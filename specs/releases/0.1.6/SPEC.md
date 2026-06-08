# SPEC — Release 0.1.6 "Consolidation"

**Status:** Aprovado
**Release ID:** 0.1.6
**Owner:** product-engineer
**Branch:** `feature/0.1.6`
**Date:** 2026-06-07

---

## 1. Objective

Release 0.1.6 is a large **consolidation** of the published 0.1.x line (PyPI = main = 0.1.5).
It folds every open bug and every live backlog item — spanning panel, Codex harness, SDD
lifecycle, specs evolution, agent surface, and workspace sanitization — into a single release.

The unpushed v0.2.x history (branches `feature/0.2.0`, `feature/0.2.1`, `feature/0.2.2`) is
**abandoned**. Its live design content — state-model redesign, agent roster reduction, Codex
compatibility, constitution canonization, memory-tree restructure — is carried forward here as
part of the 0.1.6 pick.

### Version semantics (record explicitly)

Folding framework rewrites, a new command surface (`dadaia specs upgrade`), a roster reduction
(15 → 9 agents), a full Codex compatibility program, and the complete open bug set under a
`0.1.6` label on the 0.1.x line is a **large CONSOLIDATION**, not a semver patch in the
conventional sense. The 0.1.6 label is the operator's explicit choice: this release continues
the published 0.1.x train and matures through `alpha-N → rc-N` segments per release-governance
(ADR-1). Implementers and reviewers must treat the scope as equivalent to a MAJOR or MINOR bump
in engineering terms, even though the version string is a PATCH increment.

---

## 2. Grill — completed

The mandatory `dadaia-grill-me` session was completed by the operator. All four open forks
from the pre-SPEC session are now resolved; see **§11 (Resolved Decisions)** for the full
record. No fork remains open. Status may advance.

---

## 3. Abandoned v0.2.x reconciliation

The locally-closed releases v0.2.0, v0.2.1, and v0.2.2 (all on abandoned branches, unpushed)
contain design content that is now re-adopted into 0.1.6. Their archived CLOSURE.md files are
historical; the SPEC/PLAN/TASKS that follow are the authoritative pick for 0.1.6. Where a v0.2.x
artifact claimed work was completed (e.g. v0.2.1 T-021-15 safe-preserve backup claim — see
WS-SPECS-EVOLUTION §3 drift), this release must either implement the claimed behavior or
explicitly correct the archived record per `FEAT-SPECS-EVOLUTION-200 §3`.

---

## 4. Product Deltas — six workstreams

### WS-PANEL — Panel fixes + UX overhaul

Seven panel bugs from the published 0.1.5 wheel, plus the operator-directed UX redesign.

**Operator-authorized plugin-scope deviation:** the `plugin-scope` rule would route HTML/CSS/JS
and UX/UI work to the `frontend-design` plugin (`frontend-engineer` / `design-specialist`). The
operator has authorized doing this work directly as library source edits
(`dadaia_workspace/features/panel/`) because there is no `dadaia plugin install frontend-design`
command in this CLI. This deviation is recorded here; it is not a silent violation.

**Cross-cutting gate (mandatory for all panel UI changes):** No panel or frontend change may ship
without deep-interaction e2e tests AND the global zero-tolerance 4xx/5xx-and-console-error guard
(E2E-GUARD-01/02) across a full tab tour plus key interactions. Label-deep assertions (`text
exists`) are insufficient. The CI `e2e-panel` job must seed the test workspace with a real spec
context so data-dependent paths run.

#### FR-P01 — Memory document viewer fixed (Critical)

Source: `specs/bugs/panel-memory-doc-links-broken-html.md`

The panel chip hrefs and iframe src currently use stale `.html` extensions; the memory route
serves `.md` files; every click 404s. Introduce a single canonical memory-URL builder used by
the chip generator, the memory-view wrapper iframe, and the wikilink renderer. All three call
sites must reference the builder — no independent URL encoding.

Acceptance:
- `GET /memory/dadaia-workspace/architecture.html` no longer 404s (redirect or canonical `.md`
  path is served).
- Clicking Architecture, Tech Stack, and Product chips each returns 200 with real body.
- A regression test clicks each chip and asserts iframe content is 200 + non-empty
  (E2E-SCP-03/04/05).
- Memory API contract test verifies the `/memory/` route responds correctly (E2E-SCP-06).
- Zero `panel-memory-doc-links-broken-html` class of failure in `dadaia specs doctor`.

#### FR-P02 — Theme switcher functional + visual redesign (High)

Source: `specs/bugs/panel-theme-switcher-broken-ugly.md`; `specs/backlog/panel-ux-overhaul.md`

Two scopes in one task:
(a) **Functional:** clicking the theme switcher applies and persists the selected theme
(`document.documentElement.dataset.theme` changes; localStorage persists across reload).
(b) **Visual/UX redesign:** the bottom theme control is "totally improved" per operator directive.

Acceptance:
- Theme selection applies immediately and persists across a panel reload.
- Deep-interaction e2e test: click control → option visible → theme dataset changes →
  persists across reload.
- Visual redesign is operator-reviewed before rc-N ship.

#### FR-P03 — Auth route unification (High)

Source: `specs/bugs/panel-handler-parallel-auth-registries.md`

Collapse `_BEARER_AUTH_ROUTE_NAMES`, `_BEARER_ONLY_ROUTES`, and `_SECOND_LOOP_AUTH_ROUTES`
into one declarative route struct `(pattern, name, auth_class)` where
`auth_class ∈ {PUBLIC, BEARER, BEARER_SECOND_LOOP, BEARER_TELEMETRY}`. The dispatch loop reads
`auth_class`. DELETE ordering is enforced structurally (own table or anchored test).

Acceptance:
- A unit test asserts every route has an explicit auth classification.
- A test proves DELETE route ordering is structurally correct (important-before-catch-all).
- No route can be added to `_RAW_ROUTES` without being classified.

#### FR-P04 — Workflow launcher extract to infrastructure layer (High)

Source: `specs/bugs/panel-subprocess-in-features-layer.md`

Define a `WorkflowLauncher` protocol in `core/protocols/`, implement it in `infrastructure/`
(the `Popen`), inject into `PanelService`. Persist running workflow state to a JSON file under
`.dadaia/states/` so restart does not lose state.

Acceptance:
- No `subprocess.Popen` or `os.kill` call inside `dadaia_workspace/features/` layer.
- Running workflow state survives a panel restart.
- Unit test covers the protocol + infrastructure adapter.

#### FR-P05 — Wikilink renderer parameterized by context slug (High)

Source: `specs/bugs/panel-wikilink-slug-hardcoded.md`

Parameterize `build_renderer(slug)` and close over the active slug in the wikilink plugin;
cache renderers per slug. All wikilink hrefs route through the canonical memory-URL builder
(FR-P01).

Acceptance:
- A wikilink `[[other-atom]]` in a non-dadaia-workspace context resolves to the correct context,
  not always `/memory-view/dadaia-workspace/`.
- Renderer cache is keyed by slug.

#### FR-P06 — E2e deep-interaction suite + global deploy gate (High)

Source: `specs/bugs/panel-e2e-shallow-coverage-no-deploy-gate.md`

Three mandatory changes:
1. Deep-interaction regression tests for each memory chip (FR-P01, E2E-SCP-03/04/05/06).
2. Global zero-tolerance guard: `page.on('response', ...)` + `page.on('console', ...)` fail
   the test on any 4xx/5xx or console error during a full tab tour + key interactions
   (E2E-GUARD-01/02).
3. CI panel workspace seeded with a real spec context (memory atoms) so data-dependent paths run.

Acceptance:
- E2E-GUARD-01: any 4xx/5xx during tab tour fails the test run.
- E2E-GUARD-02: any console error during tab tour fails the test run.
- CI `e2e-panel` job bootstraps a workspace with at least one alive spec context.
- A broken iframe (404-ing memory chip) now fails CI.

#### FR-P07 — Token file atomic restricted-mode create (Medium)

Source: `specs/bugs/panel-token-file-chmod-toctou.md`

Replace `path.write_text(token); os.chmod(path, 0o600)` with atomic
`fd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, 0o600); os.write(fd, ...)`.

Acceptance:
- No window between file creation and permission set.
- `O_EXCL` prevents double-write race.
- Unit test verifies the resulting file has mode `0o600`.

#### FR-P08 — Tab consolidation (Agents + Workflows + Kanban → one tab) (Medium)

Source: `specs/backlog/panel-ux-overhaul.md`

Merge the three tabs into a single tab that shows all three sections with smaller cards.
Sessions tab is untouched. This is library source edits to `views/agents.py`,
`views/workflows.py`, `views/kanban.py`, and their associated JS/CSS.

Acceptance:
- Single consolidated tab shows Agents, Workflows, and Kanban sections together.
- The three previously-separate top-level tabs are gone.
- Sessions tab is functionally and visually unchanged.
- Deep-interaction e2e test clicks through the consolidated tab and passes E2E-GUARD-01/02.

---

### WS-CODEX — Codex harness fixes + full compatibility

Two bugs and two backlog items targeting the Codex harness.

#### FR-C01 — Context injection idempotence (Critical)

Source: `specs/bugs/repeated-visible-userpromptsubmit-memory-injection.md`;
`specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md` WS-1/WS-2

Fix `ctx-inject.sh` so the full workspace memory bootstrap happens exactly once per logical
Codex session, not once per hook invocation (which is once per prompt).

The root cause: `ctx-inject.sh` falls back to `$$` (hook subprocess PID) when neither
`CLAUDE_CODE_SESSION_ID` nor `OPENCODE_SESSION_ID` is set. In Codex, each hook invocation runs
in a new shell, so `$$` is unique per prompt — the sentinel check is never stable.

The already-fired path must emit empty/no-op Codex JSON or nothing, not `[dadaia-workspace]`
plus the full memory block.

Acceptance (forks resolved — see §11 Resolved Decisions):
- Full memory bootstrap moves to a Codex `SessionStart` hook (matcher `startup|resume`);
  idempotence key is the `session_id` field from the JSON stdin Codex passes on startup.
- Subagents inherit the parent `session_id`; the sentinel check is stable across all
  hook invocations in one logical session.
- The already-fired path emits nothing and exits 0 (doc-blessed no-op).
- The per-prompt `[dadaia-workspace]` breadcrumb is dropped entirely from the
  `UserPromptSubmit` path — no minimal payload; SessionStart carries context once.
- `ctx-inject.sh` no longer uses raw `$$` as the Codex idempotence key.
- Generator change in `public_assets.py` `_codex_hooks` (~line 2350) wires the
  `SessionStart` hook (matcher `startup|resume`) and reads stdin to parse `session_id`.
- Tests assert bootstrap markers appear at most once per session for Codex.

#### FR-C02 — Deterministic Codex workflow preflight (High)

Source: `specs/bugs/codex-workflow-dispatch-not-deterministically-enforced.md`;
`specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md` WS-6

Add a deterministic preflight mechanism so Codex role ownership and subagent fan-out are
enforced by structure, not model memory. Resolution (FORK-4a + FORK-4b): combination approach.

- `PreToolUse` hook enforces ownership/SDD-gate deterministically (blocked = hard block).
- `SessionStart` `additionalContext` routes: active context + owning-role map + "discover
  subagent tooling before orchestration work" instruction.
- Codex `.rules` govern commands only.
- AGENTS.md serves the advisory layer.

PM-only backlog writes are enforced by the existing `sdd-spec-gate.sh` via two mechanisms:
(1) injecting `CODEX_AGENT_PERSONA` for known custom agents via `codex_agent_dispatcher.py`;
(2) fail-safe-blocking writes to `specs/backlog/**` (and other owner-only paths) when the
persona is unresolved/empty — today these fall through to allowed, which is the bug.

Accepted constraint: specialist fan-out is NOT hard-enforceable in Codex (it never
auto-spawns). Fan-out is a strongly-prompted expectation, not a runtime guarantee.

Acceptance (FORK-4 resolved):
- `PreToolUse` hook blocks writes to `specs/backlog/**` when `CODEX_AGENT_PERSONA` is
  unresolved or is not `project-manager`; a clear unblock message is printed.
- Writes to owner-only paths (backlog, memory in non-CLOSURE phase, constitution) are
  fail-safe-blocked when persona is empty/unresolved.
- `SessionStart` `additionalContext` routes active context, owning-role map, and "discover
  subagent tooling before orchestration work" to the lead Codex agent.
- Ownership enforcement is structural (enforced/blocked); fan-out is prominently prompted
  (not hard-enforced — accepted constraint documented here, not hidden).
- Release-from-bug/backlog work requires PE release-definition and mandatory grill before SPEC.
- Test covers persona-empty path to `specs/backlog/**` being blocked.

#### FR-C03 — Claude duplicate hook hygiene + OpenCode regression proof

Source: `specs/backlog/codex-context-hook-and-workflow-enforcement-hotfix.md` WS-3/WS-4

(a) Fresh `dadaia init` + `dadaia public install --target claude` yields exactly one
ctx-inject `UserPromptSubmit` entry (no legacy double-wiring).
(b) OpenCode first `chat.message` appends bootstrap; second `chat.message` appends nothing.

Acceptance:
- Single ctx-inject hook entry on fresh init.
- OpenCode session guard proven by test.

#### FR-C04 — Full Codex compatibility (FEAT-CODEX-COMPAT-100)

Source: `specs/backlog/full-codex-compatibility.md`

Seven sub-workstreams (CX-1 through CX-7):

- CX-1: Fix Codex agent semantic projection — no broad `claude-*` body rewriting; golden tests
  for skill names, file paths, agent names; `ai-engineer.toml` references real
  `ai-harness-claude-code` skill.
- CX-2: Codex-native command Rules — generate official Starlark `.rules` for command policy;
  decide Markdown protocol doc fate in `.codex/rules`.
- CX-3: Codex hook live smoke test — forbidden root write blocked; production write without
  approved task blocked; additive report/handoff write allowed; `ctx-inject.sh` emits valid
  Codex JSON.
- CX-4: Codex custom-agent config mapping — map dadaia activity classes to supported Codex
  custom-agent config; review/audit agents receive read-only or least-privilege config.
- CX-5: Codex subagent/orchestration truth update — memory + personas distinguish workflow
  files (reference docs) from custom-agent delegation (real when explicitly invoked).
- CX-6: Harness-neutral protocol references — Codex agents do not reference `.claude/rules/...`
  as governing protocol paths; shared references are harness-neutral.
- CX-7: Semantic doctor and CI gate — `dadaia public doctor` checks Codex semantic referential
  integrity; CI fails on non-existent skill references, stale harness paths, fake rule files.

Acceptance: all 8 non-negotiable invariants in `full-codex-compatibility.md §2` hold; fresh
temp workspace runs `public stage`, `public install --target all`, `public doctor`, and Codex
compatibility smoke checks cleanly.

---

### WS-SDD-LIFECYCLE — State model redesign + session orchestration + review gate

Three backlog items targeting the SDD enforcement core.

#### FR-L01 — Single TTL-lease record replaces four-store lock model

Source: `specs/backlog/sdd-state-model-redesign.md` (FEAT-STATE-MODEL-REDESIGN-01)
Design source of truth: `.dadaia/reports/dadaia-workspace/project-manager/2026-06-06T043437Z-state-model-redesign-proposal.md`

Replace the four-store lock model (semaphore + fcntl Lock-3 + session files + runtime .ptr)
with **ONE cross-platform JSON TTL-lease record per context**
(`.dadaia/states/ctx_locks/<ctx>.lock.json`), guarded by a thin fail-safe PreToolUse hook.

Locked design decisions (from the proposal — carry verbatim, do not re-debate):
- Lock guards release-mutation lifecycle only (MUTATING phases); backlog/audit/research are
  ADDITIVE and never blocked.
- Classify by write-target PATH, not bound mode.
- Liveness = JSON heartbeat + TTL lease. NO PID / `os.kill` / `/proc` anywhere.
- Drop `write_set` from the record; write authorization = agent-frontmatter allowlist in
  `agents.index.json`.
- No hard impl-XOR-review lock; PM coordinates phase sequence.
- Full cut in one atomic commit (no lingering dual-store).
- `O_EXCL` sentinel CAS on acquire — MUST-NOT-SHIP red line.
- Lock-1 / Lock-2 fcntl git-serialization locks untouched.

Acceptance:
- A single agent session carries through read → spec → implementation → review → closure
  with no relaunch and no manual re-export.
- Gate blocks only on a live-lease conflict; never halts additive work.
- `dadaia lock steal <ctx>` is the documented unblock command.
- `doctor --fix` GC actually deletes stale lock records and orphan session files.
- Injectable clock seam (`is_stale(data, *, clock, ...)`) for deterministic tests.
- Cross-harness honesty: real `decision:block` on Claude Code; guardrail-only on Codex;
  advisory on OpenCode (JSON PreToolUse unsupported).

#### FR-L02 — Review-gate relabel (FORK-1: honest relabel, no new hooks)

Source: `specs/backlog/review-gate-enforcement-decision.md` (FEAT-REVIEW-GATE-ENFORCEMENT-01)

FORK-1 resolved: **Option (b) honest relabel**. No new fail-closed git hooks. The review
stages (qa→commit, security→push, code-review→PR) are coordinator-enforced checkpoints,
not mechanical git-hook gates. Enforcement is PM coordinator's discipline.

Work: rename "gate" → "coordinator-enforced checkpoint" in constitution language and all
reviewer/PM personas. This becomes a WS-SDD-LIFECYCLE task (T-016-L04) touching only text
in `specs/constitution.md` and `dadaia_workspace/public/agents/`.

Rationale: adding verdict-reading git hooks reintroduces the fail-closed soft-deadlock
class that FR-L01 (TTL-lease redesign) is fixing. The pre-push CI gate (ruff/mypy/pytest)
already provides the quality guarantee; the lease model provides the spatial guarantee.
Honest naming is the safer choice for 0.1.6.

Acceptance:
- "Gate" terminology is replaced by "coordinator-enforced checkpoint" in constitution §11
  and all relevant reviewer + PM personas.
- No new git hook is introduced by this FR.
- `dadaia specs doctor` single-source lint shows no residual "gate" framing for the review
  stages (in reviewer/PM personas).
- No residual ambiguity in constitution §11 or reviewer personas.

#### FR-L03 — Session orchestration intent (FEAT-SESSION-SEMAPHORE-01)

Source: `specs/backlog/session-orchestration-semaphore.md`

The operator intent from this backlog item is absorbed into FR-L01 (TTL-lease redesign). The
per-context semaphore mechanism it originally proposed is superseded by the TTL-lease. This item
is satisfied when FR-L01's acceptance criteria hold, specifically: (a) concurrent
implement+review on the same context is impossible; (b) PM is the maestro that holds/releases
the critical section; (c) env-free session resolution; (d) flow never dead-ends.

---

### WS-SPECS-EVOLUTION — Specs evolution / migration framework

Source: `specs/backlog/specs-evolution-migration-framework.md` (FEAT-SPECS-EVOLUTION-200)

#### FR-S01 — Pattern version stamp in constitution.md frontmatter

Add `specs_pattern_version: N` to the YAML frontmatter of `specs/constitution.md`. Library
carries `CANONICAL_SPECS_VERSION` constant. Absent stamp ⇒ treat as version 0 (pre-framework);
doctor warns and recommends upgrade.

#### FR-S02 — Ordered idempotent migration-chain registry

Generalize the single `migrate tree-v2` transform into a registry of versioned steps
(`v0→v1`, `v1→v2`, ...) walked current → target. Each step is idempotent and dry-run-capable.
The existing `tree-v2` transform becomes the first registered step.

#### FR-S03 — Backup-first on every chain execution

Before any chain step runs, back up to `specs_bkp/<from>→<to>-<UTC>/` inside the repo.
The backup dir must be gitignored AND doctor-tolerated (explicit acceptance criterion).

#### FR-S04 — `dadaia specs upgrade` command

Sequence: backup-first → apply chain (current→target) → re-stamp pattern version → run
`dadaia specs doctor`. Doctor must exit 0; if not, point the operator back to the backup.
Flags: `--dry-run` (plan only, no writes); interactive confirmation before mutating;
idempotent (already-at-target ⇒ no-op).

#### FR-S05 — Doctor integration + wire create/alive

`dadaia specs doctor` warns when a project's `specs_pattern_version` is below
`CANONICAL_SPECS_VERSION` and recommends `dadaia specs upgrade`. Wire `context create` /
`context alive` to offer the backup-protected upgrade instead of today's silent add-missing-only
merge.

#### FR-S06 — Drift reconciliation (v0.2.1 T-021-15 safe-preserve claim)

The archived v0.2.1 CLOSURE claims T-021-15 ("Fix `alive()`: safe-preserve existing specs on
scaffold") was delivered at commit `b051853`. Code inspection confirms the backup code does not
exist (`service.py:204-209` still calls `_merge_scaffold_into`, which never creates a backup).

This release must choose path (a) or (b) from the backlog item §3 and document the resolution
in the CLOSURE. The chosen path must be stated in the PLAN. The misleading comment at
`service.py:195` must be corrected regardless of which path is chosen.

---

### WS-AGENTS — Agent roster reduction + surface cleanup

Two bugs and one backlog item.

#### FR-A01 — Agent skill surface slop — library-side fix

Source: `specs/bugs/agent-skill-surface-slop.md`
Note: re-stamped from `adopted: v0.2.0` to `adopted: 0.1.6` at SPEC authoring.

Strip dangling skill references from surviving generic personas:
- `public/agents/software-architect.md`: remove references to `architect-code-audit`,
  `architect-design-patterns`.
- `public/agents/devops-engineer.md`: remove references to `devops-deploy-strategies`,
  `github-actions-pipelines`, `devops-gitflow-governance`; remove dead
  `docs/agent-knowledge/devops-engineer/github-actions-pipelines.md` link.

Frontend/design skill pruning scope (5 skills: `frontend-design`,
`frontend-implementation-quality`, `design-reference-research`, `design-report-quality-gate`,
`ux-ui-review`) must be confirmed in the mandatory grill before execution — capability reduction,
not pure cleanup.

Acceptance:
- No generic persona references a skill absent from `public/skills/`.
- `dadaia public install --force --target all && dadaia public doctor` exits 0.
- A fresh `dadaia init` + `public install` yields the reduced surface on all runtimes; no
  orphans.
- The install prune mechanism (FR-A03) ensures orphan projections are removed.

#### FR-A02 — Constitution/persona single-source drift fix

Source: `specs/bugs/constitution-persona-single-source-drift.md`
Note: re-stamped from `adopted: v0.2.0` to `adopted: 0.1.6`.

Fix four single-source-of-truth contradictions (P1a–P1d) and three medium-priority items
(P2a–P2c):

- **P1a** — memory-write-phase: align all sources to DEFINITION + CLOSURE (delete CLOSURE-only
  statements in `product-engineer.md` and `workspace-protocol.md §5`).
- **P1b** — `quality-assurance.md` path: constitution §13 must match the actual file location
  on disk.
- **P1c** — project-auditor dispatch wording: reconcile the two contradictory paragraphs.
- **P1d** — dual grill-me ownership: state once that PM owns the intake grill and PE owns the
  release-definition grill on the picked set.
- **P2a** — plugin-stub exemption in constitution §14 persona-existence rule.
- **P2b** — qa-engineer worker→worker wording: route escalations through PM.
- **P2c** — gate-trio sequence cite in each reviewer persona.

#### FR-A03 — `dadaia public install` prune + doctor orphan detection

Source: `specs/bugs/install-does-not-prune-orphan-projections.md`

`dadaia public install` (or `--prune` flag, default-on for `--force`) removes managed projected
files (agents/skills/workflows/rules) absent from the current staging set, while never touching
operator-added files (use the manifest to distinguish lib-managed from operator files).

`dadaia public doctor` gains an orphan-projection check: any projected agent/skill/workflow/rule
absent from staging → `[orphan]` non-zero exit.

Acceptance:
- Regression test: stage with file A, install, delete A from source, stage, install → A is
  absent from all runtime projections and doctor flags it before the prune.
- Doctor exit 0 after a full round-trip: source edit → stage → install --prune → doctor.

#### FR-A04 — Roster reduction 15 → 9 (FEAT-DADAIA-AGENTS-01 P3/P4)

Source: `specs/backlog/dadaia-agent-specialization.md`

Reduce core roster from 15 to 9 (operator-confirmed):
- Merge `software-engineer-python` + `software-engineer-node` + `backend-engineer` → one
  `software-engineer`.
- Move `frontend-engineer` + `design-specialist` (+5 frontend/design skills) → plugin.
- Move `devops-engineer` → plugin.
- Remove `researcher` from core.
- Each surviving persona declares its activity class (MUTATING/ADDITIVE) + lease relationship +
  gate role per constitution §7/§14.

Deepen the four dadaia-specific personas (product-engineer, project-manager, project-auditor,
ai-engineer) per the P3/P4 specialization contract in the backlog file §2.1–§2.5.

R4 surface cleanup: delete stale workflows; restructure `product/` memory tree; prune skills
22 → 17. Apply anti-slop constraint: each persona/skill is reviewable by ai-engineer and a
second reader with no redundancy or over-explanation.

Acceptance:
- Roster is exactly 9 core + 3 plugin personas in `dadaia_workspace/public/agents/`.
- `dadaia public stage && install --force --target all && dadaia public doctor` exits 0.
- No dangling persona references or orphan skill refs.
- ai-engineer produces a strategy document reviewed by PM before PE authors the SPEC task.

#### ADR-A08 — software-architect anti-slop specialization (operator-requested)

Source: `specs/backlog/software-architect-anti-slop-specialization`

Operator-requested specialization of the `software-architect` persona into an explicit
anti-slop / anti-spaghetti architecture specialist, paired with a new Core Workflow skill
(two mandatory steps: Understand the Problem; Research Existing Solutions). Both persona and
skill must be slop-free, non-verbose, and directly actionable. Task: T-016-A08.

**Operator mandate — release/spec review gate (added 2026-06-07):**

In every spec/release review, the `software-architect` MUST:

1. **Root-cause gate:** Verify that each reported bug's root cause was correctly understood
   and that the release proposes a root-cause solution — never a workaround. If a release
   defines a bug's solution as a workaround, the `software-architect` REJECTS that solution
   and documents the rejection with an overview of the actual root cause and its expected
   fix. The architect understands the material difference between a workaround and its
   consequences (fragile layers, hard-to-track side-effect bugs) and does not permit
   workarounds to pass review.

2. **Architecture fidelity gate:** Verify that the SPEC correctly represents the
   architecture — the right abstractions, layers, and boundaries are declared, not a
   convenient approximation. If the SPEC misrepresents the architecture, the
   `software-architect` REJECTS it and states the required correction.

Both gates are non-negotiable review criteria; a SPEC that fails either is REJECTED.
Record both gate behaviors as part of the anti-slop specialization alongside the existing
anti-spaghetti / strong-layers / Core-Workflow requirements.

Backlog reconciliation note: `specs/backlog/software-architect-anti-slop-specialization.md`
(FEAT-SA-ANTISLOP-01) and `specs/backlog/software-architect-workspace-specialization.md`
(FEAT-SA-WORKSPACE-SPEC-01) cover overlapping intent. At TASK execution both MUST be
reconciled into one acceptance set (do not delete either file; annotate one as superseding
at the task level).

---

### WS-SANITIZATION — Root whitelist + `.dadaia/` hygiene

Two bugs and one backlog item.

#### FR-Z01 — `dadaia init --workspace` flag honored

Source: `specs/bugs/init-ignores-workspace-flag.md`

When `--workspace <dir>` is explicitly provided, treat it as authoritative: initialize exactly
that directory (create the sentinel there) instead of walking up to an ancestor workspace.

Fix: `dadaia_workspace/core/workspace_resolver.py:~57,100` —
`resolve_workspace_root_for_init` must treat an explicit `--workspace` path as the CWD, not as a
hint to the ancestor-walk.

Acceptance:
- `dadaia init --workspace /tmp/freshws` from inside an existing workspace writes only to
  `/tmp/freshws`.
- Unit test covers the explicit-`--workspace` path.

#### FR-Z02 — Workspace sanitization laws enforced

Source: `specs/backlog/workspace-sanitization.md`

Implement the remaining SANITIZE items not yet delivered:
- SANITIZE-03: canonical `.dadaia/` internal layout enforced (`.dadaia/mcps/<server>/`,
  `.dadaia/scripts/`, `.dadaia/tmp/<agent>/<YYYYMMDD>/`, `.dadaia/reports/`, `.dadaia/states/`).
- SANITIZE-04: declarative retention policy + `dadaia clean` (or equivalent) command with
  `--dry-run` default; safe-delete rules (never operator-created files; honor per-zone TTLs; log
  every reclaim).
- SANITIZE-05: `dadaia doctor` ROOT-1..ROOT-4 invariants checking root whitelist, forbidden
  caches, tool config placement, and `.dadaia/` internal layout.

Note: SANITIZE-01 (root whitelist hook) and SANITIZE-02 (root cleanup + root_exceptions.txt)
were delivered in v0.1.4.4 and closed. SANITIZE-03/04/05 remain open. The T-SANI-02
(`CLAUDE.md` + `prompt.md` whitelist) was delivered in v0.2.1 (which is being folded into
0.1.6); confirm it is present on the 0.1.6 baseline or re-deliver as part of this workstream.

Acceptance:
- `dadaia doctor` ROOT-1..ROOT-4 exit 0 on a clean workspace.
- `dadaia clean --dry-run` lists stale ephemeral files; `dadaia clean` removes them safely.
- No operator-created file is ever auto-deleted.
- `.dadaia/` internal layout matches the canonical map.

---

## 5. Architecture Deltas

- `dadaia_workspace/features/panel/` — handler.py auth unification; auth.py token atomic create;
  views/index.py + views/wrapper.py + views/_md_render.py canonical URL builder; views/assets/
  JS/CSS theme redesign; tab consolidation views.
- `dadaia_workspace/features/panel/service.py` — WorkflowLauncher extracted to infrastructure.
- `dadaia_workspace/core/protocols/` — WorkflowLauncher protocol (new).
- `dadaia_workspace/infrastructure/` — WorkflowLauncher implementation (new).
- `dadaia_workspace/features/spec_context/service.py` — `resolve_workspace_root_for_init` fix;
  `alive()` backup-protected upgrade wire (FR-S05).
- `dadaia_workspace/core/workspace_resolver.py` — `--workspace` flag honored (FR-Z01).
- `dadaia_workspace/features/specs/doctor.py` — orphan-projection check; ROOT-1..ROOT-4;
  pattern-version check; upgrade recommendation.
- `dadaia_workspace/features/migrate/` — migration-chain registry replacing single tree-v2
  transform; `dadaia specs upgrade` command.
- `dadaia_workspace/cli/main.py` — `specs upgrade` subcommand; `clean` command.
- `dadaia_workspace/public/scripts/ctx-inject.sh` — Codex idempotence fix (stable session key).
- `dadaia_workspace/public/scripts/sdd-spec-gate.sh` — TTL-lease redesign (gate shrink ~1050 →
  ~150 lines).
- `dadaia_workspace/public/agents/` — roster reduction 15→9; persona deepening; skill surface
  prune.
- `dadaia_workspace/public/skills/` — prune to native-workflow + coordinator skills.
- `specs/constitution.md` — frontmatter version stamp; P1a–P1d single-source fixes; §14
  plugin-stub exemption; review-gate semantics (whichever fork the operator chooses).
- `.codex/` — Starlark `.rules`; semantic projections for CX-1 through CX-6.
- `tests/` — new regression and e2e tests throughout.

---

## 6. Tech-Stack Deltas

No new runtime dependencies required by the feature work. If FR-L01 (TTL-lease gate rewrite)
or FR-C04 (Codex Starlark rules) introduces a new dependency, it must be confirmed in the PLAN.

---

## 7. Security / Operations Deltas

- FR-P07 (token file): closes a TOCTOU race on the panel Bearer token file.
- FR-P03 (auth route unification): eliminates latent auth-bypass footgun.
- FR-L01 (TTL-lease): `O_EXCL` CAS eliminates the force-reclaim / heartbeat-vs-reclaim TOCTOU
  races documented in the dev/test/review system audit.
- FR-C04 CX-2 (Codex command Rules): sensitive commands (`git push`, `dadaia context dead`,
  `dadaia public install`, destructive shell ops) receive explicit allow/prompt/forbid policy.
- FR-L02 (review gate): if option (a) is chosen, new git hooks; security-reviewer must approve
  the hook implementation before push.

---

## 8. Memory Files Affected at Closure

- `specs/memory/architecture.md` — TTL-lease state model, WorkflowLauncher protocol, migration
  framework, roster changes.
- `specs/memory/tech-stack.md` — any new dependencies; Codex compatibility; upgrade command.
- `specs/memory/product/index.md` — catalog updated for new/changed features.
- `specs/memory/product/<feature-slug>.md` — atoms for panel, lock-model, specs-upgrade,
  codex-compatibility, workspace-sanitization.
- `specs/memory/quality-assurance.md` — e2e strategy; global deploy gate; Codex smoke tests.
- `specs/constitution.md` — frontmatter version stamp; P1a–P1d corrections; §14 plugin-stub
  exemption; review-gate semantics per chosen fork.

---

## 9. Acceptance Criteria (release-level)

1. `dadaia specs doctor` exits 0 on the live workspace after all workstreams complete.
2. `dadaia public doctor` exits 0 after all `public/` changes are staged and installed.
3. The pytest suite passes (zero red) including all new regression tests.
4. Panel e2e suite passes with E2E-GUARD-01/02 active and the CI workspace seeded with a
   real spec context.
5. No panel or frontend change ships without deep-interaction e2e + global 4xx/5xx guard.
6. Two consecutive Codex prompts produce the full memory bootstrap exactly once.
7. `dadaia init --workspace /tmp/freshws` from inside an existing workspace writes only
   to `/tmp/freshws`.
8. `dadaia specs upgrade` runs backup-first → chain → re-stamp → doctor-exit-0 on a
   synthetic test workspace.
9. Core roster is exactly 9 (no more, no less) after roster reduction.
10. No generic persona references a skill absent from `public/skills/`.
11. ROOT-1..ROOT-4 doctor invariants pass on a clean workspace.
12. The review-gate fork (option a or b) is resolved and fully implemented with no residual
    ambiguity in constitution §11 or reviewer personas.
13. The v0.2.1 T-021-15 safe-preserve drift is explicitly resolved (implemented or corrected).

---

## 10. Out of Scope

- PyPI publish — operator-gated; not in this release (as always).
- OpenCode deep parity beyond not regressing existing projections (full OpenCode program is a
  future release).
- New panel features beyond the tab consolidation, theme redesign, and memory viewer fix.
- `dadaia plugin install` command — the plugin installation mechanism is not implemented in
  this CLI; the frontend-design deviation is an operator-authorized one-time workaround.
- Memory edits beyond the atoms listed in §8.
- Any feature not in the picked set above. The operator's explicit direction is "everything now,
  nothing deferred" — and this SPEC covers everything listed.

---

## 11. Resolved Decisions

All four forks were resolved by the operator in the mandatory grill session on 2026-06-07.
No fork remains open. The resolutions below are the canonical record.

### FORK-1 — Review-gate enforcement: RESOLVED → honest relabel

**Decision:** Option (b) honest relabel. No new fail-closed git hooks.

Rename "gate" → "coordinator-enforced checkpoint" in the relevant constitution/persona
language (this is a WS-SDD-LIFECYCLE text change, not mechanical enforcement). The
pre-push CI gate (ruff/mypy/pytest) provides quality guarantees; the TTL-lease provides
spatial guarantees. Adding verdict-reading git hooks would reintroduce the fail-closed
soft-deadlock class that FR-L01 is fixing.

Tasks affected: T-016-L04 work and done criterion updated to option (b) only.

---

### FORK-2 — Codex `ctx-inject.sh` session key: RESOLVED → SessionStart + stdin `session_id`

**Decision:** Use Codex `SessionStart` hook (matcher `startup|resume`) for the one-time
memory bootstrap. Idempotence key is the `session_id` JSON field that Codex passes on
stdin at startup. Subagents inherit the parent `session_id`. The `$$`/PID fallback is
abandoned.

Implementation: the generator change is in `public_assets.py` `_codex_hooks` (~line 2350)
to wire a `SessionStart` hook. The hook reads stdin and parses `session_id`.

Tasks affected: T-016-C01 work and done criterion updated.

---

### FORK-3 — Repeated-prompt hook output: RESOLVED → nothing + exit 0

**Decision:** The already-fired path emits nothing and exits 0 (doc-blessed no-op). The
per-prompt `[dadaia-workspace]` breadcrumb is dropped entirely from the `UserPromptSubmit`
path. No minimal payload. SessionStart carries context once per logical session.

Tasks affected: T-016-C01 done criterion updated; T-016-C11 documentation criterion updated.

---

### FORK-4 — Deterministic Codex workflow preflight: RESOLVED → combination approach

**Decision:** Combination of `PreToolUse` enforcement + `SessionStart` routing + `.rules`
command policy + AGENTS.md advisory.

- `PreToolUse` hook: enforces ownership/SDD-gate deterministically (hard block on
  writes to owner-only paths when persona is unresolved/empty).
- `SessionStart` `additionalContext`: routes active context + owning-role map +
  "discover subagent tooling before orchestration work".
- Codex `.rules`: govern commands only.
- AGENTS.md: advisory layer.

PM-only backlog is enforced via `sdd-spec-gate.sh` by two mechanisms:
(1) injecting `CODEX_AGENT_PERSONA` via `codex_agent_dispatcher.py` for known agents;
(2) fail-safe-blocking writes to `specs/backlog/**` (and other owner-only paths) when
the persona is unresolved/empty (current bug: these fall through to allowed).

Accepted constraint (documented, not hidden): specialist fan-out is NOT hard-enforceable
in Codex — Codex never auto-spawns subagents. Fan-out is a strongly-prompted expectation.
Ownership = enforced/blocked; fan-out = prompted.

Tasks affected: T-016-C03 work and done criterion updated.

---

### WS-PANEL operator feedback — 4 decisions (2026-06-07 grill extension)

The following four decisions were recorded after T-016-P01..P09 shipped (alpha-1 done) and
before the operator approved the mid-release scope addition of T-016-P10..P13. All four are
operator-confirmed and added to the WS-PANEL alpha-1 task list with Status remaining
Aprovado (mid-release scope extension, explicitly authorized).

**Decision W1 — Tab label renames**
"Spec Context Projects" tab → **"Projects"**; "Ops" tab → **"Agentic"**. Label-only change;
`data-section` attribute values (`memories`, `ops`) are kept stable to avoid cascading
JS/CSS breakage. Task: T-016-P10.

**Decision W2 — Agentic section order**
Inside the consolidated Agentic tab, sections are reordered top-to-bottom:
**Kanban (top) → Workflows → Agents** (was Agents → Workflows → Kanban from T-016-P09).
Rationale: Kanban is the most operationally relevant section for daily use.
Task: T-016-P11.

**Decision W3 — Agent card size reduction (~40%)**
Agent cards after tab consolidation are too large. Reduce visual footprint by ~40%, tighten
grid min-column-width, padding, stat-row, and badges. Legibility and WCAG AA must be
maintained. Task: T-016-P12.

**Decision W4 — Kanban 4-stage lifecycle columns (constitution §7 mapping)**
Replace the current {research, spec, implementation, review} column set with the canonical
four-stage release lifecycle from constitution §7:

| Column | Maps from | Lock modes |
|--------|-----------|------------|
| **Backlog** | Phases 1–2 (DISCOVERY, pre-release) | `READ` |
| **Release Definition** | Phase 3 (SPEC/PLAN/TASKS definition) | `SPEC` |
| **Implementation + Review** | Phases 4–5 (impl + review combined) | `BOUND_IMPLEMENTATION`, `BOUND_REVIEW` |
| **Closure** | Phase 6 (CLOSURE) | closure phase |

`BOUND_IMPLEMENTATION` and `BOUND_REVIEW` share one combined column — the XOR-lock-dimming
logic between them is retired. A within-column sub-indicator is acceptable but not required.
Task: T-016-P13.

---

## 12. Dependencies and Risks

**Sequencing dependencies:**
- FR-P06 (e2e gate) must be authored early so subsequent panel changes have a trustworthy suite.
- FR-L01 (TTL-lease redesign) must be complete before FR-L02 (review gate, option a) can add
  verdict-reading hooks — the lease model is the enforcement foundation.
- FR-A04 (roster reduction) requires ai-engineer strategy document reviewed by PM before PE
  authors the TASK scope.
- FR-S05 (alive() wire) depends on FR-S01 (version stamp) so the version is known before the
  upgrade is offered.
- WS-CODEX forks (§11 FORK-2/3/4) are resolved; FR-C01/C02/C03 tasks may proceed.

**Risks:**
- Scope is very large for a PATCH release; alpha-N segments isolate risk per workstream.
- FR-L01 gate shrink is the highest integration risk: the gate path must migrate atomically
  (old path → new path in a single commit or the MUTATING path silently breaks).
- FR-C04 Codex compatibility is broad; the CX-7 doctor gate and CI tests must be written
  before any CX-1/6 changes can be verified as drift-free.
- FR-A04 roster reduction has cascading write-set: personas + skills + manifest + doctor
  + all runtime projections must reconcile in one `install --prune && doctor` pass.
- FR-P08 tab consolidation touches shared chrome; Sessions tab regression risk is real.

**Deploy model:** single `feature/0.1.6` branch. Maturation: `alpha-1, alpha-2, ...` with
qa-engineer commit gate at each alpha; `rc-1, ...` with full ship trio (qa→commit,
security→push, code-review→PR) before merge. No PyPI publish without operator approval.
