---
slug: harness-primitives
title: harness-primitives
category: product
tldr: 'Middle-depth harness literacy for all agents: primitive definitions, Claude Code vs Codex deltas, dadaia projection mechanics, and ai-engineer defer checklist.'
summary: Available to all 9 core agents. Defines at middle depth what each AI harness
  primitive is (agent persona, subagent, skill, rule, hook, AGENTS.md, MCP), how Claude Code
  and Codex differ in naming and enforcement for each primitive, how dadaia stages and projects
  them (public/ -> stage -> install -> .claude/.codex/.pi/.agents; manifest SHA256;
  doctor checks), and a decision checklist for when to defer deeper questions to ai-engineer.
  Complements the ai-engineer-only deep skills without duplicating their protocol depth.
tags:
- harness
- primitives
- all-agents
- claude-code
- codex
- literacy
agent_tier: self-pull
token_estimate: 620
last_updated: '2026-06-25'
release_origin: v0.1.18
---

## Propósito

`harness-primitives` is the shared middle-depth literacy skill available to all 9 core
agents. It answers the question "what is this harness thing I keep seeing
referenced in workspace rules?" at a depth sufficient for agents to follow workspace
protocols without needing to become harness specialists.

"Harness" carries two meanings, and the skill teaches both (the **two-layer agentic
model** — see [[architecture]]): **Layer 1** is the entry harness the operator launches
in the terminal — `claude`, `codex`, or `pi` (three entry harnesses; PI is the third) —
where governance is `AGENTS.md` + the projected `.X/` asset trees; **Layer 2** is the
per-step worker harness the lifecycle engine drives behind `AgentRuntimePort` (the four
`AgentRuntimeKind`s — see [[tech-stack]] `## Agent runtimes` for the canonical roster),
selectable via `--harness`. The Claude-Code-vs-Codex deltas below are Layer-1 deltas.

The skill defines each primitive (agent persona, subagent/dispatch, skill, rule,
hook, AGENTS.md, MCP tool injection), explains how Claude Code and Codex differ in
naming and behavior for each, describes how dadaia's canonical asset chain projects
them from `public/` source to runtime trees, and provides a decision checklist for
when a question goes beyond literacy and requires `ai-engineer`'s depth.

## Fluxo de uso

1. An agent encounters a workspace rule or protocol that references a harness primitive
   it does not recognize (e.g. "why does this rule fire?", "what is a hook?").
2. The agent invokes `harness-primitives` and reads the primitive catalog section for
   a one-paragraph orientation.
3. If the agent is operating across both Claude Code and Codex surfaces, it reads the
   comparison table to understand naming and behavior deltas.
4. If the agent is trying to understand why a projection is present or absent, it reads
   the dadaia projection mechanics section.
5. If the question cannot be answered at literacy depth, the agent reads the
   defer-to-ai-engineer checklist and dispatches `ai-engineer` if any item matches.

## Trigger típico

Any non-ai-engineer agent receives a workspace task involving harness primitives and
needs orientation before following the protocol.

## Diferencial

Before this skill, agents had no middle-depth reference for harness primitives. They
either worked blind (guessing at what "a hook" or "a rule" means in context) or
needed to escalate to `ai-engineer` for basic definitions. `harness-primitives` fills
that middle layer: agents can answer their own basic harness questions and reserve
`ai-engineer` dispatch for genuine depth work.

## Estado runtime tocado

- No runtime state written by this skill.
- Projected to: `.claude/skills/harness-primitives/SKILL.md`,
  `.agents/skills/harness-primitives/SKILL.md`, and relevant Codex/PI paths
  via `dadaia public install`.
- Source: `dadaia_workspace/public/skills/harness-primitives/SKILL.md`.

## Dependências

- No hard dependencies. The skill is self-contained by design so any agent can use it
  without loading additional context.
- Complements `ai-harness-claude-code`, `ai-harness-codex`, and `ai-context-engineering`
  (the ai-engineer-only deep skills) — those provide decision protocols; this provides
  definitions.
