---
slug: ai-harness-codex
title: ai-harness-codex
category: product
tldr: Deep ai-engineer Codex skill — AGENTS.md law, rules collision, trust model, live-verified hook facts.
summary: Provides ai-engineer with actionable mastery of the Codex harness — covering
  AGENTS.md as the scoped constitution, the naming-collision disambiguation between Codex
  Starlark .rules and dadaia workflow-protocols, Codex skill discovery, subagent fan-out
  model, config trust layers (global vs project), customization decision table, SDD phase
  integration, and hooks. Carries live-verified contract facts (codex-cli 0.139.0,
  evidence-level annotated) — hooks fire only in interactive sessions, never under
  headless codex exec. Restricted to ai-engineer by harness-skill-scope rule.
tags:
- ai-engineer
- harness
- codex
- skill
- decision-protocol
agent_tier: self-pull
token_estimate: 890
last_updated: '2026-06-12'
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

### Live-verified contract facts (codex-cli 0.139.0)

The skill and academy course 07 carry these facts with evidence-level annotations;
they are the current Codex runtime truth:

- **Hooks fire ONLY in interactive Codex (TUI) sessions.** `codex exec` (headless)
  never executes command hooks for any event (SessionStart / UserPromptSubmit /
  PreToolUse / PostToolUse), across all four documented config locations and with
  `--dangerously-bypass-hook-trust`. Consequence: the Codex **automation path is
  discipline-only** — deterministic SDD-gate enforcement on Codex exists only in
  interactive sessions. Tracked upstream as bug
  `codex-exec-hooks-do-not-fire-headless` (Open; upstream Codex defect).
- **Block envelope:** the legacy `{"decision":"block"}` stdout envelope IS honored
  interactively — a gate-shaped PreToolUse hook demonstrably blocked a FROZEN
  `specs/_archive/` write via `apply_patch` in the TUI.
- **Matcher form:** the anchored regex matcher `^(apply_patch|Edit|Write)$` is valid
  and matches.
- **Hook commands are shell-executed** — env-prefixed command strings work.
- **Invalid config keys:** `approved_commands` and `[skills] paths` are NOT valid
  Codex config keys (inert; no runtime behavior). `[agents."<name>"] config_file`
  IS real and loads custom-agent TOML.
- **Model tiering is Codex-native:** tier identity = (model id ×
  `model_reasoning_effort`), registry-derived via
  `core/model_registry.codex_tier_views()` — deep→high, dispatch→medium reasoning
  effort; rendering fails loudly when a mapping collapses two tiers into one id;
  Anthropic tier names (Opus/Sonnet/Haiku) are lint-blocked by doctor D-CX-4 in
  Codex-projected artifacts.
- **Live verification harness:** `tests/integration/codex_live/` (opt-in via
  `DADAIA_CODEX_LIVE=1`) drives a real Codex binary against a throwaway trusted
  workspace under `.dadaia/tmp/` and re-proves these facts repeatably.

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

- Read-only input: `dadaia_workspace/features/academy/knowledge_basis/07_codex/` —
  the full English Codex academy course (README, numbered lessons, exercises,
  example, references), official-doc-derived and annotated with the same
  live-verified facts (primary source during skill authoring; not read at
  invocation time).
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
