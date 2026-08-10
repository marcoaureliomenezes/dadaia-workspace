---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "No-lock SDD enforcement: deterministic path/mode gates, advisory presence, warn-only concurrent commits, and a security-gated push boundary."
summary: >-
  The merged Python PreToolUse gate enforces root whitelist, workspace venv usage,
  path class, phase, and the caller's own mode. It never waits for or blocks on another
  session. Presence is advisory. Git pre-commit warns only; pre-push enforces CI and an
  approved security handoff for every pushed commit.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
token_estimate: 552
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Purpose

The gate constrains unsafe writes without serializing agents. Races are accepted and
surfaced; no lease, mutex, lock file, incumbent pointer, acquisition, adoption, steal,
or wait path exists in the SDD concurrency design.

## PreToolUse

`dadaia_workspace.hooks.pre_gate` reads each tool payload once and evaluates three
policies in order, first block wins:

1. **root whitelist** blocks file-tool creation of forbidden workspace-root entries;
2. **venv guard** blocks leading Bash invocations of `dadaia`, `python -m
   dadaia_workspace`, or `pip` outside `.dadaia/.venv/bin/`;
3. **SDD gate** evaluates context-relative path class, phase, and caller-owned mode.

Path classes:

| Class | Behavior |
|---|---|
| ADDITIVE | `specs/bugs`, `specs/backlog`, `specs/audits`, and workspace reports/handoffs/tmp are writable. |
| MEMORY | Writable only in `DEFINITION` or `CLOSURE`. |
| FROZEN | Archived specs are never writable — archive by `git mv`. |
| PROTECTED | Session identity records and projected law files are fail-closed. |
| MUTATING | Writable unless this session explicitly resolves to READ mode. |

Mode resolution is environment, then this session's own record, then
`IMPLEMENTATION`. There is no context-global mode or foreign-session fallback. A READ
session blocks only its own mutating writes; it does not affect another session.

## Presence

A mutating write best-effort upserts
`.dadaia/states/presence/<context>/<session-id>.json`. Another live presence record
causes one throttled warning and never changes the verdict. Presence I/O failure is
swallowed. Stale records are removed opportunistically and by doctor.

The PostToolUse reconciler reports out-of-scope dirty paths and refreshes advisory
presence. It never blocks.

## Git Chokepoints

- `pre-commit-presence-gate.sh` may warn about another live session but always permits
  the commit on concurrency grounds.
- `pre-push-ci-gate.sh` runs the local CI preflight and requires an APPROVED
  `security-reviewer` handoff whose `metrics.commit_sha` equals every pushed commit.
  Branch deletion and tag-only updates are exempt.

The push rule is a quality gate, not a concurrency lock. Commits are never blocked for
missing review evidence; pushes are.

## Context Injection

`dadaia context bind` writes the caller's session record and a bind-epoch marker. The
marker is the only trigger for context-memory injection. An unbound session gets generic
preflight only. A foreign session's bind cannot alter this session's context or mode.

## Non-Goals

The hook does not read approval status, task markers, or task write sets. It constrains
**what** may be written, never **how** the change was produced — the ordered SDD
sequence is carried by the specs documents and upheld by the agents. It also does not
parse arbitrary shell strings; git chokepoints provide the independent commit/push
boundary.

## Runtime State

- `.dadaia/states/presence/<context>/<session-id>.json`
- `.dadaia/sessions/<session-id>.json`
- `.dadaia/states/bind_epoch/<context>`
- `.dadaia/logs/hook-latency.jsonl`
- `.dadaia/logs/reconciler-events.jsonl`

Legacy `.dadaia/states/ctx_locks/` and `.dadaia/sessions/runtime/` are retired residue;
doctor reports and removes them.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]].
