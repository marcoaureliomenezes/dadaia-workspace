---
slug: multi-platform-parity
title: multi-platform-parity
category: product
tldr: Claude Code, Codex, and OpenCode receive honest runtime-specific projections from the same public source.
summary: Codex uses native config, shared and Codex-specific skills, hook parity, reference-only workflows, and Codex-native multi-agent wording.
tags:
- codex
- opencode
- claude-code
- parity
- multi-platform
agent_tier: self-pull
token_estimate: 355
last_updated: '2026-06-03'
release_origin: public-agentic-hygiene-codex-readiness
---

## Propósito

Multi-platform parity means the same canonical public assets are projected to
Claude Code, Codex, and OpenCode without pretending the runtimes are identical.
Each projection must be truthful about the runtime's native concepts, supported
hooks, config loading, workflow support, and skill discovery.

## Fluxo de uso

Codex receives:

- `AGENTS.md` as the automatically loaded workspace rule surface.
- `.codex/config.toml` containing native `[agents.<name>]` blocks.
- `[skills] paths = [".agents/skills", ".codex/skills"]` so shared skills and
  Codex-only adapters are explicit.
- `.codex/hooks.json` with `PreToolUse`, `PostToolUse`, and `UserPromptSubmit`
  entries where the runtime supports them.
- broad hook matchers; shell scripts decide whether a tool call is relevant.
- workflows installed as reference docs, not as an executable workflow runtime.
- dispatch wording based on Codex tool discovery (`tool_search`) and deferred
  multi-agent tools when available, never a fake literal `subagent` tool.

Hook scripts prefer `.dadaia/.venv/bin/python` and fall back only when the
workspace venv is absent.

Claude Code receives the canonical agent bodies, Claude-native frontmatter,
skills, commands, hooks, and rules. Claude remains the strongest hook/runtime
reference, but shared docs must not assume Claude-only mechanisms exist in
Codex or OpenCode.

OpenCode receives transformed agent definitions, permissions mapped to its
runtime categories, and plugins that delegate SDD gate/context behavior to the
same shell scripts used by the other runtimes.

## Estado runtime tocado

`dadaia public doctor` is the source of truth for projection state. It reports
Codex workflows as reference-only, not missing runtime behavior. It reports
OpenCode workflow limitations separately. It also verifies Codex config/hooks,
shared skill paths, privacy cleanliness, and projection drift.
