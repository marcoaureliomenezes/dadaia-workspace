---
slug: harness-copilot
title: harness-copilot
tldr: Entry harness on GitHub Copilot CLI — native root AGENTS.md and .agents/skills; .github/ carries agents/*.agent.md transcodes and two hook files.
summary: Copilot reads the universal surface natively; its projection is the three dd- personas as .github/agents/*.agent.md and two hook files answered in Copilot's permissionDecision JSON, and nothing else under .github/.
tags: [harness, copilot, projection, hooks]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/agent_transcodes.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Surface

- GitHub Copilot CLI is an entry harness reading the root `AGENTS.md` map, ancestor `AGENTS.md` files of touched paths and `.agents/skills/` natively ([[agentic-entities]]).
- `dadaia harness add copilot` renders `.github/agents/dd-*.agent.md` from the authored personas — frontmatter reduced to `name`, `description`, `tools`, body verbatim, compared byte-wise.
- `.github/` is shared with a repository's own workflows: the projection owns only `agents/*.agent.md` and `hooks/*.json` and never touches anything else there.

## Hooks

- The four hook behaviours ([[agentic-entities]]) arrive as two files in the workspace root's `.github` hooks directory, entry key `bash`, `version: 1`: `pre-tool-use.json` (`preToolUse` -> the `copilot-pre-gate` wrapper) and `session-start.json` (`sessionStart` -> `copilot-doctor-expired`, the reaper).
- Copilot decides by stdout JSON, so the wrapper remaps the gate's envelope to `{"permissionDecision": allow|deny, "permissionDecisionReason"}` ([[sdd-gate-v3]]).
- `dadaia certify`'s `copilot-live-probe` checks that the `copilot` binary answers `--version`, reporting SKIP `UNVERIFIED` when it is absent; no version floor.

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[workspace-init]].
