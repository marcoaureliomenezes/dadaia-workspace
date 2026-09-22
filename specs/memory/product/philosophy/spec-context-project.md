---
slug: spec-context-project
title: spec-context-project
tldr: One canonical specs tree owned by one main repository, optionally spanning associated repos, bound per session and safe for visible concurrent work.
summary: The central unit of dadaia-workspace — one main repository is the sole source of specs, bind, memory, releases and backlog, and associated repositories extend it without a second specs tree.
tags: [spec-context, sdd, lifecycle, concurrency]
sources:
  - dadaia_workspace/features/spec_context/**
  - dadaia_workspace/core/invocation.py
  - dadaia_workspace/cli/commands/context.py
---

## The unit

- A Spec Context Project is one canonical `specs/` tree owned by one main repository — the unit for memory, backlog, bugs, releases, reports and handoffs.
- A product spanning several repositories is still one project: the context carries associated repositories, added by `dadaia context repo add` and removed by `dadaia context repo remove`, which live and die with it.
- Specs, bind, memory, releases and backlog resolve only from the main repo; an associated repo's own `specs/` is never read.
- The main repository owns production source and `specs/`; an associated repository owns production source only.
- `dadaia context bind <ctx>` selects a context and nothing else, changing only the caller's own session record; a session without a harness-native id carries the binding in `DADAIA_CONTEXT`.
- A bind carries a scope — the context's main repo plus its associated repos — and a bound session's MUTATING write into a repo another context owns is refused with the bind that would allow it; an unbound session is never scope-judged ([[sdd-gate-v3]]).
- Context injection fires when the session record's `bound_at` is newer than that session's injection sentinel ([[context-management]]).
- No phase and no mode is enforced; concurrent sessions never block each other, and overlap surfaces through git.

## Runtime state

`.dadaia/states/spec_contexts.json`, `.dadaia/sessions/<session-id>.json`, `repos/<slug>/specs/`; runtime state stays at the workspace root, and a repo-local `.dadaia/` is always invalid.

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[ARCHITECTURE]].
