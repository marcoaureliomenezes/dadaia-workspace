---
slug: harness-cursor
title: harness-cursor
tldr: Entry harness on Cursor — native root AGENTS.md and .agents/skills; .cursor/ carries hooks.json (gate + reaper) and persona symlinks.
summary: Cursor is a registry record (.cursor, cursor-md, cursor-hooks) — the personas reach it as relative symlinks under .cursor/agents/, the four behaviours as wrappers cited by .cursor/hooks.json, answered in Cursor's permission JSON.
tags: [harness, cursor, projection, hooks]
---

## Surface

- Cursor (IDE and `cursor-agent` CLI) is an entry harness — `HarnessRecord("cursor", ".cursor", cursor-md, cursor-hooks)` — reading the root `AGENTS.md` map, the `AGENTS.md` of any file's subtree and `.agents/skills/` natively (research 2026-09-20).
- `dadaia harness add cursor` projects `.cursor/agents/dd-*.md` as relative symlinks onto `.agents/agents/dd-*.md` (hash-verified copy fallback, `SYMLINK-TARGET-1`) and `.cursor/hooks.json` (`version: 1`).
- `hooks.json` cites two wrappers under `.dadaia/hooks/cursor-*`: `beforeShellExecution` -> the merged `pre_gate` (root whitelist, venv guard, SDD gate) and `sessionStart` -> the expired-state reaper; Cursor decides by stdout JSON, so the wrapper remaps the gate's native envelope to `{"permission": allow|deny, "user_message"}` — the adapter is the wrapper, never a fifth behaviour.
- Cursor's file-edit event fires after the write, so the IDE edit lane is ungated by Cursor's own vocabulary; the gap is stated in the entity registry's `sdd-gate` row, not hidden.
- `dadaia certify`'s `cursor-live-probe` reports SKIP `UNVERIFIED` when `cursor-agent` is absent from PATH, no version floor ([[TECHSTACK]]).

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
