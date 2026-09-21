---
slug: harness-devin
title: harness-devin
tldr: Entry harness on the Devin CLI — native AGENTS.md, .agents/skills and .agents/agents; .devin/hooks.v1.json registers gate and reaper, Claude-compatible.
summary: Devin is a registry record (.devin, devin-md, devin-hooks) whose persona transcode projects nothing because Devin reads .agents/agents natively; its only projected file is .devin/hooks.v1.json, which reads the gate's native envelope without translation.
tags: [harness, devin, projection, hooks]
---

## Surface

- Devin CLI is an entry harness — `HarnessRecord("devin", ".devin", devin-md, devin-hooks)` — reading the root `AGENTS.md` map, nested `AGENTS.md` lazily on file access, `.agents/skills/` and `.agents/agents/` natively (research 2026-09-20), so its persona transcode yields zero rules and no duplicate persona copy exists.
- `dadaia harness add devin` projects one file, `.devin/hooks.v1.json`: `PreToolUse` -> the `.dadaia/hooks/devin-pre-gate` wrapper (merged `pre_gate`), `SessionStart` -> `devin-doctor-expired` (the reaper), each entry `type: command`; Devin reads the gate's Claude-compatible envelope and exit code, so the wrapper translates nothing.
- The four behaviours it implements are the workspace's — root whitelist, venv guard, SDD gate, session-start reaper — no more ([[agentic-entities]]).
- `dadaia certify`'s `devin-live-probe` reports SKIP `UNVERIFIED` when the `devin` binary is absent, no version floor ([[TECHSTACK]]).

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
