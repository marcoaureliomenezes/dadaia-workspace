# Spec: Release — agents-r1-v1

> **Status:** Aprovado
> **Approved:** 2026-05-18
> **Approved-by:** operator (design pre-approved via `~/.claude/plans/parsed-sniffing-teapot.md`)
> **Release ID:** agents-r1-v1
> **Owner:** product-engineer
> **Created:** 2026-05-18
> **Phase:** SPEC
> **Stakeholders:** operator (decision authority), product-engineer (curator + leaf author post-release), software-architect (review of skill content), qa-engineer (panel topology tests)
> **Branch:** `release/agents-r1-v1` (cut from `main` at `427ab86`, post panel-r3-v1 archive)
> **Discovery inputs:**
> - Operator-approved plan: `~/.claude/plans/parsed-sniffing-teapot.md`
> - Atomic memory (post panel-r3-v1 CLOSURE): `specs/memory/architecture.html`, `specs/memory/product/index.html`, `specs/memory/product/panel.html`
> - Constitution: `specs/constitution.md` Pilar 2 (orquestração multi-agente)

---

## 1. Objective

Refactor the dadaia-workspace agent topology from a flat 10-agent / 12-workflow set with a
single overloaded `product-engineer` orchestrator into an explicit **3-tier dispatcher
architecture**:

- **Tier 1 — Orchestrators (2 agents with `Agent` tool):** `project-manager` (intake +
  workflow dispatch), `project-auditor` (drift detection + audit dispatch).
- **Tier 2 — Curator (1 agent, no `Agent` tool):** `product-engineer` becomes a leaf
  SPEC/PLAN/TASKS/CLOSURE author and the exclusive memory guardian.
- **Tier 3 — Leaf specialists (13 agents, no `Agent` tool):** existing implementers
  (software-engineer, backend-engineer, frontend-engineer, qa-engineer, software-architect,
  devops-engineer, game-developer, game-designer, game-tester) plus 4 new leaf specialists
  (`code-reviewer`, `researcher`, `security-reviewer`, `design-specialist`).

After this release the workspace ships **16 agents** and **15 workflows**, with three new
audit/review workflows and PE → PM orchestrator swaps in 6 existing workflows. The panel
must continue to render correctly; full pytest + `dadaia specs doctor` + `dadaia public doctor`
must remain green; no production source under `dadaia_workspace/` (beyond reader + tests)
is touched.

---

## 2. Problem statement

Two research reports (P0/P1 design problems, see plan §Context) and the operator's own
diagnosis converge on the same set of pains in the current 10-agent topology:

1. **product-engineer is overloaded.** Today PE owns spec writing AND discovery interview
   AND parallel specialist dispatch AND report synthesis AND memory atomicity. This bundles
   four distinct responsibilities into a single agent and makes PE's prompt unmanageable
   (~484 lines). It also blocks PE from being safely invoked as a leaf when another
   orchestrator needs a SPEC written.
2. **frontend-engineer is overloaded.** FE today owns implementation AND UX/UI judgment
   (the "anti-AI-slop aesthetics" section). Operator wants design decoupled from
   implementation so visual exploration is not coupled to FE workload.
3. **Workflows are confusing and hard to reuse.** The operator cannot tell workflows apart
   when picking one. Root cause: PE monopolizes orchestration stages and so most workflows
   look like minor variants of `spec-refinement`.
4. **Missing roles.** Code review (P0), security audit (P1), deep research with citations
   (P1), drift detection (audit), and UX/UI specialization are all done ad-hoc today by
   the wrong agents.
5. **Silent failure bug (P0).** Six agents declare the `Agent` tool but sub-agents
   cannot spawn sub-agents in the Claude harness — calls silently fail when those agents
   run as workflow stages. Only top-level orchestrators should declare `Agent`.

---

## 3. Goals

- G1. Introduce 6 new agents covering the missing roles: `project-manager`,
  `project-auditor`, `code-reviewer`, `researcher`, `security-reviewer`, `design-specialist`.
- G2. Slim `product-engineer` to pure SPEC/PLAN/TASKS/CLOSURE author + memory guardian
  (lines target: ≤ 280).
- G3. Slim `frontend-engineer` to implementation-only (lines target: ≤ 230).
- G4. Strip the `Agent` tool from 8 leaf implementers (SE/BE/FE/QA/architect/devops + 3 game).
- G5. Ship 5 new skills: `project-orchestration`, `architecture-code-review`,
  `security-audit-protocol`, `drift-detection`, `ux-ui-review`.
- G6. Refactor 6 existing workflows to swap PE→PM orchestrator stages while keeping shape.
- G7. Ship 3 new workflows: `audit-cycle`, `code-review-fan-out`, `design-validation`.
- G8. Add 3 new scope rules and update 3 existing rules to reflect new topology.
- G9. Update `dadaia-grill-me` preamble: primary caller becomes `project-manager`.
- G10. Extend `dadaia_workspace/features/agents/reader.py` `_ALLOWED_FIELDS` with `paths`
  (declarative-only this release; enforcement deferred to `agents-r2-v1`).
- G11. Panel renders the 16-agent + 15-workflow topology without manual intervention
  (data-driven).
- G12. Memory atom `specs/memory/architecture.html` is updated in CLOSURE to reflect the
  new 3-tier topology.

## 4. Non-goals

- NG1. NOT modifying production source outside `dadaia_workspace/features/agents/reader.py`
  + test files. Service layer, container, infrastructure layer untouched.
- NG2. NOT promoting `dadaia-grill-me` to a sub-agent (deferred to `agents-r2-v1`).
- NG3. NOT enforcing the new `paths` field on agents — it's declarative-only this release.
- NG4. NOT changing the workflow schema (`when:` clause, conditional stages handled
  agent-side via skip-if-not-applicable).
- NG5. NOT introducing new runtime targets (Claude Code / Codex / OpenCode parity rules
  unchanged).
- NG6. NOT touching `specs/backlog/ideas.md` (operator working memory).
- NG7. NOT changing the gate `sdd-spec-gate.sh` v3 semantics.

---

## 5. New agents — frontmatter sketches and hard rules

All 6 new agents live in `dadaia_workspace/public/agents/<name>.md` and are projected by
`dadaia public install --target all`. Reports for each agent land at
`.dadaia/reports/<context>/<agent>/<YYYY-MM-DDTHHMMSSZ>-<type>.html`. Every agent emits a
`<stem>.handoff.json` sidecar via skill `dadaia-handoff-emitter`. Description budget per
agent: ≤ 300 characters (Claude routing constraint).

### 5.1 project-manager (Opus 4.7) — orchestrator/maestro

- **Tools:** `Read, Glob, Grep, Bash, Write, Agent`.
- **Skills:** `dadaia-grill-me`, `dadaia-workspace-manager`, `dadaia-workspace-spec-navigator`,
  `dadaia-task-manager`, `project-orchestration`, `dadaia-handoff-emitter`.
- **Mission:** Receive operator demand → grill for clarity → categorise
  (feature / bug / audit / release / research / design / security) → pick workflow →
  dispatch agents. Mediates Decision Authority Matrix; escalates unresolvable conflicts.
- **Hard rules:** NEVER writes code, specs, memory, tests, or CI. Writes only to
  `.dadaia/reports/<ctx>/project-manager/*`.

### 5.2 code-reviewer (Sonnet 4.6) — PR/branch reviewer

- **Tools:** `Read, Bash, Glob, Grep, Write` (no `Agent`).
- **Skills:** `architect-code-audit`, `architect-design-patterns`, `architecture-code-review`.
- **Mission:** 6-axis review per PR/branch/SHA (architecture / patterns / tests / security
  smells / perf smells / dead code). Reads CI logs via `gh` CLI.
- **Output:** Review report with severity badges + recommendation (approve / request-changes / comment).
- **Hard rules:** NEVER edits code. NEVER approves a PR (recommendation only).

### 5.3 researcher (Sonnet 4.6) — read-only deep explorer

- **Tools:** `Read, Glob, Grep, WebFetch, WebSearch, Write` (no `Agent`).
- **Mission:** Scope → harvest → synthesize. Every claim cites `file:line` or URL. Web
  sources restricted to whitelist (official docs, GitHub, MDN, OWASP, RFC).
- **Output:** Research report with citations + open ends.
- **Hard rules:** NEVER speculates without citation. NEVER writes source files.

### 5.4 security-reviewer (Sonnet 4.6) — vulnerability auditor

- **Tools:** `Read, Bash, Glob, Grep, Write` (no `Agent`).
- **Skills:** `security-audit-protocol`.
- **Mission:** OWASP Top 10 scan, secret detection, dependency CVEs (`pip-audit`,
  `npm audit`, `go list`), IaC review.
- **Output:** One report per finding with CWE id, `file:line`, evidence (secrets redacted),
  fix recommendation.
- **Hard rules:** NEVER writes fixes. NEVER runs exploits. NEVER logs raw secret values.

### 5.5 project-auditor (Opus 4.7) — drift detector

- **Tools:** `Read, Bash, Glob, Grep, Write, Agent`.
- **Skills:** `architect-code-audit`, `dadaia-workspace-spec-reviewer`, `drift-detection`,
  `project-orchestration`.
- **Mission ladder:**
  - **PRIMARY:** drift between `specs/memory/*.html` (atomic memory) and actual code.
  - **SECONDARY:** dead/stale code, unreachable layers.
  - **TERTIARY:** spec consistency across releases.
- **Dispatches:** researcher, code-reviewer, security-reviewer, qa-engineer,
  design-specialist for evidence.
- **Output:** Audit report with 1–10 compliance score across 6 dimensions
  (arch / product / tech-stack / security / tests / design) + drift items + recommended
  actions.
- **Hard rules:** NEVER fixes drift. NEVER mutates specs.

### 5.6 design-specialist (Sonnet 4.6) — UX/UI specialist

- **Tools:** `Read, Glob, Grep, WebFetch, WebSearch, Write` (no `Agent`).
- **Skills:** `frontend-design` (existing plugin), `ux-ui-review`.
- **Mission:** Consume qa-engineer Playwright screenshots → reference search
  (Dribbble, Mobbin, Figma Community, Refactoring UI, Apple HIG, Material 3) → emit design
  spec (tokens / typography / spacing / motion / breakpoints / a11y) + ASCII sketches.
  Knows workspace surfaces: portfolio, dadaia-bots, dadaia-workspace panel.
- **Hard rules:** NEVER writes production HTML/CSS/JS/TSX. NEVER generates raster images
  (ASCII / Markdown sketches + reference URLs only).

---

## 6. Slim of existing agents

### 6.1 product-engineer — delta table

| Aspect | Before | After |
|---|---|---|
| Tools | `Read, Glob, Grep, Bash, Write, Edit, Agent` | `Read, Glob, Grep, Bash, Write, Edit` (`Agent` removed — PE is now leaf) |
| Description | "Guardian of SDD; orchestrates discovery, dispatches specialists, synthesises, writes SPEC/PLAN/TASKS/CLOSURE, owns memory." | "Spec author and memory guardian. Writes SPEC/PLAN/TASKS/CLOSURE for an active release; writes specs/memory/*.html only in CLOSURE phase. Invoked by project-manager when a spec is needed. NEVER dispatches other agents; NEVER implements code." (≤ 300 chars) |
| Body REMOVED | Discovery interview phase; parallel specialist dispatch logic; synthesis of specialist reports; wide grill-me orchestration | — |
| Body KEPT (verbatim) | SDD file hierarchy; memory atomicity contract; SPEC/PLAN/TASKS/CLOSURE templates; status gates | — |
| Body ADDED | — | `## Invocation contract` section: "project-manager invokes me when a spec needs writing. I receive `release_id` + `context` + optional `discovery_report`. I do NOT discover." + panel "Memories → Spec Context Projects" UI-rename note (does not affect canonical `specs/memory/` path nomenclature). |
| Line budget | ~484 | ≤ 280 |

### 6.2 frontend-engineer — delta table

| Aspect | Before | After |
|---|---|---|
| Tools | `Read, Glob, Grep, Bash, Write, Edit, Agent` | `Read, Glob, Grep, Bash, Write, Edit` (`Agent` removed) |
| Description | "Implements HTML/CSS/JS/TS/React. Owns UX/UI judgment + anti-AI-slop aesthetics." | "Implements HTML/CSS/JS/TS/React for browser surfaces. Pairs with qa-engineer (E2E). Receives design specs from design-specialist. NEVER owns UX/UI judgment — that is design-specialist." (≤ 300 chars) |
| Body REMOVED | `### Aesthetics — anti-AI-slop` section; `frontend-design` plugin-skill self-invocation paragraph | — |
| Body ADDED | — | `## Design handoff contract`: design-specialist owns visual decisions; FE reads latest design_report before implementing; STOPs and asks project-manager to dispatch design-specialist if none exists. |
| Line budget | ~305 | ≤ 230 |

### 6.3 Other implementers — single change

`software-engineer`, `backend-engineer`, `qa-engineer`, `software-architect`,
`devops-engineer`, `game-developer`, `game-designer`, `game-tester` each have **one
frontmatter change only**: remove `Agent` from `tools`. No body changes.

---

## 7. Workflow refactor — 12 existing + 3 new

### 7.1 Existing workflows — PE → PM stage swap

| Workflow | Stages changing | Refactor |
|---|---|---|
| `spec-refinement` | discovery, synthesis | discovery → **PM** (runs grill-me); synthesis → **PM** (assembles reports) + NEW sub-stage `spec_write` for **PE** as leaf. |
| `game-spec-definition` | discovery, synthesis | Same pattern as spec-refinement. |
| `cross-cutting-feature` | discovery | discovery → **PM**; contract_review unchanged. |
| `onboarding-new-repo` | synthesis | synthesis → **PM** + NEW sub-stage `spec_write` for **PE**. |
| `architecture-review` | task_conversion | Split: **PM** filters/prioritizes; **PE** converts to TASKS.md. |
| `hotfix-release` | promote_to_release | **PM** decides patch number; dispatches **PE** for SPEC entry. close_with_smoke remains qa-engineer; CLOSURE.md remains PE. |
| `tdd-cycle` | — | unchanged. |
| `bug-fix-fastlane` | — | unchanged. |
| `game-bugfix` | — | unchanged. |
| `security-patch` | — | unchanged. |
| `game-dev-cycle` | — | unchanged. |
| `deploy-validation-only` | — | unchanged. |

Schema: zero change. Only `agent:` values change, plus a few `expected_output.path`
substitutions to PM-owned paths.

### 7.2 New workflows

| Workflow | Shape |
|---|---|
| `audit-cycle` | project-auditor orchestrates 4-way parallel: code-reviewer + security-reviewer + researcher + qa-engineer → synthesis with compliance score. Triggered manually. |
| `code-review-fan-out` | Per-PR parallel: code-reviewer + security-reviewer + (conditional) design-specialist → PM consolidates verdict. Conditional handled agent-side (skip-if-not-applicable). |
| `design-validation` | qa-engineer Playwright captures → design-specialist UX review. |

---

## 8. Skills + rules + reader changes

### 8.1 Five new skills

| Skill | Owner agents | Content sections |
|---|---|---|
| `project-orchestration` | project-manager, project-auditor | Agent + workflow inventory matrices, dispatch protocol, mediation, escalation, forbidden actions. |
| `architecture-code-review` | code-reviewer | 6-axis checklist, OOP/SOLID, design-pattern misuse, complexity heuristics, output template. |
| `security-audit-protocol` | security-reviewer | OWASP 2025, dep-scan workflow, secrets scan, IaC review, STRIDE template, severity matrix. |
| `drift-detection` | project-auditor | Memory↔implementation diff protocol, dead-code detection, 1–10 scoring rubric, dadaia CLI commands. |
| `ux-ui-review` | design-specialist | WCAG 2.2 AA checklist, visual hierarchy, design-system conformance, reference-search whitelist, output template. |

### 8.2 Updated skill

- `dadaia-grill-me` — change preamble: primary caller becomes project-manager during
  intake; product-engineer may still invoke when consulted as leaf for a spec-level
  question. Not promoted to sub-agent this release.

### 8.3 Three new rules

| Rule file | Content summary |
|---|---|
| `project-manager-scope.md` | PM coordinates only. Writes to `.dadaia/reports/<ctx>/project-manager/*` only. NEVER edits `specs/`, source, tests, CI, projections. |
| `project-auditor-scope.md` | Auditor only reads + writes audit reports. Forbidden from editing memory, specs, source, CI. Output must include compliance score 1–10. |
| `design-specialist-scope.md` | Design-specialist writes only to `.dadaia/reports/<ctx>/design-specialist/*` + design assets under `specs/assets/<scope>/*`. Forbidden from editing FE code. |

### 8.4 Updates to existing rules

- `dadaia-workspace-dev-guardrail.md`: append a note that PM + auditor are not allowed to
  run `dadaia public install --force`.
- `game-agents-coordination.md`: Decision Authority Matrix row "Escopo, prioridades, SPEC"
  → primary becomes **project-manager**; PE remains tie-breaker for memory atomicity only.
- `game-developer-scope.md`: add PM, auditor, code-reviewer, security-reviewer, researcher,
  design-specialist to the "Proibido para Outros Agentes" list for `repos/tauan-games/`.

### 8.5 Reader change

`dadaia_workspace/features/agents/reader.py`:
- Extend `_ALLOWED_FIELDS` to include `paths`.
- Map to optional `paths: dict[str, list[str]] | None` on `AgentDTO`.
- Declarative-only — no gate enforcement this release.

---

## 9. Tests touched

| Test file | Change |
|---|---|
| `tests/unit/features/agents/test_reader.py` | Add `test_paths_field_loaded_when_present`. |
| `tests/unit/features/panel/test_api_agents.py` | Add presence assertions for the 6 new agents in `/api/agents` LIST. |
| `tests/unit/features/panel/test_api_agent_prompt.py` | Add cases for 6 new agent prompts; verify path-traversal guard. |
| `tests/unit/features/panel/test_views_agents.py` | Extend if card count is asserted. |
| `tests/unit/features/panel/test_agents_expand_pr3_11.py` | Add expansion case for project-manager. |
| `tests/unit/features/panel/test_api_workflows_list.py` | Add audit-cycle, code-review-fan-out, design-validation to LIST snapshot. |
| `tests/unit/features/panel/test_api_workflows_detail.py` | Add DETAIL case for audit-cycle (good 4-way parallel DAG coverage). |
| `tests/unit/features/panel/test_views_workflows.py` | Extend card-grid count. |
| `tests/unit/features/workflows/test_dag.py` | Add fixtures for audit-cycle + design-validation. |
| `tests/unit/test_workflow_schema.py` | Add the 3 new workflow YAMLs to the iteration. |

Data-driven code (no change needed): `dadaia_workspace/features/agents/__init__.py`,
`dadaia_workspace/features/workflows/{service,dag}.py`,
`dadaia_workspace/features/panel/views/{agents,workflows}.js`.

---

## 10. Phase plan (P0..P8)

| Phase | Scope | Parallelism |
|---|---|---|
| **P0** | Close `panel-r3-v1` (PR3-18..23) under previous topology. | — (already done at HEAD `427ab86`) |
| **P1** | Foundations: 3 new rules, 3 updated rule files, `dadaia-grill-me` preamble update. Stage + install + doctor. | rule edits parallel-safe (disjoint files) |
| **P2** | 6 new agent files + slim PE/FE + strip `Agent` from 8 leaf agents. Stage + install + doctor. | 6 new agent files parallel-safe; existing agent edits parallel-safe |
| **P3** | 5 new skill files. Stage + install + doctor. | 5 skill files parallel-safe |
| **P4** | 6 existing workflow edits (PE → PM swap). Stage + install + doctor. | per-workflow parallel-safe |
| **P5** | 3 new workflow files. Stage + install + doctor. | 3 new workflows parallel-safe |
| **P6** | Reader `paths` field + 10 panel test updates. Full pytest. | reader + tests sequential; tests across files parallel-safe |
| **P7** | Consumer-repo audit: `dadaia public doctor` in each consumer repo. | per-consumer parallel-safe |
| **P8** | CLOSURE: PE writes CLOSURE.md; updates `specs/memory/architecture.html` (new 16-agent topology); archives. | sequential |

---

## 11. Memory updates at CLOSURE

- `specs/memory/architecture.html` — section "Camadas" gains a note about the 3-tier
  agent topology (Tier 1 orchestrators with `Agent` tool / Tier 2 curator / Tier 3 leaf
  specialists); section "Runtime state" notes that `.dadaia/reports/<ctx>/<agent>/` now
  includes 6 new directory names.
- `specs/memory/product/index.html` — catalog item `agent-orchestration` description
  updated to reflect 16 agents + 15 workflows + 3-tier topology.
- `specs/memory/product/agent-orchestration.html` — atomic re-render reflecting new
  topology (purpose, flow, trigger, differential, runtime state, dependencies).
- `specs/memory/tech-stack.html` — **no change**: release does not touch dependencies.

---

## 12. Critérios de aceite

The release is considered complete only when ALL of the following hold:

- C1. All 16 agent files exist in `dadaia_workspace/public/agents/` and load through
  `MarkdownAgentStore` without warning. `dadaia panel` shows 16 agent cards.
- C2. All 15 workflow files exist in `dadaia_workspace/public/workflows/` and load
  through `MarkdownWorkflowStore` without warning. `dadaia panel` shows 15 workflow cards.
- C3. Panel `/api/agents` LIST returns 16 entries; per-agent `/api/agents/<name>/prompt`
  returns 200 for each of the 6 new agents.
- C4. Panel `/api/workflows` LIST returns 15 entries; `/api/workflows/audit-cycle/detail`
  returns valid DAG SVG.
- C5. `Agent` tool present only on `project-manager` and `project-auditor`. Verified by
  grep of frontmatter `tools:` lines.
- C6. Full pytest green: `pytest -q tests/` from repo root.
- C7. `dadaia specs doctor` reports `[ok] N errors, 0 warnings` from repo root.
- C8. `dadaia public stage && dadaia public install --target all && dadaia public doctor`
  reports `[ok]` for every entry.
- C9. Consumer-repo `dadaia public doctor` reports `[ok]` in every consumer repo
  enumerated in P7.
- C10. CLOSURE.md present in `specs/releases/agents-r1-v1/CLOSURE.md` with valid
  Validation triples; `specs/memory/architecture.html` updated atomically (no changelog
  section).
- C11. Release directory has been `git mv`'d to `specs/_archive/releases/agents-r1-v1/`
  and `specs/releases/ACTIVE.md` no longer references it.

## 13. Definition of Done

DoD = C1 + C2 + C3 + C4 + C5 + C6 + C7 + C8 + C9 + C10 + C11, plus the operator's verbal
"OK" on the panel smoke (manual visual check of the 16-agent + 15-workflow grid).

---

## 14. Dependencies and risks

| Risk | Mitigation |
|---|---|
| Description routing budget overrun (16 × ~290 chars vs 1.5K ideal) | PM becomes primary entry point — operator addresses by name, sidestepping description routing for most calls. |
| PM `Agent` calls hitting sub-agent depth limits (PM → auditor → reviewer = 2 hops) | Verify two-hop pattern in harness during P2; if it fails, PM dispatches reviewers directly and auditor dispatches separately. |
| New skills referenced in agent frontmatter before authoring | Co-emit skill stubs in P2 (same commit as agents); fill full content in P3. |
| Hardcoded agent counts in test fixtures | P6 runs full pytest; breakage fixed there. |
| Consumer-repo projections out of sync after `dadaia public install` | P7 audit step; doctor in each consumer; recorded as CLOSURE evidence triple. |
| `code-review-fan-out` conditional `when:` clause unsupported by schema | Use agent-side skip-if-not-applicable — no schema change this release. |

## 15. Out of scope (explicit non-deliverables)

- Sub-agent promotion of `dadaia-grill-me` (deferred to `agents-r2-v1`).
- Enforcement of the agent `paths` field (declarative-only this release).
- Workflow schema `when:` clause (avoid; agent-side conditional only).
- Production source changes outside `dadaia_workspace/features/agents/reader.py` and the
  test files enumerated in §9.
- New runtime targets (Claude / Codex / OpenCode parity rules unchanged).
- Any edits to `specs/backlog/ideas.md`.
