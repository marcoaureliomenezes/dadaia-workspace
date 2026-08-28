---
slug: spec-context-project
title: spec-context-project
category: product
tldr: One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work.
summary: The central unit of dadaia-workspace — one main repository is the sole source of specs, bind, memory, releases and backlog; associated repositories extend the project without a second specs tree.
tags:
- spec-context
- sdd
- lifecycle
- concurrency
---

## Purpose

A Spec Context Project is one canonical `specs/` tree owned by one **main** repository,
and is the unit used for memory, backlog, bugs, releases, reports and handoffs.

A product spanning several repositories is still one project: the context may carry
**associated repositories**, which live and die with it. The main repo stays unique and is
the single place of control — specs, bind, memory, releases and backlog resolve only from
it, and an associated repo's own `specs/` tree, if any, is never read by this context.

## Operating chain

1. **Bind** — the caller selects a context and mode; only its own session record changes.
   A session with a harness-native id is reached through that record; a plain shell or a
   harness without a session id carries the binding in `DADAIA_CONTEXT`.
2. **Inject** — the record's `bound_at`, newer than this session's injection sentinel,
   triggers memory and release-context loading.
3. **Enforce** — path/phase/mode gates and the git chokepoints constrain unsafe changes.
4. **Work concurrently** — presence warnings expose overlap and never block progress.

The main repository owns production source and `specs/`; an associated repository owns
production source only. Workspace runtime state stays at the workspace root under
`.dadaia/`; a repo-local `.dadaia/` is always invalid.

## Runtime state

`.dadaia/states/spec_contexts.json`, `.dadaia/sessions/<session-id>.json`,
`.dadaia/tmp/ctx-inject-fired-<session-id>`,
`.dadaia/states/presence/<context>/<session-id>.json`, `repos/<slug>/specs/`.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[architecture]].
