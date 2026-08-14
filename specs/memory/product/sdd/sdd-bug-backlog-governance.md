---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bugs, PM-curated backlog, release consumption, audit dispositions, and a four-branch git contract whose only pushable branch is develop.
summary: >-
  Bugs are append-only events; the backlog is curated by project-manager and sanitized
  continuously; a release consumes an explicit picked set; closure and audit require
  terminal dispositions. Work is placed on four branch patterns with develop the only
  pushable one; a feature branch merges into develop at two milestones, each followed by a
  diff-based security review of the develop delta and a push. Intake is additive and never
  lock-gated.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
token_estimate: 620
last_updated: '2026-08-14'
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
never created to fix bugs; they exist for backlog feature work. The fix runs on
`hotfix/{M.m.p}` at the next PATCH, merged into `develop`; that merge commit also bumps
`pyproject.toml` `version` to the minted PATCH and adds the `CHANGELOG.md` entry. A hotfix
carries no ceremony: no SPEC, PLAN, TASKS or CLOSURE, and no `specs/releases/<id>/`
directory. The record of what shipped is the bug ledger's `resolved` event plus that
CHANGELOG entry.

## Backlog

`project-manager` curates `specs/backlog/**`; every other agent reads it and routes
additions through the PM. Each candidate is compared against the existing set before it
is authored: overlap forces an update or merge, divergent conflicts are resolved, and a
new item is allowed only when every existing item is unrelated. Entries are sanitized
continuously — stale or invalid ones are marked `deferred` or `rejected` with a reason.
Backlog entries and bugs are kept forever: mark them, never delete them.

## Branches And Stage Placement

Four branch patterns exist and no fifth: `main`, `develop`, `feature/{M.m.p}`, and
`hotfix/{M.m.p}` with PATCH ≥ 1. `develop` is the only pushable branch; `feature/*` and
`hotfix/*` live local-only; `main` takes no direct commit and no direct push and advances
only through a pull request from `develop`. The operational contract — the per-stage table
and the mechanical-versus-discipline split — lives in the universal skill `dadaia-gitflow`;
the law states it once in `DADAIA.md` §5/§6 and every other surface references it.

Stage placement follows the branch a stage belongs to. Backlog definition, research, and
bug registration happen on `develop`, with a commit after every registration. Release
definition and release implementation both happen on `feature/{M.m.p}` cut from `develop`.
Bug fixes happen on `hotfix/{M.m.p}`.

## Merge Cadence

A feature branch merges into local `develop` at exactly two milestones: (a) when the
definition trio SPEC/PLAN/TASKS is `Aprovado`, and (b) at ship. Each merge is followed, in
that order, by a diff-based security review of `origin/develop..develop` and a push of
`develop`. Ship continues from there: PR `develop` → `main`, every CI job green, merge.

Release finalization order is memory update → CLOSURE → archive. A group of completed tasks
is one commit; a release defined and reviewed is a mandatory commit and push.

## Release And Audit

Release definition records exactly which backlog and bug inputs are consumed; at pick
time, open bugs and undispositioned audits outrank fresh backlog. Closure gives each
consumed item a terminal disposition and evidence.

One audit generates exactly one remediation release, and that release gives every finding
an explicit disposition — fixed, superseded by a broader picked item, or deferred/rejected
with a reason routed to the backlog. Audit triage cannot silently drop a finding, and an
audit archives only once a named approved release has dispositioned it fully. The archived
audit carries a disposing-release pointer naming that release; `specs doctor` warns on an
archived audit that names none (SPEC-DOC-036) and on an audit directory still loose in
`specs/audits/` (SPEC-DOC-038). The original audit record is immutable — a disposition is
appended, never woven into the findings text.

Bug, backlog, and audit paths are additive and writable without a bind or concurrency
lock. Production release artifacts and code follow the ordinary path and phase rules.

Push is blocked until an APPROVED security-reviewer handoff covers the
`origin/develop..develop` delta being pushed, keyed to the pushed `develop` tip. The
push-gate review is that diff only; a full-tree scan exists solely in the audit lane. This
is a quality boundary, not a concurrency mechanism.

## Runtime State

- `specs/bugs/*.jsonl`
- `specs/backlog/*.md`
- `specs/releases/<id>/consumed_backlog.json` or its archived equivalent
- `specs/audits/<timestamp>-<session>/` and, once dispositioned,
  `specs/audits/_archive/<audit>--dispositioned-<release-id>`
- `pyproject.toml` and `CHANGELOG.md` at a hotfix merge into `develop`

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
