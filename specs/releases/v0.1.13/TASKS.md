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
