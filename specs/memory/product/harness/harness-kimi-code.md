---
slug: harness-kimi-code
title: Harness — Kimi Code
category: product
tldr: 'Layer-1-only harness: `.kimi-code/` projection + hooks via a managed block in the user-level `config.toml`; first with post-compact re-injection.'
summary: >-
  Kimi Code enters the workspace as a first-class Layer-1 harness. The projection
  tree is inert Markdown; the live wiring is four POSIX shims registered via a
  marker-delimited managed block of TOML hook rules in `$KIMI_CODE_HOME/config.toml`,
  delegating to the shared Python hook modules. Layer-2 workers remain codex/pi only.
tags:
- harness
- kimi-code
- layer-1
- projection
token_estimate: 400
last_updated: '2026-07-19'
release_origin: v0.2.8
---

## Purpose

Kimi Code is a Layer-1 entry harness (never a Layer-2 worker). It is an
operator-installed external CLI (`kimi`), not a Python package dependency.

## Layer 1

`.kimi-code/` is a generated projection whose workspace tree is inert Markdown
(`AGENTS.md` orientation). Kimi Code has no project-level config file, so the hook
registration lives in the user-level `$KIMI_CODE_HOME/config.toml` inside a managed,
marker-delimited block of TOML hook rules written by `dadaia public install --target
kimi-code`. Four shims under `$KIMI_CODE_HOME/hooks/dadaia-kimi-*.sh` resolve the
nearest `.dadaia/.venv/bin/python` walking up from the hook cwd and delegate to the
same Python hook modules the other harnesses use: `PreToolUse` → merged pre-gate
(block ⇒ exit 2 with the reason on stderr), `PostToolUse` → presence heartbeat,
`UserPromptSubmit` → ctx-inject (stdout is appended to context), `PostCompact` →
compact-epoch marker.

Kimi is the first harness with deterministic post-compaction context re-injection:
the `PostCompact` hook stamps `.dadaia/tmp/ctx-compact-<session_id>`; the next
`UserPromptSubmit` treats the newer marker as a re-injection trigger and re-delivers
the bound context's bootstrap exactly once (sentinel restamp keeps later prompts
silent).

The shims fail open outside dadaia workspaces, carry no secrets and no
workspace-absolute paths, and are the only dadaia assets installed outside the
workspace tree. `dadaia public doctor` verifies the projection, the shims, and the
managed block. Generated `.kimi-code/**` files must not be hand-edited.

## Layer 2

None. Layer-2 workflow workers stay `codex`/`pi`. Kimi built-in sub-agents
(`coder`/`explore`/`plan`) are a harness-native surface, not dadaia personas.

## Dependencies

[[workspace-init]], [[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]],
[[harness-claude-code]].
