---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD context registry, one resolution authority (three law rungs), bind-driven injection, advisory presence.
summary: >-
  Manages Spec Context Projects and their repositories. A single resolution function
  answers "which context is this?" for every verb, hook and gate; bind persists context
  and mode only for the caller and never acquires a lock. Concurrent work is allowed and
  surfaced through expiring presence records. `list` and `show` accept `--redact` to mask
  foreign context names in table and JSON output.
tags:
- context
- lifecycle
- session
- no-locks
- privacy
last_updated: '2026-08-14'
release_origin: v0.2.3
---

## Purpose

A Spec Context Project binds one canonical `specs/` tree to one repository. The
workspace registry stores name, repo slug, repo URL, state, branch, and lifecycle
timestamps. There is no global primary context.

## Lifecycle

- `context create` registers a DEAD context.
- `context alive` clones when necessary, restores the recorded branch, merges missing
  scaffold files without overwriting existing files, and marks the context ALIVE.
- `context dead` requires a reviewable clean transition, scans newly committed material
  for secrets when `--commit` is used, records the branch, and removes the local repo.
- `context update --url` repairs the remote URL. Alive/dead also backfill an absent URL
  from the repository origin when available.

Concurrent alive/dead races are not serialized. Operations are idempotent where
possible and surface ordinary filesystem/Git conflicts instead of waiting on a lock.

## Resolution

`core.specs_resolver.resolve_context()` is the single authority that answers "which
context is this?". Every consumer — the CLI seam, `container`, the SDD gate and the
ctx-inject hook — calls that one function, and the law it implements is its docstring:

| Rung | Input | Meaning |
|---|---|---|
| 0 | caller-supplied | the `--context` flag, or the context derived from an explicit write **target** under `repos/<slug>/` |
| 1 | `DADAIA_CONTEXT` | the environment binding |
| 2 | this session's own **live** record | keyed by the harness-native session id |
| 3 | the repo containing the cwd | `repos/<slug>/…` |

Rungs 1–3 are the law's three rungs in the law's order. Rung 0 is the caller's explicit
input, which is why a write into `repos/x/` is attributed to `x` even while
`DADAIA_CONTEXT=y` — the gate keeps path-first attribution by passing the write target.
Rungs 0 and 3 resolve a repo slug and then recover the context NAME through the
registry, falling back to the slug when it is unregistered. Every rung fails soft;
resolution returns nothing only when all four are exhausted, and `resolve_specs_dir`
then raises rather than guessing from the cwd.

`DADAIA_CONTEXT` is the only environment variable that participates in resolution.
`DADAIA_MODE` carries mode, and `WORKSPACE_ROOT` / `DADAIA_RUNTIME` /
`DADAIA_HOOK_OUTPUT` / `DADAIA_HOOK_EVENT` are hook transport; none of them resolves a
context.

## Binding

`dadaia context bind <context> --mode READ|IMPLEMENTATION|...` writes exactly one
artifact: the caller-owned record at `.dadaia/sessions/<session-id>.json`, carrying the
context, the mode and a `bound_at` timestamp. It writes no context-global incumbent
pointer and acquires nothing.

That record is reachable at rung 2 only when it is keyed by the session's own
harness-native id. When the shell has neither a harness-native session id nor
`DADAIA_CONTEXT`, `bind` prints a loud warning saying the binding is reachable only if
`DADAIA_CONTEXT=<context>` is exported — for a plain shell, and for a harness that
exposes no session id of its own, the environment variable **is** the binding (rung 1).
`bind --print-env` emits that export line.

The record's `bound_at` is also the sole context-memory injection trigger: ctx-inject
re-injects when this session's own `bound_at` is newer than its injection sentinel, so a
re-bind — including a re-bind to the same context — delivers the changed mode or release
to a live session.

READ is opt-in self-protection: it blocks this session's mutating file-tool writes while
leaving additive intake paths writable. It cannot impose READ mode on another session.

## Redacted Output

`context list` and `context show` accept `--redact` in both their table and `--json`
forms, including the `presence` block. Every context name and repo slug other than the
caller's resolved context is replaced by a stable `[REDACTED-CONTEXT-<n>]` placeholder,
ordinal by first appearance within one invocation, so the same foreign context carries
the same placeholder everywhere it appears in that output. The caller's own context stays
visible. Redaction applies at the render boundary only — the registry and services keep
returning true names, the default output is unchanged, and the redacted `--json` remains
valid JSON with the same key set, so a machine consumer's parsing contract does not
change. The purpose is authoring hygiene: output pasted into a document must not carry a
foreign Spec Context name ([[quality-assurance]]).

## Presence

Mutating file-tool activity best-effort records advisory presence under
`.dadaia/states/presence/<context>/<session-id>.json`. Live peer presence produces a
warning, never a denial. Records expire by heartbeat age and are garbage-collected by
the gate and workspace doctor.

## Runtime State

- `.dadaia/states/spec_contexts.json` - context registry.
- `.dadaia/sessions/` - caller-owned binding records (context, mode, `bound_at`).
- `.dadaia/states/presence/` - advisory live-session records.
- `.dadaia/tmp/ctx-inject-fired-<session-id>` - per-session injection sentinel.
- `repos/<slug>/` - ALIVE repository checkout and canonical specs.

No `.dadaia/` directory may exist inside a repository.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]],
[[quality-assurance]].
