---
slug: harness-kimi-code
title: Harness — Kimi Code
category: product
tldr: Layer-1 harness — inert `.kimi-code/` projection plus user-level TOML hook shims; binds through `DADAIA_CONTEXT` exported at launch.
summary: Kimi Code is a Layer-1 entry harness whose live wiring is four POSIX shims registered in a managed block of `$KIMI_CODE_HOME/config.toml`; it binds through `DADAIA_CONTEXT`.
tags:
- harness
- kimi-code
- layer-1
- projection
- binding
---

## Purpose

Kimi Code is a Layer-1 entry harness and an operator-installed external CLI (`kimi`),
never a Python dependency.

## Projection and hooks

`.kimi-code/` is a generated projection of inert Markdown — an `AGENTS.md` orientation
file plus its own copy of the law, reached exactly once per session. Kimi Code has no
project-level config file, so hook registration lives in a managed, marker-delimited
block of TOML hook rules inside the user-level `$KIMI_CODE_HOME/config.toml`, written by
`dadaia public install --target kimi-code`. Four shims under
`$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` resolve the nearest `.dadaia/.venv/bin/python`
walking up from the hook cwd and delegate to the shared Python hook modules:

| Event | Delegate |
|---|---|
| `PreToolUse` | merged pre-gate — a block exits 2 with the reason on stderr |
| `PostToolUse` | presence heartbeat |
| `UserPromptSubmit` | ctx-inject; stdout is appended to context |
| `PostCompact` | compact-epoch marker plus a bootstrap re-emission on stdout |

The shims fail open outside dadaia workspaces, carry no secrets and no
workspace-absolute paths, and are the only dadaia assets installed outside the workspace
tree. `dadaia public doctor` verifies the projection, the shims and the managed block.

## Binding

Kimi Code exposes no session-id environment variable, so its binding is `DADAIA_CONTEXT`
exported into the environment `kimi` is launched with — rung 1 of the resolution law
([[context-management]]). With it set, the `UserPromptSubmit` shim injects the bound
context's memory, the pre-gate shim resolves mode and attributes the write, and the
heartbeat carries the context. `dadaia context bind` run inside a kimi shell writes a
session record the kimi session cannot key back to, so it prints a warning naming the
export to add.

## Post-compaction

`PostCompact` stamps `.dadaia/tmp/ctx-compact-<session_id>`; the next `UserPromptSubmit`
treats the newer marker as a re-injection trigger and re-delivers the bootstrap once
(the sentinel restamp keeps later prompts silent).

## Layer 2

None. Kimi's built-in sub-agents (`coder`/`explore`/`plan`) are a harness-native surface,
not dadaia personas.

## Dependencies

[[workspace-init]], [[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]],
[[harness-claude-code]].
