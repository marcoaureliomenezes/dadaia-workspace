---
slug: context-management
title: context-management
category: product
tldr: ALIVE/DEAD context registry, caller-owned session binding, bind-driven memory injection, and advisory presence with no concurrency locks.
summary: >-
  Manages Spec Context Projects and their repositories. Bind persists context and mode
  only for the caller, writes the bind-epoch injection marker, and never acquires a
  lock. Concurrent work is allowed and surfaced through expiring presence records.
tags:
- context
- lifecycle
- session
- no-locks
token_estimate: 424
last_updated: '2026-07-13'
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

## Binding

`dadaia context bind <context> --mode READ|IMPLEMENTATION|...` writes:

- the caller-owned record at `.dadaia/sessions/<session-id>.json`;
- the bind-epoch marker at `.dadaia/states/bind_epoch/<context>`.

The marker is the sole context-memory injection trigger. The bind command does not
write a context-global incumbent pointer and does not acquire anything. Context and mode
resolution consult only explicit environment values or the current harness session's
own record. If neither exists, path/cwd resolution applies and mutating mode defaults to
IMPLEMENTATION.

READ is opt-in self-protection: it blocks this session's mutating file-tool writes while
leaving additive intake paths writable. It cannot impose READ mode on another session.

## Presence

Mutating file-tool activity best-effort records advisory presence under
`.dadaia/states/presence/<context>/<session-id>.json`. Live peer presence produces a
warning, never a denial. Records expire by heartbeat age and are garbage-collected by
the gate and workspace doctor.

## Runtime State

- `.dadaia/states/spec_contexts.json` - context registry.
- `.dadaia/sessions/` - caller-owned binding records.
- `.dadaia/states/bind_epoch/` - context injection markers.
- `.dadaia/states/presence/` - advisory live-session records.
- `repos/<slug>/` - ALIVE repository checkout and canonical specs.

No `.dadaia/` directory may exist inside a repository.

## Dependencies

[[spec-context-project]], [[sdd-gate-v3]], [[workspace-doctor]], [[workspace-init]].
