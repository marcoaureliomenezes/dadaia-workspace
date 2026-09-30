---
slug: harness-copilot
title: harness-copilot
tldr: Entry harness on GitHub Copilot CLI — native root AGENTS.md and .agents/skills; .github/ carries agent transcodes and two hook files, bootstrap at start.
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

- The four hook behaviours ([[agentic-entities]]) arrive as two files in the workspace root's `.github` hooks directory, entry key `bash`, `version: 1`: `pre-tool-use.json` (`preToolUse` -> the `copilot-pre-gate` wrapper) and `session-start.json` (`sessionStart` -> `copilot-ctx-inject`, then `copilot-doctor-expired`, the reaper).
- ctx-inject answers in Copilot's `additionalContext` JSON: the bound context's bootstrap, `constitution.md` included ([[context-management]]); there is no prompt-time injection, so a bind shows at the next session start.
- Copilot exposes no native session id: a session binds by exporting `DADAIA_SESSION_ID` (then `context bind`) or `DADAIA_CONTEXT` into its launching environment.
- Copilot decides by stdout JSON, so the wrapper answers only a deny, remapped to `{"permissionDecision": "deny", "permissionDecisionReason": <reason>}`; an allow emits nothing ([[sdd-gate-v3]]).
- `dadaia certify`'s `copilot-live-probe` checks that the `copilot` binary answers `--version`, reporting SKIP `UNVERIFIED` when it is absent; no version floor.

## Dependencies

[[agentic-entities]], [[public-asset-distribution]], [[sdd-gate-v3]], [[context-management]], [[workspace-init]].
