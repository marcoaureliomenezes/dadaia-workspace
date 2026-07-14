---
slug: spec-context-project
title: spec-context-project
category: product
tldr: One canonical specs tree plus one repository, explicitly bindable by each session and safe for visible concurrent work.
summary: >-
  The central unit of dadaia-workspace. Binding selects the project and injects its
  current memory for the caller; the SDD gate and workflows constrain writes while
  advisory presence surfaces concurrent sessions without locking them out.
tags:
- spec-context
- sdd
- lifecycle
- concurrency
token_estimate: 185
last_updated: '2026-07-13'
release_origin: v0.2.3
---

## Purpose

A Spec Context Project is one canonical `specs/` tree bound to one repository. It is
the unit used for memory, backlog, bugs, releases, workflow execution, reports, and
handoffs.

## Operating Chain

1. **Bind** - the caller selects a context and mode; only its own session record changes.
2. **Inject** - the bind-epoch marker triggers current memory and release-context loading.
3. **Enforce** - deterministic path/phase/mode gates and the four workflows constrain
   unsafe changes.
4. **Work concurrently** - other sessions may use the same or different contexts;
   presence warnings expose overlap but never block progress.

The repository owns production source and `specs/`. Workspace runtime state remains at
the workspace root under `.dadaia/`; a repo-local `.dadaia/` is always invalid.

## Runtime State

- `.dadaia/states/spec_contexts.json`
- `.dadaia/sessions/<session-id>.json`
- `.dadaia/states/bind_epoch/<context>`
- `.dadaia/states/presence/<context>/<session-id>.json`
- `repos/<slug>/specs/`

## Dependencies

[[context-management]], [[sdd-gate-v3]], [[dadaia-workflows]], [[architecture]].
