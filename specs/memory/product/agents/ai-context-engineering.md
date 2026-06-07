---
slug: ai-context-engineering
title: ai-context-engineering
category: product
tldr: Deep ai-engineer skill covering token economy, instruction hierarchy, persona-consistency invariants, model-tier selection, and scope-drift detection.
summary: Harness-agnostic context-engineering craft for ai-engineer. Covers token economy
  (cost-per-line discipline, tables vs prose compression, link vs inline decision), the
  canonical 10-section instruction hierarchy and attention ordering, five persona-consistency
  invariants (frontmatter schema, body order, [SCOPE ERROR] format, TDD flow, handoff
  contract), model-tier selection decision table (Opus/Sonnet/Haiku rubric), and recursive
  scope-drift detection with three detection rules and topology guard protocol. Extracted
  and expanded from the ai-engineer persona. Restricted to ai-engineer.
tags:
- ai-engineer
- context-engineering
- token-economy
- persona-consistency
- model-tier
agent_tier: self-pull
token_estimate: 468
last_updated: '2026-06-04'
release_origin: v0.1.4.6
---

## Propósito

`ai-context-engineering` is a deep skill restricted to `ai-engineer`. It extracts
and expands the context-engineering principles that were previously inlined in the
`ai-engineer` persona body, turning them into a reusable, protocol-depth resource.

The skill covers all five craft areas: token economy (how to reason about every line
as a recurring cost), instruction hierarchy (the canonical 10-section body order and
why reordering degrades attention), persona-consistency invariants (five invariants
every persona must satisfy and how to detect and fix violations), model-tier selection
(workload characterization rubric and cost-justification discipline), and recursive
scope-drift detection (the drift failure mode, three detection rules, topology guard).

## Fluxo de uso

1. `ai-engineer` invokes this skill when auditing an existing persona for consistency,
   drafting a new persona, or selecting a model tier for a new agent.
2. The token economy section is applied to decide whether to inline content or link,
   and whether to use a table or prose.
3. The instruction hierarchy section is used to verify or repair section order in any
   persona under review.
4. The five-invariant checklist is applied to every persona modification as a
   pre-commit gate.
5. The model-tier table is consulted when a model upgrade or downgrade is proposed,
   requiring measured-cost justification.
6. The scope-drift detection protocol is invoked when a persona's write allowlist,
   forbidden-actions table, or self-edit risk note appears to have drifted.

## Trigger típico

`ai-engineer` is authoring or reviewing a persona file and needs to apply a consistent
engineering discipline to token economy, section ordering, or model-tier decisions.

## Diferencial

Without this skill, context-engineering decisions are made ad-hoc per persona, leading
to inconsistent section orders, bloated inline content, and model-tier choices made
without cost-justification. This skill provides a shared protocol layer so every
persona `ai-engineer` authors or reviews passes the same invariant checklist.

## Estado runtime tocado

- No runtime state written by this skill.
- Projected to: `.claude/skills/ai-context-engineering/SKILL.md` and
  `.agents/skills/ai-context-engineering/SKILL.md` via `dadaia public install`.
- Source: `dadaia_workspace/public/skills/ai-context-engineering/SKILL.md`.

## Dependências

- `harness-skill-scope` rule — enforces the ai-engineer-only restriction.
- `ai-harness-claude-code` and `ai-harness-codex` — sibling harness-specific skills;
  this skill is harness-agnostic and applies across all runtimes.
