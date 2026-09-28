---
slug: harness-codex
title: harness-codex
tldr: "Entry harness on the Codex CLI: native AGENTS.md chain and .agents/skills; .codex/ carries config, hooks, the command policy and persona TOML."
summary: Codex reads the root map, the root->cwd AGENTS.md chain and .agents/skills natively; .codex/ holds config.toml, hooks.json, the command-policy rules and the three dd- persona TOMLs transcoded from .agents/agents/.
tags: [harness, codex, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/codex_doctor.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_config.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- Codex is an entry harness — the `codex` TUI and headless `codex exec` — reading the root `AGENTS.md` map, the root->cwd `AGENTS.md` chain and `.agents/skills/` natively; scoped law outside that chain reaches it by skill procedure ([[agentic-entities]]).
- `dadaia harness add codex` projects `.codex/config.toml`, `.codex/hooks.json`, `.codex/rules/dadaia-command-policy.rules` and `.codex/agents/dd-*.toml` — each persona transcoded from `.agents/agents/` with `sandbox_mode` `read-only` or `workspace-write` derived from its `activity_class`; every file is compared byte-wise against its renderer, stale persona files pruned.
- Command policy is the Starlark `.rules` file — prefix rules over venv-form paths, the one rule dialect Codex executes.

## Hooks

- The four hook behaviours ([[agentic-entities]]) are registered in `.codex/hooks.json` through wrappers under `.dadaia/hooks/codex-*`: `PreToolUse` the pre-gate (matcher `^(apply_patch|Edit|Write|Bash)$`), a matcher-less `PostToolUse` post-gate, `SessionStart` (`startup|resume`) ctx-inject plus the reaper, and `UserPromptSubmit` ctx-inject.
- Codex reads the gate's `decision: block`/`reason` envelope directly; the wrappers translate nothing ([[sdd-gate-v3]]).
- Whether hooks fire is `dadaia certify`'s `codex-live-probe` (a real `codex exec`), never the doctor's.

## Models and doctor

- Codex tier identity is native `(model id × model_reasoning_effort)`, derived from the model registry; two tiers collapsing to one pair fail loudly. The effort comes from one resolver: the D-3 clamp of the policy effort, else `medium`.
- `dadaia public doctor` keeps the structural checks byte comparison cannot express: `D-CX-7` (every `dd-` token a persona cites resolves to a skill or persona), `D-CX-8` (a Markdown file in `.codex/rules/` is flagged; the `.rules` file itself is a byte-compared rule) and `D-CX-9` (`hooks.json` names every wrapper command, and each wrapper exists and is executable).

## Dependencies

[[agentic-entities]], [[agent-orchestration]], [[sdd-gate-v3]], [[public-asset-distribution]].
