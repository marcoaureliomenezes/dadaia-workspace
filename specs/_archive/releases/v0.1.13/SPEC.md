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

---

## Amendment — alpha-2 (2026-06-11): Codex Runtime Fidelity residuals

**Segment:** alpha-2 (release-governance ADR-1 maturity model). End-of-alpha-2
review gate: qa-engineer only.

### Motivation

The Codex runtime fidelity audit
(`specs/audits/2026-06-12T001813Z/codex-runtime-fidelity-review.md`) reviewed
alpha-1's own deliverables and found three residual risk classes:

1. **Enforcement UNVERIFIED (F-1, HIGH/UNVERIFIED; siblings F-6, F-8).** The SDD
   gate's actual blocking on Codex rests on three contract points never verified
   against a live Codex binary since the v0.1.10 Python-hook rewrite — failure
   mode is silent allow while the workspace believes deterministic enforcement
   exists.
2. **Four new Open bugs** in the projection tail (description-field Claude-ism
   leak, never-matching `dadaia` prefix rules, stale T-35 roster lint,
   Claude-centric model tiering in personas).
3. **Claude-centric model strategy.** MODEL_MAP id-substitution is the wrong
   abstraction for persona prose: Anthropic tier names survive as operative
   instructions and the mapped tier table collapses `deep`/`dispatch` into one id.

The operator approved folding the residual scope into this release as segment
alpha-2.

### Scope (operator grill decisions — final, do not re-open)

In scope: **WS-CDX-VERIFY + WS-CDX-BUGFIX + WS-CDX-MODEL** only.

The codex CLI IS installed: WS-CDX-VERIFY MUST be a scripted, repeatable harness
(`codex exec` against a trusted throwaway workspace under `.dadaia/tmp/`), not an
operator-manual procedure.

### Folded bugs (bugs-always-solved law)

Every picked bug is fixed in this segment; a bug is never silently dropped
(release-governance). No picked backlog item supersedes any of them.

| Bug | Severity | Closed by |
|---|---|---|
| `codex-agent-description-claude-ism-leak` | MEDIUM | T-013-09 |
| `codex-rules-dadaia-prefix-never-matches-venv-invocation` | MEDIUM | T-013-10 |
| `stale-legacy-software-engineer-lint-inverts-roster` | LOW | T-013-11 |
| `codex-personas-claude-model-tiering-leak` | MEDIUM | T-013-12 |

### Acceptance criteria per workstream

**WS-CDX-VERIFY**

- A scripted, repeatable harness drives `codex exec` in a trusted throwaway
  workspace under `.dadaia/tmp/` and yields marker-file evidence per hook event.
- A live trusted-Codex session demonstrably BLOCKS an attempted FROZEN
  `specs/_archive/` write via `apply_patch` — or the gate's Codex story is
  rewritten honestly as discipline-only.
- Every UNVERIFIED cell in the audit gap table within this scope (F-1: matcher
  form, block envelope, shell-exec of env-prefixed commands; F-6:
  `approved_commands`; F-8: `[agents."<n>"] config_file`) is resolved to a fact
  recorded in the `ai-harness-codex` skill and academy course 07.

**WS-CDX-BUGFIX**

- All 4 folded bugs fixed, test-backed.
- The `dadaia public doctor` D-CX suite catches the in-scope Claude-ism classes
  found by the audit (Claude tool names, Anthropic tier names) — regression-proof.
- No in-scope Codex-projected artifact (agent TOMLs, command-policy rules, doctor
  lints) claims behavior Codex does not have by default.

**WS-CDX-MODEL**

- Codex personas express model guidance in Codex-native terms: per-runtime tier
  rendering instead of MODEL_MAP prose substitution; `model_reasoning_effort` as a
  first-class tiering axis; loud failure when mapping collapses tiers.
- No Opus/Sonnet/Haiku prose survives in any Codex-projected persona body.

### Explicitly deferred (NOT in this release)

**WS-CDX-PROTOCOL** (F-2/F-11 — rule-corpus visibility on Codex) and
**WS-CDX-HYGIENE** (F-3/F-7/F-9/F-12 — trust surfacing, adapter-skill rework,
`.codex/workflows/` decision, doc cleanup) are deferred by operator decision.
They remain CANDIDATE in `specs/backlog/codex-runtime-fidelity.md`.
