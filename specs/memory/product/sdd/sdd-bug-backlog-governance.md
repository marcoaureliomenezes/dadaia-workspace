---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: Event-sourced JSONL bugs, an operator-gated single-source backlog, release consumption, audit dispositions, and a develop-only four-branch git contract.
summary: >-
  Bugs are append-only events; the backlog is the operator's demand queue, curated by
  project-manager in a single BACKLOG.md (ACTIVE + LEDGER) with purge-on-pick and
  continuous sanitizing — no agent materializes an entry, residuals reach the operator
  through a PM intake report. A release consumes an explicit picked set; closure and audit
  require terminal dispositions. Work is placed on four branch patterns with develop the
  only pushable one; a feature branch merges into develop at two milestones, each followed
  by a diff-based security review of the develop delta and a push. Bug, backlog and audit
  paths stay additive and never lock-gated.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
token_estimate: 1300
last_updated: '2026-08-15'
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

The backlog is the operator's demand queue: only the operator creates demand.
`project-manager` curates it as a single source, `specs/backlog/BACKLOG.md` — an `ACTIVE`
section holding one full-prose subsection per live candidate and a `LEDGER` section
holding one line per closed item (slug · disposition · release-or-reason · date). Every
other agent reads it freely and none writes to it.

Intake is operator-gated. No agent materializes an entry: a residual found at a closure,
review or audit is only listed as an intake candidate, and `project-manager` compiles
those residuals into an intake report — the ordinary handoff-first shape with a human
target — that the operator approves, rejects or discards before anything reaches
`ACTIVE`. The one carve-out is a deferral the operator ratified during a release: it is
already-approved intake and is not re-adjudicated.

Curation is continuous, not a release-boundary event. Every touch runs a staleness scan
and a dedup scan of the whole file, so a near-duplicate subject is merged into the
existing item instead of filed twice; confirmed-stale or invalid items are dispositioned
`DEFERRED` or `REJECTED` with a one-line reason. Nothing is deleted: an item leaves
`ACTIVE` only by gaining a LEDGER line, and a picked item leaves `ACTIVE` in the same
commit that creates the release SPEC, which records its provenance (purge-on-pick). The
entry schema, the intake protocol and the terminal disposition vocabulary have exactly one
home — the `dd-backlog-definition` skill — which closure and audit reference rather than
restate.

The single source is physical. `specs/backlog/` holds exactly `BACKLOG.md`, `README.md`
and `_archive/` — plus `remote-bugs/` where an intake subtree exists. There are no
per-entry entry files anywhere in the live tree, and `specs/backlog/_archive/` is the
historical store for every superseded entry file and for the retired `candidates.md`
index.

`features/backlog/document.py` parses that document into a typed ACTIVE/LEDGER model,
with its roots injected and no I/O outside the supplied path. An `### <slug>` ACTIVE
subsection carries five required keys — `Title`, `Opened` (`YYYY-MM-DD`), `Status`,
`Description`, `Provenance` — plus the optional `Intents`, holding the typed `intents[]`
YAML in a fenced span. A LEDGER line is the four-field grammar
`<slug> · <disposition> · <release-or-reason> · <date>`. Parsing is diagnostic and never
throws: a malformed subsection, an unparseable intents block and an ungrammatical LEDGER
line are each captured as a located error naming section, slug and line, so the doctor
reports instead of crashing; an absent document is an empty model, not a failure, so a
context with no backlog is legitimate.

`dadaia backlog doctor` validates that model with its four codes unchanged in identity
and severity. **BL-SCHEMA** — a located parse error, an invalid status token, a slug
outside `^[a-z][a-z0-9-]+$`, or an item at `candidate` or beyond with no bound or an
unresolvable `intents[]` subject (`idea` stays exempt). **BL-DUP** — a slug repeated
inside `ACTIVE` or inside `LEDGER`, or two ACTIVE items sharing anchor-set and change.
**BL-CONFLICT** — two ACTIVE items sharing an anchor with an incompatible change.
**BL-STALE** — an ACTIVE item that is already consumed or dispositioned: its slug is
recorded in an archived `consumed_backlog.json`, or it also carries a LEDGER line, or its
own status is one of the six terminal tokens. `dadaia backlog new <slug>` appends one
conformant subsection at `status: idea` to `## ACTIVE`, creates the document with both
section headings when it is absent, and refuses a slug already present in either section.
The pre-commit staged-scope gate and the CI job run that same doctor over that same
model. `specs doctor` backstops the surface from the other side: SPEC-DOC-031 iterates
the ACTIVE subsections, and SPEC-DOC-035 is the single-source invariant — any item `*.md`
loose directly under `specs/backlog/`, other than `BACKLOG.md` and `README.md` and
excluding `_archive/` and `remote-bugs/`, is drift. Both are WARNING.

The backlog has no removal or consumption write side. `**Consumes:**` in a release SPEC
is provenance, not a call site: consumption is executed by the PM's purge-on-pick at
definition and by the closure disposition sweep, which gives each consumed slug its
LEDGER line and drops its ACTIVE subsection in the same commit.
`features/backlog/ledger.py`'s `read_consumed` survives only as a pure reader over the
archived sidecars and as one of BL-STALE's three inputs.

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
- `specs/backlog/BACKLOG.md` — the single source: `## ACTIVE` subsections and `## LEDGER`
  lines, read and written by every backlog verb, gate and check
- `specs/backlog/_archive/` — the historical store: superseded entry files and the retired
  `candidates.md` index, moved in by `git mv` and never deleted
- `.dadaia/reports/<context>/project-manager/<UTC>-intake.html` — the operator-facing
  intake report and its handoff
- `specs/releases/<id>/consumed_backlog.json` or its archived equivalent
- `specs/audits/<timestamp>-<session>/` and, once dispositioned,
  `specs/audits/_archive/<audit>--dispositioned-<release-id>`
- `pyproject.toml` and `CHANGELOG.md` at a hotfix merge into `develop`

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
