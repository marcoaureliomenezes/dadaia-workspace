---
slug: ai-harness-codex
title: ai-harness-codex
category: product
tldr: 'Deep ai-engineer skill for Codex: AGENTS.md constitution, rules naming collision, config trust model, subagent fan-out, and customization decision table.'
summary: Provides ai-engineer with actionable mastery of the Codex harness — covering
  AGENTS.md as the scoped constitution, the naming-collision disambiguation between Codex
  Starlark .rules and dadaia workflow-protocols, Codex skill discovery, subagent fan-out
  model, config trust layers (global vs project), customization decision table, SDD phase
  integration, and hooks. Restricted to ai-engineer by harness-skill-scope rule.
tags:
- ai-engineer
- harness
- codex
- skill
- decision-protocol
agent_tier: self-pull
token_estimate: 552
last_updated: '2026-06-07'
release_origin: v0.2.2
---

## Propósito

`ai-harness-codex` is a deep decision-protocol skill restricted to `ai-engineer`.
It compiles the academy lessons on the Codex harness into actionable protocols for
designing, auditing, and evolving dadaia's Codex projection surface.

The skill resolves the most error-prone Codex authoring hazards: the "Rules" naming
collision (Codex Starlark `.rules` vs dadaia's Markdown workflow-protocol documents),
the trust boundary between user-global `~/.codex` config and project-local `.codex`,
what must never be placed in project config, and the Codex subagent fan-out model.
Official Codex documentation is referenced as links, never transcribed.

Current projection invariant: Codex receives native custom-agent TOML under
`.codex/agents/*.toml`, native command policy under `.codex/rules/*.rules`, and hook
configuration under `.codex/hooks.json`. Markdown behavioral protocols are guidance and
must not be installed as executable Codex Rules. Skill identifiers such as
`ai-harness-claude-code` are legitimate cross-harness references and must not be rewritten
as model names.

## Fluxo de uso

1. `ai-engineer` invokes this skill when designing or modifying a Codex-specific
   projection (`.codex/config.toml`, `.codex/hooks.json`, `.codex/agents/`,
   `.codex/rules/*.rules`, skills).
2. The naming-collision disambiguation section is applied before using the word "Rules"
   in any Codex-targeted document.
3. The config trust model section is applied to decide which config layer a setting
   belongs in and what must remain in `~/.codex` (user-global).
4. The customization decision table maps a desired customization goal to the correct
   file type and config layer.
5. The subagent fan-out section guides concurrency design and guard conditions.

## Trigger típico

`ai-engineer` is authoring or reviewing a Codex projection file and needs to reason
about the correct primitive, config layer, or naming convention without re-deriving
from first principles.

## Diferencial

Codex has naming and behavioral differences from Claude Code that cause persistent
authoring errors (wrong "rules" term, wrong config layer, unconstrained fan-out).
This skill encodes those distinctions as explicit disambiguations and decision tables,
making Codex-targeted work consistent and the naming collision visible.

## Estado runtime tocado

- Read-only input: `.dadaia/academy/07_codex/` HTML lessons (primary source during skill
  authoring; not read at invocation time).
- No runtime state written by this skill.
- Projected to: `.claude/skills/ai-harness-codex/SKILL.md` and
  `.agents/skills/ai-harness-codex/SKILL.md` via `dadaia public install`.
- Source: `dadaia_workspace/public/skills/ai-harness-codex/SKILL.md`.
- Guarded by `dadaia public doctor` checks for missing custom-agent TOML, stale Claude
  model/path leaks, missing skill references, Markdown `.codex/rules/*.md`, hook shape,
  and missing TOML role-boundary fields.

## Dependências

- `harness-skill-scope` rule — enforces the ai-engineer-only restriction.
- `ai-harness-claude-code` — sibling skill for Claude Code protocols; together they
  cover the two primary harnesses.
- `harness-primitives` — open all-agent literacy skill that bridges the gap for
  non-ai-engineer agents.
