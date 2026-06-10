---
slug: multi-platform-parity
title: multi-platform-parity
category: product
tldr: "Claude Code, Codex, and OpenCode receive honest runtime-specific projections from the same public source (9 agents / 18 skills / 2 workflows / Codex .rules)."
summary: Codex uses native config, shared and Codex-specific skills, hook parity,
  native Starlark .rules command policy, workflow docs that do not auto-execute,
  and Codex custom-agent wording. Public surface is 9 core agents, 18 skills, 2 workflows. Plugin stubs (frontend-engineer,
  design-specialist, devops-engineer) project as thin stubs with no behavior until
  the plugin is installed.
tags:
- codex
- opencode
- claude-code
- parity
- multi-platform
agent_tier: self-pull
token_estimate: 606
last_updated: '2026-06-07'
release_origin: v0.2.2
---

## Propósito

Multi-platform parity means the same canonical public assets are projected to
Claude Code, Codex, and OpenCode without pretending the runtimes are identical.
Each projection must be truthful about the runtime's native concepts, supported
hooks, config loading, workflow support, and skill discovery.

## Public surface counts (v0.2.0)

| Asset type | Count | Notes |
|-----------|-------|-------|
| Core agents | 9 | project-manager, project-auditor, product-engineer, software-engineer, qa-engineer, security-reviewer, code-reviewer, ai-engineer, software-architect |
| Plugin stubs | 3 | frontend-engineer, design-specialist (plugin: frontend-design); devops-engineer (plugin: devops) |
| Skills | 18 | Reduced from 22 in v0.1.9 (5 frontend/design skills → plugin) |
| Workflows | 2 | release-ship, audit-fanout (7 stale workflows deleted in v0.1.9) |
| Rules | 5 | workspace-protocol, tmp-file-guardrail, plugin-scope, dadaia-workspace-dev-guardrail, harness-skill-scope |

Agent personas for the following names do not exist in `dadaia_workspace/public/agents/`:
`software-engineer-python`, `software-engineer-node`, `backend-engineer`, `researcher`.
These were consolidated into `software-engineer` or removed from the public roster in v0.1.8.

Plugin stubs (`frontend-engineer`, `design-specialist`, `devops-engineer`) project as
empty stubs — no behavior until the corresponding plugin is installed.

## Fluxo de uso

Codex receives:

- `AGENTS.md` as the automatically loaded workspace rule surface.
- `.codex/config.toml` containing `[agents."<name>"] config_file = "agents/<name>.toml"`
  entries for all projected agents.
- `.codex/agents/*.toml` containing native custom-agent definitions, mapped Codex
  models, `sandbox_mode`, `model_reasoning_effort`, and developer instructions.
- `[skills] paths = [".agents/skills", ".codex/skills"]` so shared skills and
  Codex-only adapters are explicit.
- `.codex/rules/dadaia-command-policy.rules` as the executable Starlark command-policy
  rule. Markdown files under `public/rules/*.md` remain behavioral protocols and are not
  projected as executable Codex Rules.
- `.codex/hooks.json` with `PreToolUse`, `PostToolUse`, and `UserPromptSubmit`
  entries where the runtime supports them.
- broad hook matchers; shell scripts decide whether a tool call is relevant.
- workflows installed as reference docs; workflow Markdown does not auto-execute.
- dispatch wording based on Codex custom agents, never fake tool names or stale
  tool-discovery promises.

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

`dadaia public doctor` is the source of truth for projection state. It reports:
- `.claude/agents/`: exactly 9 agent files; no orphan files from deleted personas.
- `.codex/agents/`: TOML agent files with no fake model-derived skill names.
- `.codex/rules/`: native `.rules` command policy and no Markdown protocol masquerading
  as executable rules.
- `.claude/skills/`, `.agents/skills/`: 18 skill directories.
- Codex workflows as reference-only, not missing runtime behavior.
- OpenCode workflow limitations separately.
- All staged SHA256 hashes match projected files (`[ok]` for every asset; `[drift]` on mismatch).

`dadaia public install --target all` propagates source → all runtimes; no `--force`
needed for ordinary source edits (plain install overwrites on hash mismatch). `--force`
is only for clobbering a locally-diverged projection.
