---
slug: harness-cursor
title: harness-cursor
tldr: Entry harness on Cursor — native root AGENTS.md and .agents/skills; .cursor/hooks.json gates every tool, injects and reaps at start; persona symlinks.
summary: Cursor reads the universal surface natively; its projection is the dd- personas as relative symlinks under .cursor/agents/ and one hooks.json whose gate wrapper answers a deny in Cursor's permission JSON and whose session-start ctx-inject carries the bound context's bootstrap.
tags: [harness, cursor, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- Cursor (IDE and `cursor-agent` CLI) is an entry harness reading the root `AGENTS.md` map, the `AGENTS.md` of any file's subtree and `.agents/skills/` natively ([[agentic-entities]]).
- `dadaia harness add cursor` projects `.cursor/agents/dd-*.md` as relative symlinks onto `.agents/agents/dd-*.md` (hash-verified copy fallback) and `.cursor/hooks.json` (`version: 1`).

## Hooks

- The four hook behaviours ([[agentic-entities]]) arrive through three wrappers under `.dadaia/hooks/cursor-*`: `preToolUse` -> the merged pre-gate, and `sessionStart` -> ctx-inject, then the reaper.
- ctx-inject answers in Cursor's `additional_context` JSON: the bound context's bootstrap, `constitution.md` included ([[context-management]]); there is no prompt-time injection, so a bind shows at the next session start.
- Cursor exposes no native session id: a session binds by exporting `DADAIA_SESSION_ID` (then `context bind`) or `DADAIA_CONTEXT` into its launching environment.
- Cursor decides by stdout JSON, so the wrapper answers only a deny, remapped to `{"permission": "deny", "agent_message": <reason>}`; an allow emits nothing and Cursor's own approval stays in force ([[sdd-gate-v3]]).
- `dadaia certify`'s `cursor-live-probe` checks that `cursor-agent` answers `--version`, reporting SKIP `UNVERIFIED` when it is absent from PATH; no version floor.

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[context-management]], [[workspace-init]].
