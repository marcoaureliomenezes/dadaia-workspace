---
slug: harness-devin
title: harness-devin
tldr: Entry harness on the Devin CLI — native AGENTS.md, .agents/skills and .agents/agents; its one projected file, .devin/hooks.v1.json, registers gate and reaper.
summary: Devin reads the universal surface including the personas natively, so its projection is only .devin/hooks.v1.json, which reads the gate's Claude-compatible envelope without translation.
tags: [harness, devin, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- Devin CLI is an entry harness reading the root `AGENTS.md` map, nested `AGENTS.md` files lazily on file access, `.agents/skills/` and `.agents/agents/` natively, so no persona copy is projected ([[agentic-entities]]).
- `dadaia harness add devin` projects one file, `.devin/hooks.v1.json`.

## Hooks

- The four hook behaviours ([[agentic-entities]]) arrive as `PreToolUse` -> the `.dadaia/hooks/devin-pre-gate` wrapper (the merged pre-gate) and `SessionStart` -> `devin-doctor-expired` (the reaper), each entry `type: command`.
- Devin reads the gate's Claude-compatible envelope and exit code, so the wrapper translates nothing ([[sdd-gate-v3]]).
- `dadaia certify`'s `devin-live-probe` checks that the `devin` binary answers `--version`, reporting SKIP `UNVERIFIED` when it is absent; no version floor.

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
