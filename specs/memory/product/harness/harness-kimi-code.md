---
slug: harness-kimi-code
title: Harness — Kimi Code
category: product
tldr: 'Layer-1-only harness: `.kimi-code/` projection + user-level TOML hook shims; binds through `DADAIA_CONTEXT` at launch.'
summary: >-
  Kimi Code enters the workspace as a first-class Layer-1 harness. The projection
  tree is inert Markdown; the live wiring is four POSIX shims registered via a
  marker-delimited managed block of TOML hook rules in `$KIMI_CODE_HOME/config.toml`,
  delegating to the shared Python hook modules. Kimi exposes no session-id environment
  variable, so its context binding is `DADAIA_CONTEXT` exported at harness launch.
tags:
- harness
- kimi-code
- layer-1
- projection
- binding
last_updated: '2026-08-12'
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
compact-epoch marker plus an observable stdout re-emission of the bootstrap (Kimi
discards it; the next prompt still re-injects deterministically).

The shims fail open outside dadaia workspaces, carry no secrets and no
workspace-absolute paths, and are the only dadaia assets installed outside the
workspace tree. `dadaia public doctor` verifies the projection, the shims, and the
managed block. Generated `.kimi-code/**` files must not be hand-edited.

## Binding

Kimi Code exposes no session-id environment variable of its own, so its binding is
**`DADAIA_CONTEXT`, exported into the environment the `kimi` process is launched with** —
rung 1 of the resolution law ([[context-management]]), the same channel any non-harness
shell uses. With that variable set, all three effects follow from the shared authority:
the `UserPromptSubmit` shim injects the bound context's memory, the pre-gate shim
resolves the bind mode and attributes the write, and the post-gate shim's heartbeat
carries the context.

Running `dadaia context bind` from inside a kimi shell tool writes a session record the
kimi session cannot key back to, so `bind` prints its loud warning naming the export to
add. Exporting `DADAIA_CONTEXT` at launch is the supported flow; the consumer validation
recipe teaches it as the kimi profile.

## Post-compaction

Kimi is the first harness with deterministic post-compaction context re-injection:
the `PostCompact` hook stamps `.dadaia/tmp/ctx-compact-<session_id>`; the next
`UserPromptSubmit` treats the newer marker as a re-injection trigger and re-delivers
the bound context's bootstrap exactly once (sentinel restamp keeps later prompts
silent).

## Layer 2

None. Kimi built-in sub-agents
(`coder`/`explore`/`plan`) are a harness-native surface, not dadaia personas.

## Dependencies

[[workspace-init]], [[tech-stack]], [[sdd-gate-v3]], [[public-asset-distribution]],
[[harness-claude-code]].
