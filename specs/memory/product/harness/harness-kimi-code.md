---
slug: harness-kimi-code
title: harness-kimi-code
tldr: Layer-1 harness with an empty projection set — reads root AGENTS.md, .agents/skills and .agents/agents natively; user-level hook shims; DADAIA_CONTEXT binding.
summary: Kimi Code consumes the universal authored set directly; the .kimi-code/ mirror died at 0.4.7 candidate 6 (ADR 0017). Hooks stay user-level shims; binding is the exported DADAIA_CONTEXT.
tags: [harness, kimi-code, hooks, binding]
sources:
  - dadaia_workspace/core/harness_registry.py
  - dadaia_workspace/infrastructure/runtime_config.py
  - dadaia_workspace/infrastructure/runtime_transforms/hook_wrappers.py
---

## Load path, hooks and binding

- Kimi Code is a Layer-1 entry harness and an operator-installed external CLI (`kimi`), never a Python dependency.
- It reads the root `AGENTS.md` map and the root->cwd `AGENTS.md` chain natively, `.agents/skills/` and `.agents/agents/` (Claude-style Markdown) natively: its own projection set is empty, and `.kimi-code/` no longer exists; the standalone dd- skills reach a Kimi user without a workspace through `npx skills add marcoaureliomenezes/dadaia-skills` into `.agents/skills` ([[public-asset-distribution]]).
- A scoped `AGENTS.md` outside the cwd chain reaches it by procedure: every dd- skill opens its area's scoped law as step 1 ([[agentic-entities]]).
- Kimi Code has no project-level hook config, so hook registration lives in a managed, marker-delimited block inside the user-level `$KIMI_CODE_HOME/config.toml`.
- Shims under `$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` resolve the nearest `.dadaia/.venv/bin/python` up from the hook cwd and delegate to the shared hook modules: `PreToolUse` to the merged pre-gate (a block exits 2 with the reason on stderr), `PostToolUse` to the throttled reaper, `UserPromptSubmit` to ctx-inject, `PostCompact` to re-emission, `SessionStart` to `dadaia doctor --fix --expired-only --quiet`.
- They fail open outside dadaia workspaces and are the only dadaia assets installed outside the workspace tree; `dadaia public doctor` verifies the shims and the block.
- Kimi Code exposes no session-id variable, so its binding is `DADAIA_CONTEXT` exported into the launching environment — rung 1 ([[context-management]]); `dadaia context bind` inside a kimi shell warns and names the export to add.
- Native-read verification is deferred until a provider is configured on the operator's machine (2026-09-20: `kimi provider list` empty); the load path is source-verified (`load_agents_md`).

## Dependencies

[[workspace-init]], [[ARCHITECTURE]], [[sdd-gate-v3]], [[harness-claude-code]].
