# SPEC: v0.1.13 — Codex Entity Parity + Academy Course

**Status:** Aprovado
**Release ID:** v0.1.13
**Owner:** product-engineer
**Created:** 2026-06-11

---

## Objective

Make the Codex runtime surface in dadaia-workspace honest, teachable, and closer to
the operator's Claude Code experience without pretending Codex behaves like Claude
Code. The release delivers four things:

1. A complete English `07_codex` Academy module based on current official OpenAI
   Codex docs and oriented to dadaia-workspace.
2. Refined Codex harness skills so `ai-engineer` has precise protocols for
   AGENTS.md, skills, rules, hooks, custom agents/subagents, config layers, and
   cross-harness boundaries.
3. Projection fixes for Codex command rules, reviewer sandbox boundaries, and the
   explicit dispatcher/subagent limitation that causes the observed Claude-vs-Codex
   drift.
4. Verification through `dadaia public doctor`, Codex rules validation where the
   local Codex binary supports it, focused tests, and Academy/Panel visibility.

## Operator Input

The operator explicitly requested this four-step flow on 2026-06-11 and provided the
official Codex source URLs:

- `https://developers.openai.com/codex/rules`
- `https://developers.openai.com/codex/hooks`
- `https://developers.openai.com/codex/guides/agents-md`
- `https://developers.openai.com/codex/skills`
- `https://developers.openai.com/codex/subagents`
- `https://developers.openai.com/codex/plugins`
- `https://developers.openai.com/codex/config-basic`
- `https://developers.openai.com/codex/config-advanced`
- `https://developers.openai.com/codex/config-reference`

The repeated operator prompt is treated as the scope-refinement session for this
release: the desired artifacts, target audience, and pain point are explicit.

## Bug Inventory

| Bug | Resolution |
|---|---|
| `codex-rules-generated-with-undocumented-command-allowed` | T-013-03 emits documented `prefix_rule(...)` command policy and verifies shape. |
| `codex-reviewer-agents-projected-workspace-write` | T-013-04 projects evidence-only reviewers as read-only in Codex custom-agent TOML. |

## Functional Requirements

### FR-1 — Academy Course

- Rewrite `dadaia_workspace/features/academy/knowledge_basis/07_codex/` as a
  coherent English course.
- Cover Codex mental model, AGENTS.md discovery and directory scoping, skills,
  plugins, hooks, Starlark Rules, config/trust layers, custom agents/subagents,
  workflow orchestration limits, and dadaia-workspace mapping.
- Include `README.md`, numbered lessons, `EXERCISES.md`, `EXAMPLE.md`, and
  `REFERENCES.md`.
- Keep official-doc content paraphrased and cited; do not paste long excerpts.

### FR-2 — Skill Refinement

- Refine `ai-harness-codex` with current official-doc-derived protocols.
- Update related all-agent literacy where needed so non-ai-engineer agents
  understand the basic Codex/Claude/OpenCode primitive boundaries.
- Make the central rule explicit: Codex custom agents and subagents require explicit
  spawn/delegation; workflow markdown does not execute the dispatcher model by
  itself.

### FR-3 — Projection Fixes

- Emit Codex command policy as documented `.rules` Starlark using
  `prefix_rule(...)`.
- Project reviewer/auditor agents with sandbox modes matching their actual role
  boundaries, especially evidence-only read/report roles.
- Make Codex workflow support honest in code and projected docs: workflow files are
  reference/context artifacts unless an explicit Codex subagent dispatch is invoked.

### FR-4 — Verification

- `dadaia public doctor` exits 0.
- Focused unit tests for Codex projection rules/sandbox behavior pass.
- Codex rules validation is attempted with `codex execpolicy check` when the local
  binary exists; if absent or incompatible, record that as an environment limitation
  and rely on shape tests.
- Academy module 7 is listed by `dadaia academy modules`.
- The Panel Academy view remains wired to render Academy courses through the
  existing `GET /api/academy` path.

## Non-Goals

- Do not build a new Codex workflow executor in this release.
- Do not make Codex auto-route every user demand to `project-manager`; official
  Codex behavior requires explicit agent/subagent requests.
- Do not change Claude Code or OpenCode projections except where shared public
  skills need wording updates.
- Do not modify the unrelated `v0.1.12` panel-auth release files.

## Acceptance

- The operator can open the Academy tab after creating/updating a course from module
  7 and read a full English Codex course.
- `ai-engineer` has updated Codex-specific instructions grounded in official docs.
- The projection no longer emits an undocumented `command_allowed` Codex Rules
  file.
- Evidence-only Codex reviewer custom agents are no longer projected as general
  workspace writers.
- Final response includes verification commands and outcomes.
