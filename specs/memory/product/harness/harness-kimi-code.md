---
slug: harness-kimi-code
title: harness-kimi-code
tldr: "Entry harness with an empty projection: reads root AGENTS.md, .agents/skills and .agents/agents natively; user-level hook shims; DADAIA_CONTEXT binds."
summary: Kimi Code consumes the universal surface directly and projects nothing into the workspace; its hooks are a managed block and shims in the user-level Kimi home, and its session binds through an exported DADAIA_CONTEXT.
tags: [harness, kimi-code, hooks, binding]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/runtime_config.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Load path

- Kimi Code is an entry harness and an operator-installed external CLI (`kimi`), never a Python dependency.
- It reads the root `AGENTS.md` map, the root->cwd `AGENTS.md` chain, `.agents/skills/` and `.agents/agents/` (Claude-style Markdown) natively, so its workspace projection is empty; scoped law outside the chain reaches it by skill procedure ([[agentic-entities]]).

## Hooks

- Kimi Code has no project-level hook config, so registration is a managed, marker-delimited block in the user-level `$KIMI_CODE_HOME/config.toml` (default `~/.kimi-code/config.toml`); content outside the markers is never touched.
- Five shims under `$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` carry the four hook behaviours ([[agentic-entities]]): `PreToolUse` (`^(Edit|Write|Bash)$`) the merged pre-gate, `PostToolUse` the throttled reaper, `UserPromptSubmit` ctx-inject, `PostCompact` bootstrap re-emission, `SessionStart` `dadaia doctor --fix --expired-only --quiet`.
- Each shim resolves the nearest `.dadaia/.venv/bin/python` up from the hook cwd, so one global block serves every workspace and fails open outside one; a gate block exits 2 with the reason on stderr ([[sdd-gate-v3]]).
- The shims and the block are the only dadaia assets installed outside the workspace tree; `dadaia public doctor` compares them with their renderers.
- `dadaia certify`'s `kimi-code-live-probe` checks that `kimi` answers `--version`, reporting SKIP `UNVERIFIED` when it is absent.

## Binding

- Kimi Code exposes no native session id, so its binding is `DADAIA_CONTEXT` exported into the launching environment ([[context-management]]).
- `dadaia context bind` in a shell with neither a native session id nor `DADAIA_CONTEXT` warns and names the export (`eval $(dadaia context bind <ctx> --print-env)`).

## Dependencies

[[agentic-entities]], [[context-management]], [[sdd-gate-v3]], [[public-asset-distribution]], [[workspace-init]].
