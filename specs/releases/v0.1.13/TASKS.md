# TASKS: v0.1.13 — Codex Entity Parity + Academy Course

**Status:** Aprovado
**Release ID:** v0.1.13
**Owner:** product-engineer
**Created:** 2026-06-11

Markers: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.

---

### [x] T-013-01 — Rewrite the English Codex Academy module
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/features/academy/knowledge_basis/07_codex/**`
- **Acceptance:** module 7 contains a full English course with README, five
  lessons, exercises, example, and references; content covers every official Codex
  primitive requested by the operator and maps them to dadaia-workspace.

### [x] T-013-02 — Refine Codex harness skills
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`,
  `dadaia_workspace/public/skills/harness-primitives/SKILL.md`
- **Acceptance:** skills distinguish AGENTS.md, skills, plugins, hooks, Rules,
  config, custom agents, and explicit subagent spawning; instructions are precise
  enough for `ai-engineer` to audit Codex surfaces.

### [x] T-013-03 — Fix generated Codex Rules shape
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`,
  projection/doctor tests
- **Acceptance:** generated `.codex/rules/dadaia-command-policy.rules` uses
  documented `prefix_rule(...)` declarations; no `command_allowed`; focused tests
  pass; bug `codex-rules-generated-with-undocumented-command-allowed` is covered.

### [x] T-013-04 — Fix Codex custom-agent sandbox boundaries
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`,
  `dadaia_workspace/infrastructure/codex_doctor.py`, projection/doctor tests
- **Acceptance:** evidence-only reviewers/auditors project as read-only where their
  role contract says they do not edit; stale `security-engineer` boundary is
  removed or corrected; bug `codex-reviewer-agents-projected-workspace-write` is
  covered.

### [x] T-013-05 — Make Codex dispatcher/subagent behavior explicit
- **Owner:** ai-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_agent_dispatcher.py`,
  `dadaia_workspace/public/workflows/*.workflow.md`,
  `dadaia_workspace/public/agents/project-manager.md`,
  `dadaia_workspace/public/agents/project-auditor.md`, focused tests/docs
- **Acceptance:** code and projected guidance do not imply automatic Codex
  workflow execution; they state Codex requires explicit subagent delegation and
  that workflow files are reference/context unless a runtime dispatcher actually
  spawns agents.

### [-] T-013-07 — Make the panel Academy tab browse knowledge_basis modules and lessons
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/features/panel/views/academy.py`,
  `dadaia_workspace/features/panel/views/api.py` (academy view only),
  `dadaia_workspace/features/panel/views/assets/js/academy.js`,
  `dadaia_workspace/features/panel/views/assets/css/academy.py`,
  `dadaia_workspace/features/panel/handler.py` (new academy lesson route rows only),
  `dadaia_workspace/features/academy/service.py`,
  `dadaia_workspace/container.py` (academy lesson view wiring only), tests
- **Acceptance:** `/api/academy` lists ALL knowledge_basis modules with titles and
  lesson counts; clicking a module expands its lessons; a new read-only
  path-traversal-guarded `GET /academy/<module>/<lesson>` route renders the lesson
  Markdown in the panel via `views/_md_render.py`. Covers bug
  `academy-tab-cannot-browse-knowledge-basis-modules`. Unit + integration tests incl.
  traversal negatives; ruff + mypy --strict clean.

### [x] T-013-06 — Project and verify Codex parity
- **Owner:** software-engineer
- **Write set:** generated projection files via `dadaia public stage/install`,
  test snapshots if needed
- **Acceptance:** focused tests pass; `dadaia public doctor` exits 0; Codex Rules
  validation is attempted; Academy module 7 is visible via `dadaia academy modules`
  and panel Academy wiring remains intact.

---

## alpha-2 — Codex Runtime Fidelity residuals (2026-06-11)

Order: T-013-08 runs FIRST — its verified facts gate the final shape of
T-013-09/T-013-10 (matcher form, rules semantics). End-of-alpha-2 review:
qa-engineer only.

### [-] T-013-08 — WS-CDX-VERIFY: live Codex contract harness + fact recording
- **Owner:** software-engineer (harness + matcher alignment); ai-engineer
  (skill/academy fact recording — disjoint write set)
- **Write set:** harness script + focused tests under `tests/` (throwaway
  workspaces generated only under `.dadaia/tmp/`),
  `dadaia_workspace/infrastructure/runtime_config.py` (PreToolUse matcher, only if
  the live run shows the anchored form misbehaves),
  `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`,
  `dadaia_workspace/features/academy/knowledge_basis/07_codex/**`
- **Acceptance:** scripted, repeatable harness drives `codex exec` in a trusted
  throwaway workspace under `.dadaia/tmp/`; marker files prove SessionStart /
  UserPromptSubmit / PreToolUse / PostToolUse execution; an attempted FROZEN
  `specs/_archive/` write via `apply_patch` is demonstrably blocked (or the gate's
  Codex story is rewritten honestly as discipline-only); the 3 F-1 contract points
  (anchored-regex matcher form, `{"decision":"block"}` stdout envelope vs
  exit-code semantics, shell-exec of env-prefixed commands) plus
  `approved_commands` (F-6) and `[agents."<n>"] config_file` (F-8) are resolved to
  facts recorded in the `ai-harness-codex` skill and academy 07; matcher aligned
  with the documented form if the live run shows the anchored form misbehaves.
  Closes the audit's F-1/F-6/F-8 UNVERIFIED cells.

### [ ] T-013-09 — Description-field transform + D-CX-4 tool-name patterns
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/install_helpers.py`
  (`install_codex_agents`),
  `dadaia_workspace/infrastructure/runtime_transforms/codex.py`,
  `dadaia_workspace/infrastructure/codex_doctor.py` (D-CX-4), focused tests
- **Acceptance:** agent TOML `description` runs through the same replacement
  table as the body; D-CX-4 flags Claude tool names (`Agent tool`, `Task tool`)
  in Codex artifacts; post-install `.codex/agents/project-manager.toml`
  description carries no Claude-ism; unit tests cover transform + doctor pattern.
  Closes bug `codex-agent-description-claude-ism-leak`.

### [ ] T-013-10 — Venv-path prefix rules + real-form `match=` proofs
- **Owner:** software-engineer
- **Write set:**
  `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py`
  (rules generation), `dadaia_workspace/infrastructure/codex_doctor.py`
  (D-CX-8 if extended), focused tests
- **Acceptance:** generated `.codex/rules/dadaia-command-policy.rules` patterns
  match the mandated invocation form (`.dadaia/.venv/bin/dadaia public install`,
  `.dadaia/.venv/bin/dadaia context dead`), proven by `match=` examples using the
  real form; final pattern semantics per T-013-08's verified facts; tests assert
  the real invocation form matches and bare-name-only patterns are gone. Closes
  bug `codex-rules-dadaia-prefix-never-matches-venv-invocation`.

### [ ] T-013-11 — Delete/invert the stale T-35 roster lint
- **Owner:** software-engineer
- **Write set:** `dadaia_workspace/infrastructure/codex_doctor.py`
  (`lint_legacy_software_engineer`),
  `dadaia_workspace/infrastructure/runtime_transforms/codex_assets.py` (lint
  regex), focused tests
- **Acceptance:** the lint no longer flags `subagent_type: software-engineer`
  (canonical implementer, constitution §14); it is deleted or inverted to flag
  the dead `software-engineer-python|node` names; tests cover both the canonical
  name passing and (if inverted) dead names failing. Closes bug
  `stale-legacy-software-engineer-lint-inverts-roster`.

### [ ] T-013-12 — Codex-native model strategy (per-runtime tier rendering)
- **Owner:** software-engineer (rendering/registry code); ai-engineer (persona
  source prose — disjoint write set)
- **Write set:** `dadaia_workspace/infrastructure/runtime_transforms/codex.py` +
  `model_mapping.py`, `dadaia_workspace/core/model_registry.py` (per-runtime tier
  view), `dadaia_workspace/infrastructure/codex_doctor.py` (D-CX-4 tier-name
  patterns), `dadaia_workspace/public/agents/ai-engineer.md` (registry-tier prose
  — ai-engineer), focused tests
- **Acceptance:** Codex persona model guidance is rendered per-runtime instead of
  MODEL_MAP prose substitution; `model_reasoning_effort` is a first-class tiering
  axis in the rendered table; rendering fails loudly when a mapping collapses two
  tiers into one id (`deep`/`dispatch` → `gpt-5.5` today); no Opus/Sonnet/Haiku
  prose survives in any Codex-projected persona body; D-CX-4 flags Anthropic tier
  names in Codex artifacts; tests cover rendering, collapse failure, and doctor
  pattern. Closes bug `codex-personas-claude-model-tiering-leak`.
