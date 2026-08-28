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

## The unit

A Spec Context Project is one canonical `specs/` tree owned by one **main** repository, and is the
unit used for memory, backlog, bugs, releases, reports and handoffs. A product spanning several
repositories is still one project: the context may carry **associated repositories**, which live and
die with it. The main repo stays unique and is the single place of control — specs, bind, memory,
releases and backlog resolve only from it, and an associated repo's own `specs/` tree, if any, is
never read by this context. The main repository owns production source and `specs/`; an associated
repository owns production source only.

The operating chain is bind → inject → enforce → work concurrently. **Bind** selects a context and
mode, changing only the caller's own session record; a session with a harness-native id is reached
through that record, while a plain shell or a harness without a session id carries the binding in
`DADAIA_CONTEXT`. **Inject** fires when that record's `bound_at` is newer than this session's
injection sentinel. **Enforce** is the path/phase/mode gate plus the git chokepoints. **Concurrent
work** surfaces overlap through presence warnings and never blocks progress.

## Runtime state

`.dadaia/states/spec_contexts.json`, `.dadaia/sessions/<session-id>.json`,
`.dadaia/tmp/ctx-inject-fired-<session-id>`,
`.dadaia/states/presence/<context>/<session-id>.json`, `repos/<slug>/specs/`. Workspace runtime
state stays at the workspace root under `.dadaia/`; a repo-local `.dadaia/` is always invalid.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[architecture]].
