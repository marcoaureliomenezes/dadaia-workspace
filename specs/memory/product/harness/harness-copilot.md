---
slug: harness-copilot
title: harness-copilot
tldr: Entry harness on GitHub Copilot CLI — native root AGENTS.md and .agents/skills; .github/ carries agents/*.agent.md transcodes and two hook files.
summary: Copilot is a registry record (.github, copilot-agent-md, copilot-hooks) — personas render to .github/agents/<name>.agent.md (frontmatter name/description/tools + verbatim body), the four behaviours to two hook files answered in Copilot's permissionDecision JSON; nothing else under .github/ is projected.
tags: [harness, copilot, projection, hooks]
---

## Surface

- GitHub Copilot CLI is an entry harness — `HarnessRecord("copilot", ".github", copilot-agent-md, copilot-hooks)` — reading the root `AGENTS.md` map, ancestor `AGENTS.md` on file touch and `.agents/skills/` natively (research 2026-09-20).
- `dadaia harness add copilot` renders `.github/agents/dd-*.agent.md` from the authored personas (frontmatter reduced to `name`, `description`, `tools`; body verbatim — a transcode, byte-compared like a Codex TOML) and two hook files in its `hooks/` subdirectory — `pre-tool-use.json` (`preToolUse` -> the `copilot-pre-gate` wrapper) and `session-start.json` (`sessionStart` -> `copilot-doctor-expired`) — entry key `bash`, `version: 1`.
- `.github/` is shared with a repository's own workflows: the projection owns only `agents/*.agent.md` and `hooks/*.json`, never lists or touches anything else there.
- Copilot decides by stdout JSON, so the wrapper remaps the gate's envelope to `{"permissionDecision": allow|deny, "permissionDecisionReason"}`; the behaviours stay the workspace's four ([[agentic-entities]]).
- `dadaia certify`'s `copilot-live-probe` reports SKIP `UNVERIFIED` when the `copilot` binary is absent, no version floor ([[TECHSTACK]]).

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
