---
slug: sdd-gate-v3
title: sdd-gate-v3
category: product
tldr: "No-lock SDD enforcement: deterministic path/mode gates, advisory presence, warn-only concurrent commits, and a develop-only, security-gated push boundary."
summary: >-
  The merged Python PreToolUse gate enforces root whitelist, workspace venv usage,
  path class, phase, and the caller's own mode. It never waits for or blocks on another
  session. Presence is advisory. Git pre-commit warns only; pre-push enforces the CI
  preflight, develop-only branch policy, and a security verdict covering the develop delta.
tags:
- sdd
- gate
- hooks
- enforcement
- no-locks
token_estimate: 760
last_updated: '2026-08-12'
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

## Context Attribution

The gate does not carry a resolution ladder of its own. It calls the shared authority
`core.specs_resolver.resolve_context()` ([[context-management]]) and passes the write's
target path as the caller-supplied input, which keeps attribution **path-first**: a
write under `repos/<slug>/` is attributed to that slug's context even when
`DADAIA_CONTEXT` names another. A write under no repo falls through the remaining law
rungs — the environment, then this session's own live record, then the repo containing
the working directory — so a demonstrably bound session's out-of-repo write belongs to
its own context. The slug reaching the classifier is mapped back to the context NAME
through the registry.

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
- `pre-push-ci-gate.sh` runs the local CI preflight and then applies branch policy and the
  security verdict, in that order.

Branch policy at the push boundary: `refs/heads/develop` is the only pushable ref. A push
of `main` is refused and named as PR-only from `develop`; a push of a `feature/*` or
`hotfix/*` ref is refused as local-only; a ref outside the four permitted patterns
(`main`, `develop`, `feature/vM.m.p`, `hotfix/vM.m.p` with PATCH ≥ 1) is refused by the
branch-name validator; a local ref that is not a branch head gets its own diagnosis. The
remote side is policed too — a refspec aiming local `develop` at another remote ref is
refused, so only `refs/heads/develop → refs/heads/develop` passes. Parsing is fail-closed:
any unparseable stdin line refuses the whole push and the message names `git push
--no-verify` as the one traceable bypass, while empty stdin remains the distinct
"nothing to gate" allow. Tag pushes and branch deletions keep their carve-out, which is
what release publication depends on.

Security verdict: an APPROVED `security-reviewer` handoff whose `metrics.commit_sha`
equals the pushed `develop` tip, i.e. a verdict covering the `origin/develop..develop`
delta. Every refusal names the rule that fired, the permitted value, and the corrective
action, so each one is clearable by an action the product accepts.

The push rules are a quality gate, not a concurrency lock. Commits are never blocked for
missing review evidence; pushes are.

## Context Injection

`dadaia context bind` writes the caller's session record. That record's `bound_at`
timestamp, compared against this session's injection sentinel, is the only trigger for
context-memory injection — so a re-bind reaches a live session. An unbound session gets
generic preflight only. A foreign session's bind cannot alter this session's context or
mode.

## Non-Goals

The hook does not read approval status, task markers, or task write sets. It constrains
**what** may be written, never **how** the change was produced — the ordered SDD
sequence is carried by the specs documents and upheld by the agents. It also does not
parse arbitrary shell strings; git chokepoints provide the independent commit/push
boundary.

## Runtime State

- `.dadaia/states/presence/<context>/<session-id>.json`
- `.dadaia/sessions/<session-id>.json`
- `.dadaia/tmp/ctx-inject-fired-<session-id>`
- `.dadaia/logs/hook-latency.jsonl`
- `.dadaia/logs/reconciler-events.jsonl`

Legacy `.dadaia/states/ctx_locks/` and `.dadaia/sessions/runtime/` are retired residue;
doctor reports and removes them.

## Dependencies

[[context-management]], [[workspace-doctor]], [[architecture]].
