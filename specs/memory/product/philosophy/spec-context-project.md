---
slug: spec-context-project
title: spec-context-project
category: product
tldr: One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work.
summary: The central unit of dadaia-workspace — one main repository is the sole source of specs, bind, memory, releases and backlog, and associated repositories extend it without a second specs tree.
tags: [spec-context, sdd, lifecycle, concurrency]
---

## The unit

- A Spec Context Project is one canonical `specs/` tree owned by one main repository — the unit for memory, backlog, bugs, releases, reports and handoffs.
- A product spanning several repositories is still one project: the context may carry associated repositories, which live and die with it.
- Specs, bind, memory, releases and backlog resolve only from the main repo, an associated repo's own `specs/` never being read.
- The main repository owns production source and `specs/`; an associated repository owns production source only.
- Bind selects a context and mode, changing only the caller's own session record; a session without a harness-native id carries the binding in `DADAIA_CONTEXT` instead.
- Injection fires when that record's `bound_at` is newer than this session's injection sentinel.
- Enforcement is the path/phase/mode gate plus the git chokepoints, and concurrent work surfaces overlap through presence warnings without blocking.

## Runtime state

`.dadaia/states/spec_contexts.json`, `.dadaia/sessions/<session-id>.json`, `.dadaia/states/presence/`, `repos/<slug>/specs/`; runtime state stays at the workspace root, a repo-local `.dadaia/` always being invalid.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[architecture]].
