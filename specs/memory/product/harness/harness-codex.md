---
slug: harness-codex
title: Harness — Codex
category: product
tldr: Entry harness on the operator's Codex CLI — native AGENTS.md, Starlark command policy, version-qualified hook fire, `.codex/` projection.
summary: Capability and scaffold truth for the Codex harness — native AGENTS.md discovery, version-qualified hook certification, Starlark command policy and the .codex/ projection.
tags: [harness, codex, projection, enforcement]
---

## Surface

- Codex is an entry harness — the `codex` TUI and headless `codex exec` — governed by `AGENTS.md` read natively up-tree plus the `.codex/` projection.
- PreToolUse `pre_gate` (matcher `^(apply_patch|Edit|Write|Bash)$`) and a matcher-less PostToolUse heartbeat are registered in `.codex/hooks.json` through wrappers under `.dadaia/hooks/codex-*`.
- Command policy is evaluated natively from `.codex/rules/*.rules` — Starlark prefix rules over venv-form paths, not configuration keys.
- Hook fire is version-qualified: hooks are live-certified at `codex-cli 0.144.4` (`_CODEX_HOOKS_LIVE_CERTIFIED_VERSION`, `infrastructure/codex_doctor.py`) for both the TUI and headless `codex exec`.
- Any other version is probe-driven: `dadaia certify`'s `codex-live-probe` invokes the binary and reports what it observed, an absent or different version yielding UNVERIFIED.
- `dadaia public install --target codex` projects `.codex/{config.toml,hooks.json,rules,skills,DADAIA.md}` plus `.codex/agents/` — nine role-only TOML personas carrying no inline law restatement.
- Codex tier identity is native `(model id × model_reasoning_effort)`, registry-derived via `core/model_registry.codex_tier_views()`, failing loudly when two tiers collapse to one pair.
- Doctor lint `D-CX-4` blocks Anthropic tier names and Claude model or tool-name leaks ([[sdd-gate-v3]]).

## Dependencies

[[tech-stack]], [[sdd-gate-v3]], [[agentic-entities]], [[public-asset-distribution]], [[agent-orchestration]].
