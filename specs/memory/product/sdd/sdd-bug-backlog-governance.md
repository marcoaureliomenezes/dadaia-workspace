---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bugs, duplicate-safe backlog definition, release consumption, audit dispositions, and exact-commit security-gated push.
summary: >-
  Bugs are append-only events; backlog definition binds canonical subjects and prevents
  duplicate/conflicting intake; release definition consumes explicit items; closure and
  audit require terminal dispositions. Intake is additive and never lock-gated.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
token_estimate: 380
last_updated: '2026-07-16'
release_origin: v0.2.3
---

## Bugs

`dadaia bugs append` writes redacted `bug-event-v1` JSONL events under `specs/bugs/`.
`reported` establishes the bug; terminal events such as `resolved` or `rejected` close
it. `bugs status` and `bugs stats` fold the ledger. Agents never hand-author one-file
Markdown bug records and never delete bug history.

Every dadaia-workspace production defect encountered while using the tool is registered
before the turn ends. Expected validation failures and mistakes in throwaway scripts are
not product bugs.

**Bug-hotfix doctrine (constitution §1, always-on rule `bug-hotfix-doctrine`):** a bug
is fixed ON THE SPOT — register → root-cause → RED reproducing test → fix → GREEN →
`resolved` event with evidence → new wheel to the consumer-side validator. Releases are
NEVER created to fix bugs; they exist only for backlog feature work.

## Backlog

Backlog definition starts with operator-demand refinement, binds each subject through
the canonical registry, compares against every existing item, forces update/merge for
overlap, resolves divergent conflicts, authors one item, and rechecks consistency. A new
item is allowed only when every existing item is unrelated.

## Release And Audit

Release definition records exactly which backlog/bug inputs are consumed. Closure gives
each consumed item a terminal disposition and evidence. Audit triage must dispose every
finding as bug, backlog, accepted risk, or resolved; it cannot silently drop findings.

Bug, backlog, and audit paths are additive and writable without a bind or concurrency
lock. Production release artifacts and code follow the ordinary workflow and phase rules.

Push is blocked until an APPROVED security-reviewer handoff names each exact pushed
commit SHA. This is a quality boundary, not a concurrency mechanism.

## Runtime State

- `specs/bugs/*.jsonl`
- `specs/backlog/*.md`
- `specs/releases/<id>/consumed_backlog.json` or its archived equivalent
- `specs/audits/<timestamp>-<session>/`

## Dependencies

[[dadaia-workflows]], [[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
