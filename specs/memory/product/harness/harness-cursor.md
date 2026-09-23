---
slug: harness-cursor
title: harness-cursor
tldr: Entry harness on Cursor — native root AGENTS.md and .agents/skills; .cursor/ carries hooks.json (gate on shell, reaper at session start) and persona symlinks.
summary: Cursor reads the universal surface natively; its projection is the dd- personas as relative symlinks under .cursor/agents/ and one hooks.json whose wrappers answer in Cursor's permission JSON; IDE file edits are not gated.
tags: [harness, cursor, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- Cursor (IDE and `cursor-agent` CLI) is an entry harness reading the root `AGENTS.md` map, the `AGENTS.md` of any file's subtree and `.agents/skills/` natively ([[agentic-entities]]).
- `dadaia harness add cursor` projects `.cursor/agents/dd-*.md` as relative symlinks onto `.agents/agents/dd-*.md` (hash-verified copy fallback, attested by `SYMLINK-TARGET-1`) and `.cursor/hooks.json` (`version: 1`).

## Hooks

- The four hook behaviours ([[agentic-entities]]) arrive through two wrappers under `.dadaia/hooks/cursor-*`: `beforeShellExecution` -> the merged pre-gate and `sessionStart` -> the reaper.
- Cursor decides by stdout JSON, so the wrapper remaps the gate's envelope to `{"permission": allow|deny, "user_message"}` ([[sdd-gate-v3]]).
- Cursor's file-edit event fires after the write, so IDE file edits are ungated; the gap is declared in the registry's `sdd-gate` implementation row.
- `dadaia certify`'s `cursor-live-probe` checks that `cursor-agent` answers `--version`, reporting SKIP `UNVERIFIED` when it is absent from PATH; no version floor.

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
