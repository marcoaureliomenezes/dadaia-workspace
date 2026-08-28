---
slug: harness-codex
title: Harness — Codex
category: product
tldr: Entry harness on the operator's Codex CLI — native AGENTS.md, Starlark command policy, version-qualified hook fire, `.codex/` projection.
summary: Capability and scaffold truth for the Codex harness — native AGENTS.md discovery, version-qualified hook certification, Starlark command policy, and the `.codex/` projection.
tags:
- harness
- codex
- projection
- enforcement
---

## Surface

Codex is an entry harness: the operator's `codex` TUI and its headless `codex exec`, governed by
`AGENTS.md` read natively up-tree plus the `.codex/` projection. It runs the same nine-role roster
against the same SDD documents as every other harness, and resolves no import chain that would
deliver a second copy of the law. PreToolUse `pre_gate` (matcher `^(apply_patch|Edit|Write|Bash)$`)
and a matcher-less PostToolUse heartbeat are registered in `.codex/hooks.json` through self-locating
wrappers under `.dadaia/hooks/codex-*`. Command policy is evaluated natively from
`.codex/rules/*.rules` — Starlark prefix rules over venv-form paths, not configuration keys.

**Hook fire is version-qualified.** Hooks are live-certified at `codex-cli 0.144.4`
(`_CODEX_HOOKS_LIVE_CERTIFIED_VERSION`, `infrastructure/codex_doctor.py`) for both the TUI and
headless `codex exec`. Any other installed version is probe-driven: `dadaia certify`'s
`codex-live-probe` invokes the installed binary and reports what it observed; an absent binary or a
different version yields UNVERIFIED plus a re-certify instruction, never an assumption. The git
chokepoints enforce the commit/push boundary independently of hook fire ([[sdd-gate-v3]]).

Projected by `dadaia public install --target codex`: `.codex/{config.toml,hooks.json,rules,skills,
DADAIA.md}` plus `.codex/agents/` — nine role-only TOML personas carrying no inline law
restatement, whose tier identity is Codex-native `(model id × model_reasoning_effort)`,
registry-derived via `core/model_registry.codex_tier_views()` (deep→high, dispatch→medium) and
rendered loudly-failing when two tiers collapse to one pair, with doctor lint `D-CX-4` blocking
Anthropic tier names and Claude model/path/tool-name leaks ([[workspace-init]]).

## Dependencies

[[tech-stack]], [[sdd-gate-v3]], [[agentic-entities]], [[public-asset-distribution]],
[[agent-orchestration]].
