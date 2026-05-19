# Backlog Draft SPEC — codex-design-frontend-projection-pilot-v1

**Status:** Draft
**Backlog candidate:** codex-design-frontend-projection-pilot-v1
**Parent candidate:** codex-agent-orchestration-parity-v1
**Owner:** product-engineer
**Created:** 2026-05-19

> This is a backlog discovery draft, not an active release artifact. It does not authorize
> PLAN.md, TASKS.md, implementation, or production edits. Promotion requires the normal
> SDD flow under `specs/releases/<release-id>/` with `**Status:** Aprovado`.

---

## 1. Context

The workspace wants Codex to help `design-specialist` and `frontend-engineer` use modern
Codex plugins/skills without regressing Claude Code. Current architecture is only partially
ready:

- Shared skills under `dadaia_workspace/public/skills/` are projected to both
  `.claude/skills/` and `.agents/skills/`, so they are not Codex-only.
- `public/plugins/` is staged and projected to OpenCode, but `_install_codex()` does not
  install plugins for Codex.
- Codex config currently exposes shared skills through `[skills] paths = [".agents/skills"]`.
- `design-specialist` already references a missing `frontend-design` skill.
- `frontend-engineer` declares handoff-schema outputs but does not list
  `dadaia-handoff-emitter`.

This pilot is a slice of `codex-agent-orchestration-parity-v1`. It must prove the
runtime-scoped asset boundary before the wider Codex parity release adopts it.

---

## 2. Functional Requirements

### FR1 — Runtime-scoped Codex asset boundary

Define and implement an ADR-backed source layout for Codex-exclusive plugin/skill adapters,
preferably `dadaia_workspace/public/runtime/codex/**`.

Required decisions:

- Codex-only assets must not be authored in `public/skills/` unless intentionally shared.
- Codex-only plugins must not be authored in `public/plugins/` unless OpenCode projection is
  explicitly intended.
- `dadaia public stage`, `install --target codex`, and `doctor` must understand the chosen
  path and report drift/missing/stale projection honestly.
- Claude and OpenCode projections must remain byte-identical when only Codex-only assets are
  added.

### FR2 — Fix shared design/frontend skill baseline

Create or normalize shared skills that are useful to both Claude and Codex:

- `frontend-design` — owned by `design-specialist`; contains workspace surfaces, token
  naming, typography scale, spacing system, component handoff conventions.
- `design-report-quality-gate` — validates design report completeness without giving
  `design-specialist` Bash/test execution.
- `design-reference-research` — centralizes reference whitelist and citation protocol.
- `frontend-implementation-quality` — objective frontend implementation gates: TDD,
  TypeScript strictness, component tests, accessibility checks, responsive breakpoints,
  performance budget, OWASP frontend checklist.

Update agent references only where they preserve ownership:

- `design-specialist` may use `frontend-design`, `ux-ui-review`,
  `design-reference-research`, `design-report-quality-gate`, and
  `dadaia-handoff-emitter`.
- `frontend-engineer` may use `frontend-implementation-quality` and
  `dadaia-handoff-emitter`.
- `frontend-engineer` must not receive UX/UI judgment ownership.

### FR3 — Codex UX/frontend adapters

After FR1 chooses a runtime-scoped format, define Codex-specific adapters for:

- `design-specialist`: read-only context injection for active context, surface, latest QA
  screenshot report, latest design report, and approved reference whitelist.
- `frontend-engineer`: implementation helper context for latest design report, active
  task, dev-server registry state, and objective frontend quality gates.

Adapters must not duplicate the canonical personas. They enrich Codex runtime behavior while
the canonical agent Markdown remains the source of truth.

### FR4 — Preserve agent boundaries

The pilot must harden, not weaken, the existing design/frontend split:

- `design-specialist` does not write HTML/CSS/JS/TS/TSX, does not use Bash/Edit, does not
  run Playwright, and does not generate raster assets.
- `design-specialist` may write reports and textual design assets only. If `specs/assets/**`
  remains in its allowlist, accepted extensions must be limited to textual artifacts such as
  `.md`, `.html`, `.json`, and `.txt`.
- `frontend-engineer` implements browser-facing code and objective quality gates, but asks
  for a design report when visual direction is missing.
- E2E and Playwright evidence remain owned by `qa-engineer`.

---

## 3. Non-Functional Requirements

- **NFR1 — Null Claude regression:** `_install_claude()`, `.claude/agents/**`,
  `.claude/skills/**`, `.claude/workflows/**`, and `ClaudeAgentDispatcher` behavior remain
  unchanged unless a shared skill is intentionally added and accepted in the SPEC.
- **NFR2 — Null OpenCode regression:** Codex-only plugin/skill adapters must not leak into
  `.opencode/**`.
- **NFR3 — Honest doctor:** `dadaia public doctor` must report Codex-only assets as
  `[ok]`, `[missing]`, `[drift]`, or `[not-applicable]` according to real runtime support.
- **NFR4 — No fake plugin support:** Do not project `.codex/plugins/**` unless the SPEC
  verifies that the Codex runtime consumes that destination or defines the required local
  marketplace/config contract.
- **NFR5 — Reusable slice:** any renderer/adapter added here must be reusable by
  `codex-agent-orchestration-parity-v1`.

---

## 4. Out of Scope

- Codex workflow runtime or dispatcher parity.
- Native `.codex/agents/*.toml` for all 16 agents, except minimal test fixtures needed for
  this pilot.
- Changing canonical `project-manager` / `project-auditor` Agent-tool wording.
- Touching active `panel-r4-v1` or draft `panel-r5-v1` scope.
- Giving `frontend-engineer` design authority.
- Giving `design-specialist` Playwright, image generation, Bash, Edit, or production-code
  permissions.

---

## 5. Acceptance Criteria

- **C1:** `test_agent_skill_references_exist` fails when any `skills:` frontmatter entry
  references a missing `dadaia_workspace/public/skills/<name>/SKILL.md`.
- **C2:** `frontend-design/SKILL.md` exists and is referenced by `design-specialist`.
- **C3:** `frontend-engineer` frontmatter includes `dadaia-handoff-emitter` and
  `frontend-implementation-quality`.
- **C4:** boundary tests assert `design-specialist` has no `Edit`, no `Bash`, no Playwright
  or image-generation tools, and no non-text asset write permission.
- **C5:** boundary tests assert `frontend-engineer` has no `ux-ui-review`, no Playwright MCP
  ownership, no E2E ownership, and no specs ownership.
- **C6:** `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  reports no drift for shared assets.
- **C7:** adding a Codex-only adapter changes only `.codex/**` and the intended generated
  manifest/staging entries; `.claude/**` and `.opencode/**` are byte-identical before/after.
- **C8:** `doctor` detects a missing Codex-only adapter, a stale Codex-only adapter, and an
  accidental OpenCode leak.
- **C9:** any `.codex/config.toml` changes parse with `tomllib` and preserve shared
  `[skills] paths` behavior or document the ADR-approved replacement.
- **C10:** the pilot SPEC names the exact external Codex plugin/skill bundle choices for
  `design-specialist` and `frontend-engineer` before implementation.

---

## 6. Candidate Plugin/Skill Distribution

### design-specialist

Recommended shared skills:

- `frontend-design`
- `ux-ui-review`
- `design-reference-research`
- `design-report-quality-gate`
- `dadaia-handoff-emitter`

Recommended Codex-only adapter/plugin candidates, pending FR1 ADR:

- Figma read-only/context adapter for design systems, Code Connect context, and design
  parity review.
- Design context injection adapter similar in spirit to `ctx-inject.ts`, but read-only and
  scoped to latest QA/design reports.

Rejected for this agent:

- Playwright/browser capture.
- Image generation/raster creation.
- Production code editing.

### frontend-engineer

Recommended shared skills:

- `dadaia-workspace-spec-navigator`
- `dadaia-task-manager`
- `dev-server-registry`
- `frontend-implementation-quality`
- `dadaia-handoff-emitter`

Recommended Codex-only adapter/plugin candidates, pending FR1 ADR:

- Build Web Apps / frontend implementation adapter for component implementation and visual
  QA prompts, limited to objective implementation gates.
- React best-practices adapter when a repo is React/Next.
- shadcn adapter only when `components.json` or equivalent project evidence exists.
- Figma consumer adapter only to read handoff/design-system context, not to decide design.
- Expo adapter only for React Native/Expo repos.

Rejected for this agent:

- UX/UI ownership.
- E2E ownership.
- Specs ownership.

---

## 7. Required ADRs Before PLAN

- **ADR-CX-001:** Runtime-scoped public asset layout (`public/runtime/<runtime>/**` or
  accepted alternative).
- **ADR-CX-002:** Codex plugin/skill projection format and runtime-consumption proof.
- **ADR-CX-003:** Shared skill vs Codex-only adapter classification rules.
- **ADR-CX-004:** Null-regression methodology for Claude/OpenCode projections.
- **ADR-CX-005:** UX/frontend role boundary hardening.

---

## 8. Discovery Inputs

- Product-engineer consultation: pilot should be a child of
  `codex-agent-orchestration-parity-v1`, not a competing release.
- Software-architect consultation: runtime-scoped assets are required; plugin projection must
  not repeat the old `.codex/agents/` problem of projecting files the runtime does not read.
- Design-specialist consultation: fix `frontend-design`, keep design no-code/no-raster, and
  prefer report/reference skills over browser/image plugins.
- Frontend-engineer consultation: add handoff emitter, add objective implementation-quality
  skill, keep Playwright/E2E with QA.
