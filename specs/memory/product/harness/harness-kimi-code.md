---
slug: harness-kimi-code
title: Harness — Kimi Code
category: product
tldr: Layer-1 harness — inert `.kimi-code/` projection plus user-level TOML hook shims; binds through `DADAIA_CONTEXT` exported at launch.
summary: Kimi Code is a Layer-1 entry harness whose live wiring is four POSIX shims registered in a managed block of the user-level Kimi config; it binds through DADAIA_CONTEXT.
tags: [harness, kimi-code, layer-1, projection, binding]
---

## Projection, hooks and binding

- Kimi Code is a Layer-1 entry harness and an operator-installed external CLI (`kimi`), never a Python dependency.
- `.kimi-code/` is a generated projection of inert Markdown — an `AGENTS.md` orientation file plus its own copy of the law, read once per session.
- Kimi Code has no project-level config, so hook registration lives in a managed, marker-delimited block inside the user-level `$KIMI_CODE_HOME/config.toml`.
- Four shims under `$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` resolve the nearest `.dadaia/.venv/bin/python` up from the hook cwd and delegate to the shared hook modules.
- They map `PreToolUse` to the merged pre-gate (a block exits 2 with the reason on stderr), `PostToolUse` to the heartbeat, `UserPromptSubmit` to ctx-inject, `PostCompact` to a compact-epoch marker plus re-emission.
- They fail open outside dadaia workspaces and are the only dadaia assets installed outside the workspace tree.
- `dadaia public doctor` verifies the projection, the shims and the block ([[public-asset-distribution]]).
- Kimi Code exposes no session-id variable, so its binding is `DADAIA_CONTEXT` exported into the launching environment — rung 1 ([[context-management]]).
- With it set, the injection shim delivers the bound memory, the pre-gate resolves mode and attributes the write, and the heartbeat carries the context.
- `dadaia context bind` inside a kimi shell writes a record the session cannot key back to, so it warns and names the export to add.

## Dependencies

[[workspace-init]], [[tech-stack]], [[sdd-gate-v3]], [[harness-claude-code]].
