# TASKS — Release 0.1.6 "Consolidation"

**Status:** Aprovado
**Release ID:** 0.1.6
**Owner:** product-engineer (authorship); implementing agents per task
**Date:** 2026-06-07

Marker discipline: `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
At most one `[-]` per owner at a time. Flip `[ ]` → `[-]` before starting; flip `[-]` →
`[x]` only after qa-engineer has committed the task green.

---

## alpha-1 — WS-PANEL

> Ordering: FR-P06 first (e2e guard makes the suite trustworthy); FR-P07 next (tiny,
> security, low-risk); then the functional fixes FR-P01/P05/P03/P04/P02; UX last (FR-P08).
> qa-engineer commit gate at the end of alpha-1.

### T-016-P01 — E2E global guard + CI workspace seed

- **Owner:** software-engineer
- **Write set:** `tests/e2e/panel/` (new global guard helpers), `.github/workflows/` (CI seed)
- **Precondition:** none
- **Work:** Implement E2E-GUARD-01 (fail on any 4xx/5xx during tab tour) and E2E-GUARD-02
  (fail on any console error). Seed CI panel workspace with a real spec context so
  data-dependent paths run. Verify existing e2e suite passes with guards active.
- **Done criterion:** guard helpers merged; CI `e2e-panel` job bootstraps a context; E2E-GUARD-01/02 active.

[x] T-016-P01

### T-016-P02 — Token file atomic restricted-mode create

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/auth.py`
- **Precondition:** none
- **Work:** Replace `write_text(token); os.chmod(path, 0o600)` with
  `fd = os.open(path, os.O_CREAT|os.O_WRONLY|os.O_EXCL, 0o600); os.write(fd, ...)`.
- **Done criterion:** Unit test verifies resulting file has mode `0o600`; no window between
  create and restrict.

[x] T-016-P02

### T-016-P03 — Canonical memory-URL builder + chip/iframe fix

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/index.py`,
  `dadaia_workspace/features/panel/views/wrapper.py`,
  `dadaia_workspace/features/panel/views/_md_render.py` (new shared builder)
- **Precondition:** T-016-P01 (guard exists before testing fix)
- **Work:** Create a single canonical memory-URL builder. Update all three call sites
  (chip hrefs, wrapper iframe src, wikilink renderer) to use it. `.html` paths → `.md`.
  Add E2E-SCP-03/04/05/06 regression tests (chip click → 200 + non-empty body).
- **Done criterion:** Clicking Architecture/Tech Stack/Product chips each returns 200 with
  real body in e2e test; E2E-SCP-03/04/05/06 pass; E2E-GUARD-01/02 stay green.

[x] T-016-P03

### T-016-P04 — Wikilink renderer parameterized by context slug

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/_md_render.py`
- **Precondition:** T-016-P03 (canonical URL builder exists)
- **Work:** Parameterize `build_renderer(slug)`; close over active slug in wikilink plugin;
  cache renderers per slug; route wikilinks through canonical builder.
- **Done criterion:** Wikilink in non-dadaia-workspace context resolves to the correct
  context slug, not hardcoded `dadaia-workspace`.

[x] T-016-P04

### T-016-P05 — Auth route unification

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/handler.py`
- **Precondition:** none
- **Work:** Collapse three auth classification lists into one declarative route struct
  `(pattern, name, auth_class)`. Give DELETE its own table or anchor ordering with a test.
  Unit test: every route has an explicit auth classification.
- **Done criterion:** No route can be added without classification; DELETE order enforced
  structurally; unit test passes.

[x] T-016-P05

### T-016-P06 — WorkflowLauncher extract to infrastructure layer

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/protocols/` (new protocol),
  `dadaia_workspace/infrastructure/` (new adapter),
  `dadaia_workspace/features/panel/service.py`
- **Precondition:** none
- **Work:** Define `WorkflowLauncher` protocol in `core/protocols/`; implement in
  `infrastructure/` (Popen + os.kill); inject into `PanelService`. Persist running workflow
  state to `.dadaia/states/` JSON. Unit test covers protocol + adapter.
- **Done criterion:** No `subprocess.Popen` or `os.kill` in `features/` layer; state
  survives panel restart; unit test green.

[x] T-016-P06

### T-016-P07 — Theme switcher functional fix

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/assets/js/themes.js`,
  theme CSS constants
- **Precondition:** T-016-P01 (guard active before UX change)
- **Work:** Diagnose `themes.js` + CSS; fix theme selection apply + localStorage persistence
  path. Add deep-interaction e2e test: click → option visible → dataset changes → persists
  across reload.
- **Done criterion:** Theme applies and persists; e2e test passes E2E-GUARD-01/02.

[x] T-016-P07

### T-016-P08 — Theme switcher visual redesign

- **Owner:** software-engineer (library source; operator-authorized plugin-scope deviation)
- **Write set:** `dadaia_workspace/features/panel/views/assets/` (CSS/JS), panel template
- **Precondition:** T-016-P07 (functional fix landed before redesign)
- **Work:** Visual overhaul of the bottom theme switcher per operator directive ("totally
  improved"). Operator reviews the redesign before rc-N ship.
- **Done criterion:** Operator-reviewed visual redesign; e2e tests pass E2E-GUARD-01/02.

[x] T-016-P08

### T-016-P09 — Tab consolidation (Agents + Workflows + Kanban → one tab)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/agents.py`,
  `dadaia_workspace/features/panel/views/workflows.py`,
  `dadaia_workspace/features/panel/views/kanban.py`,
  `dadaia_workspace/features/panel/views/assets/js/agents.js`,
  `dadaia_workspace/features/panel/views/assets/js/workflows.js`,
  `dadaia_workspace/features/panel/views/assets/js/kanban.js`,
  `dadaia_workspace/features/panel/views/index.py` (nav markup + section containers),
  `dadaia_workspace/features/panel/views/assets/js/core.js` (tab-switch wiring),
  associated CSS constants
  (write set widened during implementation: the nav/tab-switch wiring lives in
  index.py + core.js, which the merge inherently must touch.)
- **Precondition:** T-016-P01, T-016-P07 (guard active; functional theme fix landed)
- **Work:** Merge three tabs into one consolidated tab — **stacked sections (one scroll)**:
  Agents, Workflows, Kanban each a labelled section with smaller/compact cards, in a single
  scrollable tab. Sessions tab is untouched. Deep-interaction e2e test clicks through the
  consolidated tab and passes E2E-GUARD-01/02.
- **Done criterion:** Single consolidated tab; three separate tabs gone; Sessions tab
  unchanged; e2e test passes.

[x] T-016-P09

### T-016-P10 — Rename nav tabs ("Projects" and "Agentic")

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/index.py`,
  `tests/e2e/panel/` (specs asserting old tab labels: `tab-navigation.spec.ts`,
  `spec-context-tab.spec.ts`, `ops-tab.spec.ts`)
- **Precondition:** T-016-P09
- **Work:** Rename the "Spec Context Projects" nav tab to **"Projects"** and the "Ops" nav
  tab to **"Agentic"** (visible label text and `aria-label` only). Keep `data-section`
  attribute values stable (`data-section="memories"` and `data-section="ops"` remain
  unchanged to avoid cascading JS/CSS breakage). Update any e2e spec assertions that match
  the old label strings ("Spec Context Projects", "Ops") to the new labels ("Projects",
  "Agentic").
- **Done criterion:** Nav shows "Projects" and "Agentic"; `data-section` ids are unchanged;
  full panel e2e suite green with E2E-GUARD-01/02 active.

[x] T-016-P10

### T-016-P11 — Reorder Agentic tab sections (Kanban top, then Workflows, then Agents)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/index.py` (section order within
  the Agentic tab container), `dadaia_workspace/features/panel/views/assets/js/core.js`
  (load order adjustment if needed), associated CSS
- **Precondition:** T-016-P09
- **Work:** Reorder the three stacked sub-sections inside the Agentic tab so the display
  order from top to bottom is **Kanban → Workflows → Agents** (currently Agents →
  Workflows → Kanban from the T-016-P09 implementation). Update any e2e assertions that
  depend on section order within the tab.
- **Done criterion:** Agentic tab renders Kanban first, Workflows second, Agents third;
  e2e green with E2E-GUARD-01/02 active.

[x] T-016-P11

### T-016-P12 — Agent cards ~40% smaller + layout tightening

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/assets/css/agents.py` (or the
  equivalent CSS constants file for agent card styles),
  `dadaia_workspace/features/panel/views/assets/js/agents.js`
- **Precondition:** T-016-P09
- **Work:** Reduce the visual footprint of agent cards by approximately 40% (they are too
  large after the tab consolidation). Tighten the grid layout: reduce `min-column-width`,
  padding, stat-row line-height, and badge sizing while keeping all text legible. Run axe
  accessibility checks to confirm WCAG AA is maintained after the resize. Update any e2e
  assertions that depend on exact card dimensions.
- **Done criterion:** Agent cards are visibly ~40% smaller with a clean, compact grid
  layout; axe accessibility checks pass; E2E-GUARD-01/02 green; any agent-card axe tests
  pass.

[x] T-016-P12

### T-016-P13 — Kanban 4-stage lifecycle columns (constitution §7)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/kanban.py` (column model +
  lock-mode → column mapping + docstring update),
  `dadaia_workspace/features/panel/views/assets/js/kanban.js` (column labels + render
  logic), `dadaia_workspace/features/panel/views/assets/css/kanban.py` (column layout
  CSS), `tests/e2e/panel/` (kanban e2e specs), `tests/unit/features/panel/` (kanban unit
  tests)
- **Precondition:** T-016-P09
- **Work:** Replace the current four kanban columns {research, spec, implementation,
  review} with the canonical §7 release lifecycle: **Backlog | Release Definition |
  Implementation + Review | Closure**. Lock-mode → column mapping:
  - `READ` → **Backlog**
  - `SPEC` → **Release Definition**
  - `BOUND_IMPLEMENTATION` + `BOUND_REVIEW` → **Implementation + Review** (one combined
    column; retire the XOR-lock-dimming logic since the two modes share one column; a
    within-column sub-indicator is acceptable but not required)
  - Closure phase → **Closure** (feed from sessions/contexts that have reached the
    closure phase; present-but-empty if none are currently in closure)
  Update `kanban.py` docstring and the column-label map. Update all kanban unit tests and
  e2e specs to assert the new four-column layout.
- **Done criterion:** Kanban renders exactly 4 columns: Backlog / Release Definition /
  Implementation + Review / Closure; impl and review contexts appear in the combined
  column; unit tests and e2e specs green; E2E-GUARD-01/02 active.

[x] T-016-P13

---

## alpha-2 — WS-SANITIZATION

> qa-engineer commit gate at end of alpha-2.

### T-016-Z01 — `dadaia init --workspace` flag honored

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/workspace_resolver.py`
- **Precondition:** none
- **Work:** Fix `resolve_workspace_root_for_init` so an explicit `--workspace <dir>` path
  is treated as authoritative (not forwarded to ancestor-walk). Unit test: init with
  `--workspace /tmp/freshws` from inside an existing workspace writes only to `/tmp/freshws`.
- **Done criterion:** Unit test passes; no silent ancestor-workspace mutation.

[x] T-016-Z01

### T-016-Z02 — ROOT doctor invariants (ROOT-1..ROOT-4)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`
- **Precondition:** none
- **Work:** Add ROOT-1 (root whitelist), ROOT-2 (no forbidden caches at root), ROOT-3
  (tool configs in canonical homes), ROOT-4 (`.dadaia/` canonical subdirs) checks. Tests:
  each check fires on a synthetic violating tree.
- **Done criterion:** All four checks present; tests pass; `dadaia doctor` ROOT-1..ROOT-4
  exit 0 on the clean live workspace.

[x] T-016-Z02

### T-016-Z03 — Canonical `.dadaia/` layout + `dadaia clean` command

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/main.py` (`dadaia clean`),
  `dadaia_workspace/features/` (retention policy logic)
- **Precondition:** T-016-Z02 (ROOT-4 check defined first)
- **Work:** Implement `dadaia clean` with `--dry-run` default. Declarative per-zone TTL
  (`.dadaia/tmp/`, `.dadaia/reports/`, `.dadaia/dev-report/`). Safe-delete: never touch
  operator-created files; log every reclaim. Unit tests cover dry-run, safe-delete, TTL.
- **Done criterion:** `dadaia clean --dry-run` lists stale files; `dadaia clean` removes
  them; no operator file ever deleted; unit tests pass.

[x] T-016-Z03

### T-016-Z04 — Fix malformed duplicate UserPromptSubmit hook write

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/workspace/service.py`,
  `dadaia_workspace/infrastructure/public_assets.py`
- **Precondition:** none
- **Work:** `WorkspaceService._configure_hook` appends a flat-schema `UserPromptSubmit`
  hook entry that duplicates / conflicts with the nested-schema entry written by
  `public_assets.py`, causing Claude Code `/doctor` to report
  `hooks.UserPromptSubmit.1.hooks: Expected array`. Make `_configure_hook` write the
  canonical nested schema (or skip when the projection already provides it); no duplicate
  malformed entry. Unit test: configuring hooks yields a single well-formed
  `UserPromptSubmit` entry that passes the schema. See bug
  `configure-hook-writes-malformed-duplicate-userpromptsubmit`.
- **Done criterion:** `/doctor` no longer reports the malformed-array error; settings has one
  well-formed UserPromptSubmit entry; unit test green.

[x] T-016-Z04

---

## alpha-3 — WS-SPECS-EVOLUTION

> Confirm path (a) or (b) for FR-S06 drift before this alpha starts (operator decision
> from grill). qa-engineer commit gate at end of alpha-3.

### T-016-S01 — Drift reconciliation: v0.2.1 T-021-15 safe-preserve claim

- **Owner:** product-engineer (annotation if path b) / software-engineer (implementation if path a)
- **Write set:** `dadaia_workspace/features/spec_context/service.py` (path a);
  `specs/bugs/` annotation (path b)
- **Precondition:** operator confirms path (a) or (b) at grill; FR-S06 states the chosen path
- **Work:** Path (a): implement the backup in `service.py` so the v0.2.1 claim becomes true.
  Path (b): correct the misleading comment at `service.py:195` + annotate the v0.2.1 archived
  record. Either path: correct the comment at `service.py:195`.
- **Done criterion:** Comment is corrected; chosen path is implemented and tested; PLAN states
  which path was taken.

[x] T-016-S01

### T-016-S02 — Pattern version stamp in constitution.md

- **Owner:** product-engineer
- **Write set:** `specs/constitution.md` (add YAML frontmatter),
  `dadaia_workspace/` (CANONICAL_SPECS_VERSION constant)
- **Precondition:** T-016-S01 done
- **Work:** Add `specs_pattern_version: N` to `specs/constitution.md` frontmatter. Add
  `CANONICAL_SPECS_VERSION` constant in library code (single source). Define absent-stamp
  semantics (version 0 / pre-framework).
- **Done criterion:** `constitution.md` has valid YAML frontmatter with version stamp;
  library constant exists; absent-stamp treated as v0.

[x] T-016-S02

### T-016-S03 — Migration-chain registry

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/migrate/`
- **Precondition:** T-016-S02 (version stamp defined)
- **Work:** Generalize single `migrate tree-v2` into a registry of versioned steps walked
  current → target. Each step is idempotent and dry-run-capable. Register `tree-v2` as the
  first step.
- **Done criterion:** Registry exists; `tree-v2` is registered; idempotency tests pass.

[x] T-016-S03

### T-016-S04 — Backup-first implementation

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/migrate/`
- **Precondition:** T-016-S03
- **Work:** Before any chain step runs, back up to `specs_bkp/<from>→<to>-<UTC>/` inside
  the repo. The backup dir is gitignored. Doctor explicitly tolerates it (no false ROOT
  warnings). Tests: backup created before migration; gitignored; doctor-tolerant.
- **Done criterion:** Backup created on every migration run; gitignored; `dadaia doctor`
  does not flag `specs_bkp/`.

[x] T-016-S04

### T-016-S05 — `dadaia specs upgrade` command

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/cli/main.py`, `dadaia_workspace/features/migrate/`
- **Precondition:** T-016-S03, T-016-S04
- **Work:** Implement `dadaia specs upgrade` with: `--dry-run` (plan only); interactive
  confirm; backup-first → chain → re-stamp → `dadaia specs doctor`; exit-0-or-restore;
  idempotent (already-at-target ⇒ no-op). Integration test on a synthetic workspace.
- **Done criterion:** All flags work; `--dry-run` produces correct plan; integration test
  passes; doctor exits 0 on success.

[x] T-016-S05

### T-016-S06 — Doctor + create/alive integration for upgrade

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py`,
  `dadaia_workspace/features/spec_context/service.py`
- **Precondition:** T-016-S02, T-016-S05
- **Work:** Doctor warns when `specs_pattern_version < CANONICAL_SPECS_VERSION` and
  recommends `dadaia specs upgrade`. Wire `context create` / `context alive` to offer
  the backup-protected upgrade instead of silent add-missing-only merge.
- **Done criterion:** Doctor warn fires on a below-version tree; `context alive` on a
  stale-pattern tree offers upgrade; regression test covers both paths.

[x] T-016-S06

---

## alpha-4 — WS-CODEX

> Forks FORK-2, FORK-3, FORK-4 resolved (see SPEC §11 Resolved Decisions).
> qa-engineer commit gate at end of alpha-4.

### T-016-C01 — ctx-inject.sh Codex idempotence fix

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/scripts/ctx-inject.sh`, `.codex/hooks.json`,
  `dadaia_workspace/public_assets.py` (`_codex_hooks` ~line 2350)
- **Precondition:** none (FORK-2/3 resolved — see SPEC §11)
- **Work:** Wire a `SessionStart` hook (matcher `startup|resume`) in `public_assets.py`
  `_codex_hooks`. The hook reads stdin and parses the `session_id` JSON field that Codex
  passes at startup; subagents inherit the parent `session_id`. Use `session_id` as the
  idempotence key (stable across all invocations in a logical session). Drop the `$$`/PID
  fallback entirely. The already-fired path emits nothing and exits 0 (doc-blessed no-op).
  Drop the per-prompt `[dadaia-workspace]` breadcrumb from the `UserPromptSubmit` path
  entirely — SessionStart carries context once. Tests assert bootstrap markers appear at
  most once per session for Codex.
- **Done criterion:** Two consecutive Codex prompts produce bootstrap exactly once; second
  prompt produces no output (not even a breadcrumb); `ctx-inject.sh` reads `session_id`
  from stdin; `$$` not used; `public_assets.py` wires the `SessionStart` hook; tests pass.

[x] T-016-C01

### T-016-C02 — Claude duplicate hook hygiene + OpenCode regression proof

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/scripts/ctx-inject.sh`,
  `dadaia_workspace/public/` (init/install idempotence)
- **Precondition:** T-016-C01
- **Work:** Fresh `dadaia init + public install --target claude` yields exactly one
  ctx-inject `UserPromptSubmit` entry. OpenCode first message appends bootstrap; second
  message appends nothing. Tests cover both.
- **Done criterion:** Single hook entry on fresh init; OpenCode session guard proven.

[x] T-016-C02

### T-016-C03 — Deterministic Codex workflow preflight

- **Owner:** ai-engineer (hook + SessionStart routing + rules design) + software-engineer
  (`codex_agent_dispatcher.py` + `sdd-spec-gate.sh` persona-empty block)
- **Write set:** `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (fail-safe-block on
  empty/unresolved persona for owner-only paths), `dadaia_workspace/` (codex_agent_dispatcher.py
  — CODEX_AGENT_PERSONA injection), Codex `.rules` sources (command policy), SessionStart
  `additionalContext` wiring
- **Precondition:** T-016-C01 (SessionStart hook exists); FORK-4 resolved (see SPEC §11)
- **Work (combination approach — FORK-4 resolved):**
  1. `PreToolUse` hook (`sdd-spec-gate.sh`): add fail-safe-block for writes to
     `specs/backlog/**` and other owner-only paths when `CODEX_AGENT_PERSONA` is empty or
     not the declared owner — emit a clear unblock message; never silently allow.
  2. `codex_agent_dispatcher.py`: inject `CODEX_AGENT_PERSONA` env var for known custom
     agents so the gate can resolve persona without model-memory.
  3. `SessionStart` `additionalContext`: include active context, owning-role map, and
     "discover subagent tooling before orchestration work" instruction.
  4. Codex `.rules` (CX-2, T-016-C05): command policy only (separate task).
  5. AGENTS.md: advisory layer (existing, no new changes here).
  Note: specialist fan-out is NOT hard-enforceable (Codex does not auto-spawn) — prominently
  prompt; accepted constraint. Do not attempt to gate fan-out mechanically.
- **Done criterion:** `PreToolUse` hook blocks writes to `specs/backlog/**` when persona is
  unresolved or is not `project-manager`; `codex_agent_dispatcher.py` injects persona for
  known agents; `SessionStart` routes active context + owning-role map; test covers the
  persona-empty path to `specs/backlog/**` being blocked; no silent fall-through.

[x] T-016-C03

### T-016-C04 — CX-1: Fix Codex agent semantic projection

- **Owner:** software-engineer (projector + tests); ai-engineer (AI-surface intent review)
- **Write set:** `dadaia_workspace/` projector code (`runtime_transforms/codex.py`),
  `dadaia_workspace/public/` (source agents); `tests/` (golden tests)
- **Precondition:** T-016-C01
- **Work:** Replace broad `claude-*` body rewriting. Add golden tests for skill names,
  file paths, agent names, model tables. Regenerate Codex agents.
- **Done criterion:** `ai-engineer.toml` references real `ai-harness-claude-code` skill;
  golden tests pass; `dadaia public doctor` exits 0.

[x] T-016-C04

### T-016-C05 — CX-2: Codex-native command Rules

- **Owner:** ai-engineer (rule design); software-engineer (generator + doctor + tests);
  security-reviewer review before push
- **Write set:** Starlark `.rules` sources, projector code, `dadaia_workspace/features/`
  (generator)
- **Precondition:** T-016-C04
- **Work:** Generate official Starlark `.rules` for command policy. Decide Markdown protocol
  doc fate in `.codex/rules`. Validate generated rules where tooling supports.
- **Done criterion:** Sensitive commands have explicit allow/prompt/forbid policy; Starlark
  `.rules` are valid; security-reviewer APPROVED handoff before push.

[x] T-016-C05

### T-016-C06 — CX-3: Codex hook live smoke test

- **Owner:** software-engineer + qa-engineer
- **Write set:** `tests/` (smoke test harness)
- **Precondition:** T-016-C01, T-016-C05
- **Work:** Temp workspace Codex-compatible test: forbidden root write blocked; production
  write without approved task blocked; additive write allowed; `ctx-inject.sh` emits valid
  Codex JSON.
- **Done criterion:** All three hook behaviors proven by smoke test.

[x] T-016-C06

### T-016-C07 — CX-4: Codex custom-agent config mapping

- **Owner:** ai-engineer (role policy); software-engineer (TOML generator)
- **Write set:** TOML generator, `dadaia_workspace/public/` (agent sources)
- **Precondition:** T-016-C01
- **Work:** Map dadaia activity classes to supported Codex custom-agent config. Review/audit
  agents receive read-only or least-privilege config. Generated TOML is portable (no
  provider/auth/telemetry config).
- **Done criterion:** Activity-class → config mapping documented and tested; TOML validates.

[x] T-016-C07

### T-016-C08 — CX-5: Codex subagent/orchestration truth update

- **Owner:** product-engineer (memory/SPEC); ai-engineer (persona/workflow wording)
- **Write set:** `specs/memory/` (architecture + tech-stack + product atoms);
  `dadaia_workspace/public/agents/` (dispatcher wording)
- **Precondition:** T-016-C04
- **Work:** Memory states that Codex custom agents/subagents are real when explicitly
  invoked, while workflow files are reference docs. Dispatcher personas use Codex-native
  wording for delegation.
- **Done criterion:** No obsolete "Codex reference-only" blanket wording where it contradicts
  current Codex docs; memory matches current Codex runtime.

[x] T-016-C08

### T-016-C09 — CX-6: Harness-neutral protocol references

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/` (Codex agent sources)
- **Precondition:** T-016-C04
- **Work:** Generated Codex agents do not reference `.claude/rules/...`. Shared protocol
  references point to `AGENTS.md`, `.codex` protocol docs, or neutral "workspace protocol"
  phrase. Doctor fails if `.codex/agents/*.toml` contains stale Claude-only governance paths.
- **Done criterion:** No `.claude/rules` references in Codex agents; doctor check added.

[x] T-016-C09

### T-016-C10 — CX-7: Semantic doctor + CI gate

- **Owner:** software-engineer + qa-engineer
- **Write set:** `dadaia_workspace/features/` (doctor checks), `tests/` (CI gate tests)
- **Precondition:** T-016-C04 through T-016-C09
- **Work:** `dadaia public doctor` checks Codex semantic referential integrity. CI fails on
  non-existent skill references, missing TOML files, stale harness paths, fake rule files,
  unsupported config keys, unvalidated hook contracts.
- **Done criterion:** All 8 non-negotiable invariants from `full-codex-compatibility.md §2`
  hold; `dadaia public doctor` exits 0 on a canonical workspace.

[x] T-016-C10

### T-016-C11 — Context-engineering documentation correction

- **Owner:** ai-engineer + product-engineer
- **Write set:** `dadaia_workspace/public/skills/` (ai-harness-claude-code, ai-harness-codex,
  dadaia-step0-memory-bootstrap); `specs/memory/architecture.md`, `specs/memory/tech-stack.md`
- **Precondition:** T-016-C01
- **Work:** Docs state: hooks may fire every prompt; full static context injects once per
  logical session. Static/deep context belongs in skills or once-per-session bootstrap.
  All affected skills and memory atoms agree.
- **Done criterion:** No skill or memory atom implies repeated full-bootstrap injection;
  harness skills and memory agree.

[x] T-016-C11

---

## alpha-5 — WS-SDD-LIFECYCLE

> FORK-1 resolved: honest relabel (no new git hooks) — see SPEC §11 Resolved Decisions.
> MUST-NOT-SHIP red line: gate migration must be atomic (one commit).
> qa-engineer commit gate at end of alpha-5.

### T-016-L01 — Single TTL-lease record: core module + is_stale predicate

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/core/` (new TTL-lease module), `tests/unit/` (injectable
  clock seam tests)
- **Precondition:** none
- **Work:** Implement single per-context JSON TTL-lease record. `is_stale(data, *, clock)`
  predicate with injectable clock (no direct `datetime.now` in predicate). `O_EXCL` CAS
  on acquire. One `is_stale` predicate in `core/` replacing the 3 divergent impls.
- **Done criterion:** Unit tests: CAS prevents double-acquire; injectable clock makes
  staleness deterministic; `O_EXCL` test passes.

[x] T-016-L01

### T-016-L02 — Delete Lock-3 + retire semaphore.py + gate shrink (atomic)

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/locking.py` (delete Lock-3 surface),
  `dadaia_workspace/features/semaphore.py` (retire),
  `dadaia_workspace/public/scripts/sdd-spec-gate.sh` (shrink ~1050 → ~150 lines),
  `dadaia_workspace/core/` (integrate new TTL-lease module)
- **Precondition:** T-016-L01 (core module + CAS complete)
- **Work:** Delete Lock-3 surface: `create/release/reclaim_impl_lock`, `check_lock_state`,
  `has_implementation_lock`, `find_review_sessions`, `_session_is_stale`, `renew_heartbeat`,
  `LockState`, `check_impl_xor_review`. Retire `semaphore.py`. Migrate gate to read new
  `<ctx>.lock.json` record. Migration MUST be atomic — old path and new path change in ONE
  commit. Regression tests for gate behavior.
- **Done criterion:** Gate reads only the new TTL-lease record; Lock-3 and semaphore.py
  deleted; migration is one commit; regression tests green; MUST-NOT-SHIP red line satisfied.

[x] T-016-L02

### T-016-L03 — Doctor GC + lock steal CLI verb

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/specs/doctor.py` (lock invariants),
  `dadaia_workspace/cli/main.py` (`dadaia lock steal`)
- **Precondition:** T-016-L01, T-016-L02
- **Work:** `doctor --fix` GC deletes stale lock records and orphan session files. Collapse
  LOCK-2..LOCK-7 doctor checks into one `<ctx>.lock.json` invariant check. Add `dadaia lock
  steal <ctx>` CLI verb as the documented unblock command.
- **Done criterion:** GC deletes stale locks; doctor exit 0 on clean workspace; `lock steal`
  command works.

[x] T-016-L03

### T-016-L04 — Review-gate honest relabel (FORK-1: option b)

- **Owner:** product-engineer (constitution §11 wording) + ai-engineer (reviewer/PM persona
  wording in `dadaia_workspace/public/agents/`)
- **Write set:** `specs/constitution.md` (§11 review-gate language), `dadaia_workspace/public/agents/`
  (reviewer + PM personas: qa-engineer, security-reviewer, code-reviewer, project-manager)
- **Precondition:** FORK-1 resolved (see SPEC §11); T-016-L02 (gate stable — ensures no new
  hook surface is regressed by this text change)
- **Work:** Rename "gate" → "coordinator-enforced checkpoint" in constitution §11 and all
  relevant reviewer/PM persona language. No new git hooks are introduced. Run
  `dadaia public stage && install --target all && dadaia public doctor`. Verify
  `dadaia specs doctor` single-source lint shows no residual "gate" framing for the review
  stages in reviewer/PM personas.
- **Done criterion:** "Coordinator-enforced checkpoint" terminology is used consistently in
  constitution §11 and all reviewer/PM personas; `dadaia specs doctor` exits 0 with no
  single-source contradiction; `dadaia public doctor` exits 0; no new hook introduced.

[x] T-016-L04

---

## alpha-6 — WS-AGENTS

> Prerequisite: ai-engineer strategy document reviewed by PM before alpha-6 starts.
> qa-engineer commit gate at end of alpha-6.

### T-016-A01 — ai-engineer roster-reduction strategy document

- **Owner:** ai-engineer
- **Write set:** `.dadaia/reports/dadaia-workspace/ai-engineer/` (strategy HTML report)
- **Precondition:** none (ADDITIVE phase — no gate required)
- **Work:** Produce a strategy document answering: which skills are thin vs need dedicated
  new skills (toward 22→17 prune); what goes in each persona body vs referenced skill vs
  rule; how each persona declares activity class + lease relationship + gate role; minimum
  edit per persona; how merged `software-engineer` subsumes three prior implementers.
- **Done criterion:** Strategy document reviewed and approved by PM before T-016-A03 starts.

[x] T-016-A01

### T-016-A02 — `dadaia public install` prune + doctor orphan detection

- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/public/` (install prune logic),
  `dadaia_workspace/features/specs/doctor.py` (orphan-projection check),
  `tests/` (orphan detection regression test)
- **Precondition:** none
- **Work:** `dadaia public install` (or `--prune` flag, default-on for `--force`) removes
  managed projected files absent from staging. Doctor orphan check: projected agent/skill/
  workflow/rule absent from staging → `[orphan]` non-zero exit. Regression test: stage A,
  install, delete A, stage, install → A absent + doctor flags it.
- **Done criterion:** Orphan detection regression test passes; doctor exit non-zero on
  orphan; prune removes orphan.

[x] T-016-A02

### T-016-A03 — Agent skill surface slop — strip dangling refs

- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/agents/software-architect.md`,
  `dadaia_workspace/public/agents/devops-engineer.md`
- **Precondition:** T-016-A01 (strategy confirms which refs to strip); T-016-A02 (prune exists)
- **Work:** Strip references to `architect-code-audit`, `architect-design-patterns` from
  `software-architect.md`. Strip references to `devops-deploy-strategies`,
  `github-actions-pipelines`, `devops-gitflow-governance` and dead
  `docs/agent-knowledge/...` link from `devops-engineer.md`. Frontend/design skill scope
  per strategy. Run `dadaia public stage && install --force --target all && doctor`.
- **Done criterion:** No generic persona references a skill absent from `public/skills/`;
  `dadaia public doctor` exits 0.

[x] T-016-A03

### T-016-A04 — Update agent-skill-surface-slop bug adopted field

- **Owner:** product-engineer
- **Write set:** `specs/bugs/agent-skill-surface-slop.md`
- **Precondition:** T-016-A03
- **Work:** Update `adopted:` frontmatter from `v0.2.0` to `0.1.6`.
- **Done criterion:** Frontmatter updated.

[x] T-016-A04

### T-016-A05 — Constitution/persona single-source drift fix (P1a–P1d, P2a–P2c)

- **Owner:** product-engineer (constitution §) + ai-engineer (persona wording)
- **Write set:** `specs/constitution.md`, `dadaia_workspace/public/agents/` (product-engineer,
  project-manager, project-auditor, qa-engineer, security-reviewer, code-reviewer)
- **Precondition:** T-016-A01 (strategy document informs persona edits)
- **Work:**
  - P1a: align all sources to memory-write DEFINITION + CLOSURE (delete CLOSURE-only statements).
  - P1b: align constitution §13 QA path to actual file location on disk.
  - P1c: reconcile project-auditor dispatch wording (two contradictory paragraphs).
  - P1d: state once that PM owns intake grill; PE owns release-definition grill.
  - P2a: add plugin-stub exemption in constitution §14.
  - P2b: qa-engineer worker→worker escalations route through PM.
  - P2c: gate-trio sequence cite (§11) in each reviewer persona.
  Run `dadaia public stage && install --target all && dadaia public doctor`.
- **Done criterion:** Single-source lint clean; `dadaia specs doctor` exit 0; `dadaia public
  doctor` exit 0.

[x] T-016-A05

### T-016-A06 — Update constitution-persona-single-source-drift bug adopted field

- **Owner:** product-engineer
- **Write set:** `specs/bugs/constitution-persona-single-source-drift.md`
- **Precondition:** T-016-A05
- **Work:** Update `adopted:` frontmatter from `v0.2.0` to `0.1.6`.
- **Done criterion:** Frontmatter updated.

[x] T-016-A06

### T-016-A07 — Roster reduction 15 → 9

- **Owner:** ai-engineer (persona/skill reduction); software-engineer (TOML + manifest);
  product-engineer (constitution §14 updates)
- **Write set:** `dadaia_workspace/public/agents/` (merge/remove personas),
  `dadaia_workspace/public/skills/` (prune to 17),
  `dadaia_workspace/public/` (manifest, scaffold, stage);
  `specs/constitution.md` (§14 roster table)
- **Precondition:** T-016-A01 (strategy), T-016-A02 (prune exists), T-016-A03 (slop clean)
- **Work:**
  - Merge `software-engineer-python` + `software-engineer-node` + `backend-engineer` → one
    `software-engineer`.
  - Move `frontend-engineer` + `design-specialist` (+5 frontend/design skills) → plugin.
  - Move `devops-engineer` → plugin.
  - Remove `researcher` from core.
  - Deepen four dadaia-specific personas (product-engineer, project-manager, project-auditor,
    ai-engineer) per the P3/P4 specialization contract.
  - Each surviving persona declares activity class + lease relationship + gate role per §7/§14.
  - R4 surface cleanup: delete stale workflows; restructure `product/` memory tree; prune
    skills 22→17.
  - Run `dadaia public stage && install --force --prune --target all && doctor`.
  - Update constitution §14 roster table.
- **Done criterion:** Exactly 9 core personas in `public/agents/`; `dadaia public doctor`
  exits 0; no dangling refs; roster count test passes.

[x] T-016-A07

### T-016-A08 — software-architect anti-slop specialization

- **Owner:** ai-engineer (persona + skill are lib-originated assets)
- **Write set:** `dadaia_workspace/public/agents/software-architect.md` (persona),
  `dadaia_workspace/public/skills/` (new or updated Core Workflow skill),
  `dadaia_workspace/public/` (stage/manifest)
- **Precondition:** T-016-A07 (roster settled) — may run independently if the
  `software-architect` persona already exists at the start of this task.
- **Work:** Rewrite the `software-architect` system-prompt into an anti-slop /
  anti-spaghetti architecture specialist per backlog
  `software-architect-anti-slop-specialization`: reviews all code/tests for slop;
  never allows spaghetti; identifies bad practices (features built on rotted
  foundations; AI "code-on-code" producing fragile layers); enforces strong
  layers/encapsulation/block-by-block maintainable architecture; keeps projects
  human-workable (assumes AI may be unavailable); OOP designs clean enough to derive
  a UML; philosophy = simplicity-first, firm review positions, documents
  layers/foundations/core/interfaces/test-architecture. Create or update a skill
  giving the architect a **Core Workflow**: (1) Understand the Problem (core problem,
  constraints, success criteria, assumptions; clarifying questions); (2) Research
  Existing Solutions (WebSearch tools/patterns/pitfalls/comparisons; evaluate
  maturity/fit/integration/cost/risk). Both persona and skill must be slop-free:
  clear, organized, non-verbose, direct.
  **Operator mandate (2026-06-07) — add to the persona as release/spec review gate:**
  In every spec/release review the architect MUST enforce two non-negotiable gates:
  (a) **Root-cause gate:** every bug fix in the release addresses the actual root cause,
  not a workaround; if a workaround is detected, the architect REJECTS the solution and
  documents the root cause and required fix (the architect understands the difference
  between a workaround and a root-cause fix and its downstream consequences: fragile
  layers, hard-to-track side-effect bugs);
  (b) **Architecture fidelity gate:** the SPEC correctly represents the architecture —
  right abstractions, layers, and boundaries; if the SPEC misrepresents the
  architecture, the architect REJECTS it with the required correction.
  Both gates produce a REJECTED verdict if not satisfied; they are part of the
  anti-slop specialization, alongside anti-spaghetti / strong-layers / Core-Workflow.
  **Backlog reconciliation (mandatory):** `specs/backlog/software-architect-anti-slop-specialization.md`
  (FEAT-SA-ANTISLOP-01) and `specs/backlog/software-architect-workspace-specialization.md`
  (FEAT-SA-WORKSPACE-SPEC-01) MUST be reconciled into one acceptance set at execution time;
  do not delete either file — annotate one as superseded by the other at the task level.
  Then run `dadaia public stage && install --target all && doctor`.
- **Done criterion:** `software-architect` persona reflects the anti-slop mandate
  (clear/non-verbose); the Core Workflow skill exists and is scoped appropriately;
  `dadaia public doctor` exits 0; no dangling refs.

[x] T-016-A08

---

## rc-1 — Ship trio + CLOSURE

### T-016-R01 — qa-engineer full-suite review

- **Owner:** qa-engineer
- **Write set:** `.dadaia/handoff/` (APPROVED handoff)
- **Precondition:** all alpha tasks `[x]`
- **Work:** Full qa-engineer review of the complete release. APPROVE verdict authorizes commit.

[ ] T-016-R01

### T-016-R02 — security-reviewer review

- **Owner:** security-reviewer
- **Write set:** `.dadaia/handoff/` (APPROVED handoff)
- **Precondition:** T-016-R01 APPROVED
- **Work:** Security review. APPROVE verdict authorizes push.

[ ] T-016-R02

### T-016-R03 — code-reviewer review

- **Owner:** code-reviewer
- **Write set:** `.dadaia/handoff/` (APPROVED handoff)
- **Precondition:** T-016-R02 APPROVED
- **Work:** Code review. APPROVE verdict authorizes PR merge.

[ ] T-016-R03

### T-016-R04 — CLOSURE and memory update

- **Owner:** product-engineer
- **Write set:** `specs/releases/0.1.6/CLOSURE.md`, `specs/memory/**`
- **Precondition:** T-016-R03 APPROVED; all tasks `[x]`
- **Work:** Write CLOSURE.md per `dadaia-release-closure` template. Update memory atoms
  listed in SPEC §8. Update ACTIVE.md phase to ARCHIVED.

[ ] T-016-R04
