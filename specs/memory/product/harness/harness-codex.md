---
slug: harness-codex
title: harness-codex
tldr: Entry harness on the Codex CLI — native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, Starlark rules and the persona TOML transcode.
summary: Codex reads the root map, the root->cwd AGENTS.md chain and .agents/skills natively; .codex/ holds config.toml, hooks.json, rules and the three dd- persona TOMLs transcoded from .agents/agents/. The .codex/skills copies and the DADAIA.md mirror died at 0.4.7 candidate 6.
tags: [harness, codex, projection, hooks]
---

## Surface

- Codex is an entry harness — the `codex` TUI and headless `codex exec` — governed by the root `AGENTS.md` map and the root->cwd `AGENTS.md` chain read natively (32 KiB cap, no longer a design constraint), plus `.agents/skills/` read natively (probe PANDA/KOALA 2026-09-20, codex 0.145).
- PreToolUse `pre_gate` (matcher `^(apply_patch|Edit|Write|Bash)$`) and a matcher-less PostToolUse reaper are registered in `.codex/hooks.json` through wrappers under `.dadaia/hooks/codex-*`.
- Command policy is evaluated natively from `.codex/rules/*.rules` — Starlark prefix rules over venv-form paths, not configuration keys.
- Hook fire is version-qualified: hooks are live-certified at `codex-cli 0.144.4` (`_CODEX_HOOKS_LIVE_CERTIFIED_VERSION`, `infrastructure/codex_doctor.py`); any other version is probe-driven by `dadaia certify`'s `codex-live-probe`, an absent or different version yielding UNVERIFIED. No version floor is enforced.
- `dadaia public install --target codex` projects `.codex/{config.toml,hooks.json,rules}` plus `.codex/agents/dd-*.toml` — three role-only TOML personas transcoded from `.agents/agents/` (`sandbox_mode` derived from `activity_class`), stale filenames pruned; no skills copy, no law mirror.
- Codex tier identity is native `(model id × model_reasoning_effort)`, registry-derived via `core/model_registry.codex_tier_views()`, failing loudly when two tiers collapse to one pair.
- Doctor lint `D-CX-4` blocks Anthropic tier names and Claude model or tool-name leaks; `D-CX-7` resolves every `dd-` token a persona cites to a skill directory or a persona ([[sdd-gate-v3]]).

## Dependencies

[[TECHSTACK]], [[sdd-gate-v3]], [[agentic-entities]], [[public-asset-distribution]], [[agent-orchestration]].
