# Backlog Draft SPEC — codex-design-frontend-projection-pilot-v1

**Status:** Aprovado
**Backlog candidate:** codex-design-frontend-projection-pilot-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**ADRs fechados:** 2026-05-20 (grill-me session)

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
- `public/plugins/` is staged and projected to OpenCode only; `_install_codex()` does not
  install plugins for Codex and no `.codex/plugins/` directory exists — Codex-only assets
  must use a dedicated source path (ADR-CX-001: `public/runtime/codex/`).
- Codex config currently exposes shared skills through `[skills] paths = [".agents/skills"]`.
- `design-specialist` frontmatter lists only `dadaia-handoff-emitter`; skills
  `frontend-design`, `ux-ui-review`, `design-reference-research`, `design-report-quality-gate`
  must be created and added (ADR-CX-005).
- `frontend-engineer` frontmatter is missing `dadaia-handoff-emitter` and
  `frontend-implementation-quality` (ADR-CX-005).

This is a standalone release focused on shared skills creation, agent boundary hardening,
and establishing the Codex-only asset boundary. `codex-agent-orchestration-parity-v1` is
closed and archived; this release does not depend on it.

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
- Native `.codex/agents/*.toml` for all 20 agents (20 already exist from
  `codex-agent-orchestration-parity-v1`); this release does not add new agent TOMls.
- Changing canonical `project-manager` / `project-auditor` Agent-tool wording.
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
- **C10:** the pilot SPEC names the exact Codex-only adapter candidates for
  `design-specialist` and `frontend-engineer`, sourced from `public/runtime/codex/`
  (ADR-CX-001), before implementation begins.

---

## 6. Candidate Plugin/Skill Distribution

### design-specialist

Approved shared skills (ADR-CX-005):

- `frontend-design`
- `ux-ui-review`
- `design-reference-research`
- `design-report-quality-gate`
- `dadaia-handoff-emitter`

Codex-only adapter candidates (source: `public/runtime/codex/` per ADR-CX-001):

- Design context injection adapter scoped to latest QA/design reports (read-only).
- Figma read-only context adapter (deferred to follow-up; not in this pilot's scope).

Rejected for this agent:

- Playwright/browser capture.
- Image generation/raster creation.
- Production code editing.

### frontend-engineer

Approved shared skills (ADR-CX-005):

- `dadaia-workspace-spec-navigator`
- `dadaia-task-manager`
- `dev-server-registry`
- `frontend-implementation-quality`
- `dadaia-handoff-emitter`

Codex-only adapter candidates (source: `public/runtime/codex/` per ADR-CX-001):

- Frontend implementation context adapter for latest design report, active task, and
  dev-server registry state (read-only context injection).
- React/shadcn/Expo adapters deferred — conditional on repo evidence; not in this pilot.

Rejected for this agent:

- UX/UI ownership.
- E2E ownership.
- Specs ownership.

---

## 7. ADRs — Fechados em 2026-05-20 (grill-me session)

- **ADR-CX-001 ✅:** Codex-only assets vivem em `dadaia_workspace/public/runtime/codex/`.
  `_install_codex()` lê de lá; shared assets continuam em `public/skills/`.
- **ADR-CX-002 ✅:** Sem plugins nativos Codex. Codex consome apenas `[skills] paths =
  [".agents/skills"]`. Projetar `.codex/plugins/` viola NFR4 — não há evidência de consumo
  pelo runtime. (Respondido via inspeção: nenhum `.codex/plugins/` existe.)
- **ADR-CX-003 ✅:** Shared em `public/skills/<name>/`; adapter Codex-only separado em
  `public/runtime/codex/<name>/`. Sem overrides dentro do shared. Doctor verifica que
  `runtime/codex/` nunca vaza para `.claude/` ou `.opencode/`.
- **ADR-CX-004 ✅:** Null-regression via SHA snapshot pytest. Fixture calcula hash de
  `.claude/**` e `.opencode/**` antes e depois de `install --target codex`; diferença = falha.
- **ADR-CX-005 ✅:** Listas exatas de skills aprovadas (ver §6). Tools não mudam em nenhum
  dos dois agentes.

---

## 8. Discovery Inputs

- Software-architect consultation: runtime-scoped assets are required; plugin projection must
  not repeat the old `.codex/agents/` problem of projecting files the runtime does not read.
- Design-specialist consultation: fix `frontend-design`, keep design no-code/no-raster, and
  prefer report/reference skills over browser/image plugins.
- Frontend-engineer consultation: add handoff emitter, add objective implementation-quality
  skill, keep Playwright/E2E with QA.
- Grill-me session 2026-05-20: all 5 ADRs closed (see §7). Release is standalone — no
  parent dependency on `codex-agent-orchestration-parity-v1` (closed and archived).
