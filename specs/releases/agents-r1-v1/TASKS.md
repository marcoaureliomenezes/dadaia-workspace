# Tasks: Release — agents-r1-v1

> **Status:** Aprovado
> **Approved:** 2026-05-18
> **Approved-by:** operator
> **Release ID:** agents-r1-v1
> **Owner:** product-engineer
> **Created:** 2026-05-18
> **Total tasks:** 34 (AGT-01 through AGT-34)
> **Companion docs:** SPEC.md, PLAN.md

Marks: `[ ]` OPEN, `[-]` IN PROGRESS, `[x]` DONE.
Maximum **one `[-]` per agent at a time**, except when this table marks `parallel-safe: yes`
(disjoint write sets per PLAN §4).

---

## Phase P1 — Foundations (rules + skill stubs + grill-me preamble)

### AGT-01 — Author rule `project-manager-scope.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.3
- **Depends on:** none
- **Parallel-safe with:** AGT-02, AGT-03, AGT-04, AGT-05, AGT-06
- **Files modified:**
  - `dadaia_workspace/public/rules/project-manager-scope.md` (new)
- **Mudanças:** PM coordinates only; writes to `.dadaia/reports/<ctx>/project-manager/*`; forbidden from `specs/`, source, tests, CI, projections. Use canonical rule frontmatter; body ≤ 60 lines.
- **Aceite:** File loads via `MarkdownAgentStore`-equivalent rule reader; `dadaia public stage && install && doctor` reports `[ok]`.

### AGT-02 — Author rule `project-auditor-scope.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.3
- **Depends on:** none
- **Parallel-safe with:** AGT-01, AGT-03, AGT-04, AGT-05, AGT-06
- **Files modified:**
  - `dadaia_workspace/public/rules/project-auditor-scope.md` (new)
- **Mudanças:** Auditor read-only + writes audit reports; forbidden from editing memory/specs/source/CI; output must include 1–10 compliance score. Body ≤ 60 lines.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-03 — Author rule `design-specialist-scope.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.3
- **Depends on:** none
- **Parallel-safe with:** AGT-01, AGT-02, AGT-04, AGT-05, AGT-06
- **Files modified:**
  - `dadaia_workspace/public/rules/design-specialist-scope.md` (new)
- **Mudanças:** Design writes only to `.dadaia/reports/<ctx>/design-specialist/*` + `specs/assets/<scope>/*`; forbidden from FE code. Body ≤ 60 lines.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-04 — Update rule `dadaia-workspace-dev-guardrail.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.4
- **Depends on:** none
- **Parallel-safe with:** AGT-01, AGT-02, AGT-03, AGT-05, AGT-06
- **Files modified:**
  - `dadaia_workspace/public/rules/dadaia-workspace-dev-guardrail.md`
- **Mudanças:** Append section: PM and project-auditor are NOT allowed to run `dadaia public install --force`.
- **Aceite:** `dadaia public doctor` `[ok]`; grep finds the new prohibition note.

### AGT-05 — Update rule `game-agents-coordination.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.4
- **Depends on:** none
- **Parallel-safe with:** AGT-01, AGT-02, AGT-03, AGT-04, AGT-06
- **Files modified:**
  - `dadaia_workspace/public/rules/game-agents-coordination.md`
- **Mudanças:** Decision Authority Matrix row "Escopo, prioridades, SPEC" → primary becomes **project-manager**; PE remains tie-breaker for memory atomicity only.
- **Aceite:** `dadaia public doctor` `[ok]`; matrix table reflects new primary.

### AGT-06 — Update rule `game-developer-scope.md`

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.4
- **Depends on:** none
- **Parallel-safe with:** AGT-01..AGT-05
- **Files modified:**
  - `dadaia_workspace/public/rules/game-developer-scope.md`
- **Mudanças:** Add PM, auditor, code-reviewer, security-reviewer, researcher, design-specialist to "Proibido para Outros Agentes" list for `repos/tauan-games/`.
- **Aceite:** `dadaia public doctor` `[ok]`; the 6 new agents listed.

### AGT-07 — Update `dadaia-grill-me` skill preamble

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.2
- **Depends on:** none
- **Parallel-safe with:** AGT-01..AGT-06
- **Files modified:**
  - `dadaia_workspace/public/skills/dadaia-grill-me/SKILL.md`
- **Mudanças:** Update preamble — primary caller becomes project-manager during intake; PE may invoke when consulted as leaf for spec-level question.
- **Aceite:** `dadaia public doctor` `[ok]`; grep finds new preamble wording.

### AGT-08 — Author 5 skill stubs (frontmatter + TODO body)

- [x] **Owner:** product-engineer
- **Phase:** P1
- **SPEC acceptance:** §8.1 (declarative-only; bodies in P3)
- **Depends on:** AGT-07 (skill folder convention sanity)
- **Parallel-safe with:** none (single task touches 5 files)
- **Files modified:**
  - `dadaia_workspace/public/skills/project-orchestration/SKILL.md` (new stub)
  - `dadaia_workspace/public/skills/architecture-code-review/SKILL.md` (new stub)
  - `dadaia_workspace/public/skills/security-audit-protocol/SKILL.md` (new stub)
  - `dadaia_workspace/public/skills/drift-detection/SKILL.md` (new stub)
  - `dadaia_workspace/public/skills/ux-ui-review/SKILL.md` (new stub)
- **Mudanças:** Canonical frontmatter; body = `## TODO\n\nFull content lands in AGT-XX (P3).` Stub is sufficient for P2 agent frontmatter references to resolve.
- **Aceite:** `dadaia public stage && install --target all && doctor` reports `[ok]` for all 5 entries.

---

## Phase P2 — Agents (6 new + slim 2 + strip Agent ×8)

### AGT-09 — Author agent `project-manager.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-10, AGT-11, AGT-12, AGT-13, AGT-14, AGT-15, AGT-16, AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/project-manager.md` (new)
- **Mudanças:** Frontmatter per SPEC §5.1 (Opus 4.7, tools incl. `Agent`, 6 skills); body covers mission, dispatch protocol, Decision Authority Matrix mediation, escalation, hard rules. Description ≤ 300 chars.
- **Aceite:** `MarkdownAgentStore` loads it; `dadaia public doctor` `[ok]`.

### AGT-10 — Author agent `project-auditor.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.5
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09, AGT-11..AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/project-auditor.md` (new)
- **Mudanças:** Opus 4.7, tools incl. `Agent`, 4 skills; mission ladder (PRIMARY drift, SECONDARY dead code, TERTIARY spec consistency); 1–10 compliance scorecard template across 6 dimensions; hard rules.
- **Aceite:** loads; `dadaia public doctor` `[ok]`.

### AGT-11 — Author agent `code-reviewer.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.2
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09, AGT-10, AGT-12..AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/code-reviewer.md` (new)
- **Mudanças:** Sonnet 4.6, NO `Agent`, 3 skills; 6-axis review checklist; recommendation set {approve, request-changes, comment}; hard rules (never edits; never approves).
- **Aceite:** loads; `dadaia public doctor` `[ok]`.

### AGT-12 — Author agent `researcher.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.3
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-11, AGT-13..AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/researcher.md` (new)
- **Mudanças:** Sonnet 4.6, NO `Agent`, includes `WebFetch + WebSearch`; whitelisted sources; citation rule (file:line or URL on every claim); hard rules.
- **Aceite:** loads; `dadaia public doctor` `[ok]`.

### AGT-13 — Author agent `security-reviewer.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.4
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-12, AGT-14..AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/security-reviewer.md` (new)
- **Mudanças:** Sonnet 4.6, NO `Agent`, references `security-audit-protocol` skill; OWASP Top 10, secret detection, dep CVE scans; CWE + file:line + redacted evidence + fix rec; hard rules.
- **Aceite:** loads; `dadaia public doctor` `[ok]`.

### AGT-14 — Author agent `design-specialist.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §5.6
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-13, AGT-15..AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/design-specialist.md` (new)
- **Mudanças:** Sonnet 4.6, NO `Agent`, `WebFetch + WebSearch`; consumes qa Playwright captures; reference whitelist (Dribbble, Mobbin, Figma Community, Refactoring UI, HIG, M3); emits tokens/typography/spacing/motion/breakpoints/a11y + ASCII; hard rules (no production code; no rasters).
- **Aceite:** loads; `dadaia public doctor` `[ok]`.

### AGT-15 — Slim agent `product-engineer.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §6.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-14, AGT-16, AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/product-engineer.md`
- **Mudanças:** Remove `Agent` from `tools`; tighten description ≤ 300 chars; REMOVE Discovery / dispatch / synthesis / wide grill-me sections; KEEP SDD hierarchy + memory atomicity + status gates; ADD `## Invocation contract` section + "Memories → Spec Context Projects" UI-rename note. Target ≤ 280 lines.
- **Aceite:** loads; `dadaia public doctor` `[ok]`; `wc -l` ≤ 280.

### AGT-16 — Slim agent `frontend-engineer.md`

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §6.2
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-15, AGT-17
- **Files modified:**
  - `dadaia_workspace/public/agents/frontend-engineer.md`
- **Mudanças:** Remove `Agent` from `tools`; tighten description ≤ 300 chars; REMOVE `### Aesthetics — anti-AI-slop` + `frontend-design` self-invocation paragraph; ADD `## Design handoff contract`. Target ≤ 230 lines.
- **Aceite:** loads; `dadaia public doctor` `[ok]`; `wc -l` ≤ 230.

### AGT-17 — Strip `Agent` tool from 8 leaf implementers

- [x] **Owner:** product-engineer
- **Phase:** P2
- **SPEC acceptance:** §6.3
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-09..AGT-16 (file targets disjoint)
- **Files modified:**
  - `dadaia_workspace/public/agents/software-engineer.md`
  - `dadaia_workspace/public/agents/backend-engineer.md`
  - `dadaia_workspace/public/agents/qa-engineer.md`
  - `dadaia_workspace/public/agents/software-architect.md`
  - `dadaia_workspace/public/agents/devops-engineer.md`
  - `dadaia_workspace/public/agents/game-developer.md`
  - `dadaia_workspace/public/agents/game-designer.md`
  - `dadaia_workspace/public/agents/game-tester.md`
- **Mudanças:** Remove `Agent` from `tools` frontmatter line. No body changes.
- **Aceite:** `grep -nE '^\s*-?\s*Agent\b' dadaia_workspace/public/agents/*.md` returns only project-manager.md and project-auditor.md; `dadaia public doctor` `[ok]`.

---

## Phase P3 — Skill bodies

### AGT-18 — Skill `project-orchestration` (full body)

- [-] **Owner:** product-engineer
- **Phase:** P3
- **SPEC acceptance:** §8.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-19, AGT-20, AGT-21, AGT-22
- **Files modified:** `dadaia_workspace/public/skills/project-orchestration/SKILL.md`
- **Mudanças:** Replace TODO body with: agent + workflow inventory matrices; dispatch protocol; mediation rules (Decision Authority Matrix); escalation ladder; forbidden actions.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-19 — Skill `architecture-code-review` (full body)

- [-] **Owner:** product-engineer
- **Phase:** P3
- **SPEC acceptance:** §8.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-18, AGT-20, AGT-21, AGT-22
- **Files modified:** `dadaia_workspace/public/skills/architecture-code-review/SKILL.md`
- **Mudanças:** 6-axis checklist; OOP/SOLID heuristics; design-pattern misuse; complexity rubric; output template.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-20 — Skill `security-audit-protocol` (full body)

- [-] **Owner:** product-engineer
- **Phase:** P3
- **SPEC acceptance:** §8.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-18, AGT-19, AGT-21, AGT-22
- **Files modified:** `dadaia_workspace/public/skills/security-audit-protocol/SKILL.md`
- **Mudanças:** OWASP 2025 mapping; dep-scan workflow (pip-audit / npm audit / go list); secrets scan rules; IaC review; STRIDE template; severity matrix.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-21 — Skill `drift-detection` (full body)

- [-] **Owner:** product-engineer
- **Phase:** P3
- **SPEC acceptance:** §8.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-18, AGT-19, AGT-20, AGT-22
- **Files modified:** `dadaia_workspace/public/skills/drift-detection/SKILL.md`
- **Mudanças:** Memory↔implementation diff protocol; dead-code detection; 1–10 scoring rubric per dimension; canonical dadaia CLI commands.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-22 — Skill `ux-ui-review` (full body)

- [-] **Owner:** product-engineer
- **Phase:** P3
- **SPEC acceptance:** §8.1
- **Depends on:** AGT-08
- **Parallel-safe with:** AGT-18..AGT-21
- **Files modified:** `dadaia_workspace/public/skills/ux-ui-review/SKILL.md`
- **Mudanças:** WCAG 2.2 AA checklist; visual hierarchy heuristics; design-system conformance rubric; reference-search whitelist; output template.
- **Aceite:** `dadaia public doctor` `[ok]`.

---

## Phase P4 — Refactor 6 existing workflows (PE → PM swap)

### AGT-23 — Refactor `spec-refinement.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09 (PM must exist)
- **Parallel-safe with:** AGT-24, AGT-25, AGT-26, AGT-27, AGT-28
- **Files modified:** `dadaia_workspace/public/workflows/spec-refinement.workflow.md`
- **Mudanças:** discovery stage `agent: product-engineer` → `agent: project-manager` (runs grill-me); synthesis stage → PM (assembles reports); ADD sub-stage `spec_write` with `agent: product-engineer` as leaf. `expected_output.path` updates to PM-owned paths.
- **Aceite:** `dadaia public doctor` `[ok]`; panel DAG renders.

### AGT-24 — Refactor `game-spec-definition.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09
- **Parallel-safe with:** AGT-23, AGT-25..AGT-28
- **Files modified:** `dadaia_workspace/public/workflows/game-spec-definition.workflow.md`
- **Mudanças:** same pattern as spec-refinement (discovery → PM; synthesis → PM + sub-stage `spec_write` for PE).
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-25 — Refactor `cross-cutting-feature.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09
- **Parallel-safe with:** AGT-23, AGT-24, AGT-26..AGT-28
- **Files modified:** `dadaia_workspace/public/workflows/cross-cutting-feature.workflow.md`
- **Mudanças:** discovery → PM. contract_review unchanged.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-26 — Refactor `onboarding-new-repo.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09
- **Parallel-safe with:** AGT-23..AGT-25, AGT-27, AGT-28
- **Files modified:** `dadaia_workspace/public/workflows/onboarding-new-repo.workflow.md`
- **Mudanças:** synthesis → PM + sub-stage `spec_write` for PE.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-27 — Refactor `architecture-review.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09
- **Parallel-safe with:** AGT-23..AGT-26, AGT-28
- **Files modified:** `dadaia_workspace/public/workflows/architecture-review.workflow.md`
- **Mudanças:** Split task_conversion: PM filters/prioritizes; PE converts to TASKS.md.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-28 — Refactor `hotfix-release.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P4
- **SPEC acceptance:** §7.1
- **Depends on:** AGT-09
- **Parallel-safe with:** AGT-23..AGT-27
- **Files modified:** `dadaia_workspace/public/workflows/hotfix-release.workflow.md`
- **Mudanças:** promote_to_release → PM decides patch number; dispatches PE for SPEC entry. close_with_smoke remains qa-engineer; CLOSURE remains PE.
- **Aceite:** `dadaia public doctor` `[ok]`.

---

## Phase P5 — 3 new workflows

### AGT-29 — Author workflow `audit-cycle.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P5
- **SPEC acceptance:** §7.2
- **Depends on:** AGT-10, AGT-11, AGT-12, AGT-13 (auditor + 3 reviewers must exist)
- **Parallel-safe with:** AGT-30, AGT-31
- **Files modified:** `dadaia_workspace/public/workflows/audit-cycle.workflow.md` (new)
- **Mudanças:** project-auditor orchestrates 4-way parallel: code-reviewer + security-reviewer + researcher + qa-engineer → synthesis with compliance score. Manual trigger.
- **Aceite:** `dadaia public doctor` `[ok]`; DAG renders 4 parallel nodes + synthesis convergence.

### AGT-30 — Author workflow `code-review-fan-out.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P5
- **SPEC acceptance:** §7.2
- **Depends on:** AGT-11, AGT-13, AGT-14
- **Parallel-safe with:** AGT-29, AGT-31
- **Files modified:** `dadaia_workspace/public/workflows/code-review-fan-out.workflow.md` (new)
- **Mudanças:** Per-PR parallel: code-reviewer + security-reviewer + (conditional) design-specialist → PM consolidates verdict. Conditional handled agent-side (skip-if-not-applicable), no schema change.
- **Aceite:** `dadaia public doctor` `[ok]`.

### AGT-31 — Author workflow `design-validation.workflow.md`

- [x] **Owner:** product-engineer
- **Phase:** P5
- **SPEC acceptance:** §7.2
- **Depends on:** AGT-14
- **Parallel-safe with:** AGT-29, AGT-30
- **Files modified:** `dadaia_workspace/public/workflows/design-validation.workflow.md` (new)
- **Mudanças:** qa-engineer Playwright captures → design-specialist UX review.
- **Aceite:** `dadaia public doctor` `[ok]`.

---

## Phase P6 — Reader `paths` field + 10 panel test updates

### AGT-32 — Extend `reader.py` with `paths` field

- [x] **Owner:** software-engineer
- **Phase:** P6
- **SPEC acceptance:** §8.5
- **Depends on:** AGT-09..AGT-17 (agents present so tests can iterate)
- **Parallel-safe with:** none (sequential gate before tests)
- **Files modified:**
  - `dadaia_workspace/features/agents/reader.py`
- **Mudanças:** Extend `_ALLOWED_FIELDS` to include `paths`; map to optional `paths: dict[str, list[str]] | None` on `AgentDTO`. Declarative-only — no gate enforcement.
- **Aceite:** `pytest -q tests/unit/features/agents/test_reader.py` green; new field accessible on DTO.

### AGT-33 — Update 10 panel/agents/workflows test files

- [x] **Owner:** software-engineer
- **Phase:** P6
- **SPEC acceptance:** §9 (full test list)
- **Depends on:** AGT-32, AGT-29, AGT-30, AGT-31
- **Parallel-safe with:** none (single task touches the 10 files)
- **Files modified:**
  - `tests/unit/features/agents/test_reader.py`
  - `tests/unit/features/panel/test_api_agents.py`
  - `tests/unit/features/panel/test_api_agent_prompt.py`
  - `tests/unit/features/panel/test_views_agents.py`
  - `tests/unit/features/panel/test_agents_expand_pr3_11.py`
  - `tests/unit/features/panel/test_api_workflows_list.py`
  - `tests/unit/features/panel/test_api_workflows_detail.py`
  - `tests/unit/features/panel/test_views_workflows.py`
  - `tests/unit/features/workflows/test_dag.py`
  - `tests/unit/test_workflow_schema.py`
- **Mudanças:** Per SPEC §9 — assertions for 6 new agents, 3 new workflows, path-traversal guard cases, audit-cycle DAG detail, project-manager expansion case, schema iteration includes 3 new workflow YAMLs.
- **Aceite:** `pytest -q tests/` green from repo root.

---

## Phase P7 — Consumer-repo audit

### AGT-34 — Consumer-repo `dadaia public doctor` sweep

- [ ] **Owner:** devops-engineer
- **Phase:** P7
- **SPEC acceptance:** C9
- **Depends on:** AGT-33
- **Parallel-safe with:** none (collects evidence sequentially per consumer)
- **Files modified:** none (read + run only)
- **Mudanças:** For every consumer repo in the workspace catalog, run `dadaia public doctor` and record stdout. If `drift` or `missing`, run `dadaia public install --target all` and retry. `unsupported` (e.g. Codex workflows = `[not-applicable]`) is acceptable.
- **Aceite:** Evidence collected for CLOSURE as triples `{consumer, command, stdout-snippet}`; every consumer reaches `[ok]` (or documented `[not-applicable]`).

---

## Phase P8 — CLOSURE (PE only)

P8 is a single product-engineer responsibility under the `dadaia-release-closure` skill.
It is not enumerated as a numbered task because it cannot start until all AGT-01..AGT-34
are `[x]` DONE. The PE will:

1. Set `ACTIVE.md` phase to `CLOSURE`.
2. Render memory atoms per SPEC §11 from templates.
3. Write `CLOSURE.md`.
4. `dadaia specs doctor` → green.
5. `git mv specs/releases/agents-r1-v1 specs/_archive/releases/agents-r1-v1`.
6. Set `ACTIVE.md` to `release: none / phase: none`.
