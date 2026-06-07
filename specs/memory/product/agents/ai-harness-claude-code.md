---
slug: ai-harness-claude-code
title: ai-harness-claude-code
category: product
tldr: 'Deep ai-engineer skill for Claude Code: agentic loop, context hierarchy, rules, skills, hooks, subagents, tools, MCP, and composition decision tree.'
summary: Provides ai-engineer with actionable, protocol-oriented mastery of the Claude Code
  harness — covering the agentic loop and compaction boundary, the 8-layer context hierarchy
  decision protocol, rules enforcement (always_on vs path-scoped), skills mechanics and
  listing-budget management, hooks lifecycle and matcher semantics, subagent dispatch authority,
  tool permission model, MCP tool injection, and a composition decision tree encoding academy
  findings F1-F8 as protocol constraints. Restricted to ai-engineer by harness-skill-scope rule.
tags:
- ai-engineer
- harness
- claude-code
- skill
- decision-protocol
agent_tier: self-pull
token_estimate: 520
last_updated: '2026-06-04'
release_origin: v0.1.4.6
---

## Propósito

`ai-harness-claude-code` is a deep decision-protocol skill restricted to `ai-engineer`.
It compiles the academy lessons on the Claude Code harness into a set of actionable
protocols that `ai-engineer` can apply directly when designing, auditing, or debugging
AI-entity files in the dadaia workspace.

The skill covers the full primitive surface of Claude Code: the agentic loop and
compaction mechanics, the layered context hierarchy (CLAUDE.md, memory files, rules,
skills, hooks, subagents, MCP), enforcement semantics, listing-budget management, and
a composition decision tree encoding the lessons from dadaia's own academy audit
findings F1–F8 as protocol constraints.

Official Claude Code documentation is referenced as links within the skill, never
transcribed verbatim.

## Fluxo de uso

1. `ai-engineer` invokes this skill when a harness design question surfaces that requires
   reasoning about *why* a specific primitive behaves a certain way.
2. The skill's composition decision tree is consulted: given the new requirement, does it
   belong in CLAUDE.md, a rule, a skill, a hook, a subagent, or an MCP server?
3. The hooks lifecycle section is applied when designing PreToolUse/PostToolUse enforcement.
4. The listing-budget section (F5 encoding) is applied when deciding whether to split or
   merge skills, or use `applyTo` to narrow loading.
5. Official reference URLs in the skill's index section are followed on-demand; content
   is never imported from those URLs into the skill body.

## Trigger típico

`ai-engineer` needs to design a new AI-entity file or diagnose a harness anomaly (rule
firing unexpectedly, skill not loading, hook blocking a tool call) and requires a compiled
protocol to reason from rather than re-deriving from first principles.

## Diferencial

Without this skill, `ai-engineer` must reconstruct harness reasoning from scratch each
session, relying on ad-hoc exploration of academy lessons. This skill lifts that
compiled knowledge into a reusable protocol layer, making harness design decisions
consistent, well-justified, and resistant to session-to-session drift.

## Estado runtime tocado

- Read-only input: `.dadaia/academy/06_claude/` HTML lessons (primary source during skill
  authoring; not read at invocation time — the skill body is self-contained).
- No runtime state written by this skill.
- Projected to: `.claude/skills/ai-harness-claude-code/SKILL.md` and
  `.agents/skills/ai-harness-claude-code/SKILL.md` via `dadaia public install`.
- Source: `dadaia_workspace/public/skills/ai-harness-claude-code/SKILL.md`.

## Dependências

- `harness-skill-scope` rule — must be active for the restriction to apply.
- `harness-primitives` — the open all-agent literacy skill that `ai-engineer` may
  recommend when a non-ai-engineer agent asks a basic harness question.
