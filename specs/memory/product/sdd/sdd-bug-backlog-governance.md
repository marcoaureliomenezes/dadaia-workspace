---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bugs, PM-curated backlog, release consumption, audit dispositions, and exact-commit security-gated push.
summary: >-
  Bugs are append-only events; the backlog is curated by project-manager and sanitized
  continuously; a release consumes an explicit picked set; closure and audit require
  terminal dispositions. Intake is additive and never lock-gated.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
token_estimate: 370
last_updated: '2026-08-07'
release_origin: v0.3.0
---

## Bugs

`dadaia bugs append` writes redacted `bug-event-v1` JSONL events under `specs/bugs/`.
`reported` establishes the bug; terminal events such as `resolved` or `rejected` close
it. `bugs status` and `bugs stats` fold the ledger. Agents never hand-author one-file
Markdown bug records and never delete bug history.

Every dadaia-workspace production defect encountered while using the tool is registered
before the turn ends. Expected validation failures and mistakes in throwaway scripts are
not product bugs.

**Bug-hotfix doctrine:** a bug is fixed ON THE SPOT — register → root-cause → RED
reproducing test → fix → GREEN → `resolved` event with evidence → commit. Releases are
never created to fix bugs; they exist for backlog feature work.

## Backlog

`project-manager` curates `specs/backlog/**`; every other agent reads it and routes
additions through the PM. Each candidate is compared against the existing set before it
is authored: overlap forces an update or merge, divergent conflicts are resolved, and a
new item is allowed only when every existing item is unrelated. Entries are sanitized
continuously — stale or invalid ones are marked `deferred` or `rejected` with a reason.
Backlog entries and bugs are kept forever: mark them, never delete them.

## Release And Audit

Release definition records exactly which backlog and bug inputs are consumed; at pick
time, open bugs and undispositioned audits outrank fresh backlog. Closure gives each
consumed item a terminal disposition and evidence. Audit triage must dispose every
finding as fixed, superseded, deferred, or rejected; it cannot silently drop findings,
and an audit archives only once a named approved release has dispositioned it fully.

Bug, backlog, and audit paths are additive and writable without a bind or concurrency
lock. Production release artifacts and code follow the ordinary path and phase rules.

Push is blocked until an APPROVED security-reviewer handoff names each exact pushed
commit SHA. This is a quality boundary, not a concurrency mechanism.

## Runtime State

- `specs/bugs/*.jsonl`
- `specs/backlog/*.md`
- `specs/releases/<id>/consumed_backlog.json` or its archived equivalent
- `specs/audits/<timestamp>-<session>/`

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
