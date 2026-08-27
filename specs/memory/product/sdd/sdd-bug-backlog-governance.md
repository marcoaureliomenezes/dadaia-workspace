---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: JSONL bugs written through one sanitize-then-mask seam, a three-field evidence gate, an operator-gated backlog, the rc ladder and the git contract.
summary: >-
  Bugs are append-only events written through one seam that sanitizes control and format
  characters (preserving TAB/LF/CR) and then masks every schema free-text field with the
  same operator denylist the push boundary refuses on; the kinds include a non-terminal
  repeatable `picked` reservation
  marker that surfaces contention without ever blocking it; a `resolved` event is refused
  unless it carries three checkable fields — the red-loop command, the test seam and the
  diff direction on the touched feature — and a net-positive diff routes the fix through
  software-architect before the commit. The backlog is the operator's demand queue, curated by
  project-manager in a single BACKLOG.md (ACTIVE + LEDGER) with purge-on-pick and
  continuous sanitizing — no agent materializes an entry, residuals reach the operator
  through a PM intake report, and only actionable defects do — record-only observations
  terminate in the closure record. A release consumes an explicit picked set, matures
  through an rc ladder with no alpha or beta stage, ends in the
  fixed order review → closure → archive → ship, and requires terminal dispositions at
  closure and audit. Work is placed on three branch patterns; every agent stage runs on the
  one live feature branch, and develop and main advance only by pull request. Bug, backlog
  and audit paths stay additive and never lock-gated.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
last_updated: '2026-08-27'
release_origin: v0.4.5
---

## Bugs

`dadaia bugs append` writes redacted `bug-event-v1` JSONL events under `specs/bugs/`.
`reported` establishes the bug; terminal events such as `resolved` or `rejected` close
it. `bugs status` and `bugs stats` fold the ledger. Agents never hand-author one-file
Markdown bug records and never delete bug history.

### The write seam

Every event passes one seam before it reaches the ledger, in a fixed order: **sanitize,
then mask**, both inside the service that already enforces stream coherence, and each
exactly once.

**Sanitation** deletes the characters that break a record or a terminal — the C0/C1/DEL
control range including ESC, plus U+0085 and the Unicode line/paragraph separators
U+2028/U+2029. TAB, LF and CR are **preserved**: they round-trip intact, because JSON
string escaping already makes them harmless inside a value and the reader splits the file
on a literal newline rather than on the wider terminator set a naive `splitlines()`
recognises. Deleting them once cost every multi-line free-text field its word boundaries,
silently, which is why the rule is narrow by design. Characters are deleted rather than
escaped so that a term an author split with one of them re-joins into a contiguous
substring the masking pass can still catch.

**Masking** consumes the operator denylist through the **same loader the push-boundary scan
uses** ([[sdd-gate-v3]]) — one loader, two consumers, no second reader of the file — on top
of the home-path and IPv4 patterns it already applied. A leak is therefore masked at the
moment of writing rather than caught after it is committed. The field set is the schema
mirror the serializer itself uses, so a newly added free-text field is scrubbed the day it
exists; a hand-kept field list is what missed one twice. `core` never imports the loader:
the terms are handed in from the composition root, which keeps the ring boundary intact.

The schema carries **seven** event kinds. Four are terminal — at most one per bug id —
while `archived` is a non-terminal annotation and **`picked` is a non-terminal, repeatable
observable reservation marker**. `picked` records that an actor took the bug: `bugs append
--event picked` writes the reservation with its actor and `bugs status` surfaces
picked-by. It is emphatically **not** a lease — it grants nothing, expires never, blocks
nothing. A **second pick on the same open stream is accepted and made visible, never
refused**: under the no-locks doctrine two visible picks is the sanctioned race outcome,
and hiding one would be the lock the design refuses. The only refusals are
stream-integrity refusals, never concurrency ones — a pick after a terminal event (the
stream is closed) or before any `reported` (the stream was never opened) is incoherent. A
pick mutates no state: it never terminates a bug and a picked-only tail leaves `status`
exactly where it was, and `reported` reopening a stream resets the pick list with it.
Schema, fold and CLI are one authority and evolve in one change, so the enforced gate and
the folded view can never diverge; ledgers written before the kind existed still fold.

Every dadaia-workspace production defect encountered while using the tool is registered
before the turn ends. Expected validation failures and mistakes in throwaway scripts are
not product bugs.

**Bug-fix doctrine:** a bug is fixed ON THE SPOT — register → root-cause → RED
reproducing test → fix → GREEN → `resolved` event with evidence → commit. Releases are
never created to fix bugs; they exist for backlog feature work. The fix runs on the **one
live feature branch**, in whatever phase that branch is in, with no ceremony: no SPEC,
PLAN, TASKS or CLOSURE, and no `specs/releases/<id>/` directory. The record of what shipped
is the bug ledger's `resolved` event plus, at the release that carries it, the
`CHANGELOG.md` entry. Diagnosis itself is a **method, not an exhortation**: the skill that
operates Arm B carries six ordered phases — a feedback loop observed red before any
hypothesis, minimisation until every remaining element is load-bearing, falsifiable
hypotheses each with the observation that would kill it, instrumentation of the executed
path rather than reading code for a theory, a regression test at the correct seam, and
cleanup — each ending in a criterion a reader can check without judgement. When **no
correct seam exists**, the absence *is* the finding: an architecture finding is registered
and `software-architect` is dispatched before the fix proceeds.

### Resolution

`resolved` is a gated event. `dadaia bugs append --event resolved` **refuses** evidence
that lacks any of three independently checkable fields, naming exactly the missing one and
writing nothing:

| Field | What it must carry |
|---|---|
| red-loop command | the command that failed for the real reason, before any fix existed |
| test seam | the regression test, at the boundary the bug actually crossed |
| diff direction | `net-negative` / `net-neutral` / `net-positive` on the touched feature — lines, branches and flags added versus removed |

A fix whose diff is **net-positive on the touched feature** routes to `software-architect`
for a ruling **before the commit**: the growth must be the missing enforcement at the seam
that owns it, never a branch, a flag, a second code path or a cross-feature reach-in. The
refusal is one validation inside the existing append path — no second command, no bypass
flag, no environment escape — and all three fields pass through the same redaction the rest
of the event does. The ledger stays append-only and no past event is rewritten: the reader,
`specs doctor` and `bugs status` keep folding historical events that predate the gate.

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

The branch contract has exactly two homes: one section of the law states it, and the
universal skill `dd-gitflow-default` operates it. This atom restates neither — it records
only where work is placed. Three branch patterns exist and no fourth (`hotfix/*` is
retired, reachable only on an explicit operator request), and exactly one feature branch is
live at a time.

Stage placement is therefore trivial: **every agent stage runs on the one live feature
branch** — backlog definition, research, bug registration, release definition and release
implementation alike, with a commit after every registration. `develop` and `main` are
pull-request targets only; neither is ever a working branch, and a local commit on either
could never be published.

## Merge Cadence

`develop` advances only by pull request from the live feature branch, at two kinds of
moment: once when the definition trio SPEC/PLAN/TASKS is `Aprovado`, and once per **release
candidate** thereafter. `main` advances only by pull request from `develop`, at the final
candidate. Both edges are gated by a CI check requiring an APPROVED security-reviewer
verdict covering the PR head sha, read from committed evidence ([[sdd-gate-v3]]).

There is **no alpha and no beta**. A release matures through `rc-N` only, and `rc-N` is a
state of the specs — it lives in the release's phase and its TASKS, never in a branch name.
`rc-1` burns when the whole implemented scope is validated, gate-green and closed by QA and
is merged into `develop`. Each later `rc` is an adjustment round over that same scope,
discovered by exercising the merged `develop`, worked on the same feature branch and merged
again: one candidate per merge. **No new backlog ever enters a candidate** — a demand
outside the release's declared scope is backlog for a later release. If nothing is found,
the final candidate is `rc-1`. The final candidate carries the memory window, the closure
record and the archive move, then ships `develop` → `main`; at that deploy the shipped
feature branch is deleted and the next one is cut from `main` in the same step.

An internal work boundary inside a release — a segment closed by a committed QA review — is
not a candidate: it never merges, never opens a PR and burns no `rc`.

A release ends in one fixed order: **review → closure → archive → ship**. The pre-PR six-axis
code review of the delta runs on the **thawed** tree, before the `git mv` that freezes the
release directory, so a finding lands on a file its author can still edit; only ship steps
follow the archive. Inside closure the order is memory update → CLOSURE → archive. A group of
completed tasks is one commit; a release defined and reviewed is a mandatory commit and push.

Task reservations stay observable even when the worker cannot commit. A dispatcher relaying
work for a **shell-less sub-agent** commits that sub-agent's `[ ]`→`[-]` flip **before**
relaying the next work item, never batched at the end, so the marker trace records who took
what at the moment they took it.

## Release And Audit

Release definition records exactly which backlog and bug inputs are consumed; at pick
time, open bugs and undispositioned audits outrank fresh backlog. Closure gives each
consumed item a terminal disposition and evidence.

Residual routing is calibrated by signal class, so the operator's demand queue receives
demand and nothing else. Reviews still find and record **everything** — never-silent holds,
and every observation stays in its reviewer's findings array. What differs is where an
observation terminates. A **record-only** observation — INFO-grade, awareness-only, or
already fixed at HEAD — carries no actionable fix surface: it is written into the release
CLOSURE record (its own section) or the reviewer handoff and stops there, never reaching an
intake report. Only an **actionable defect** — LOW or above with a concrete fix surface — is
listed as an intake candidate for the PM to compile and the operator to adjudicate. Zero
observations are lost either way: the two closure sections plus the reviewer handoffs
reconcile against the finding counts.

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

A **merge** is blocked until an APPROVED security-reviewer handoff covers the pull
request's head sha; a push is blocked only by the local preflight, the branch policy and
the content scan. The gating review is diff-based only; a full-tree scan exists solely in
the audit lane. This is a quality boundary, not a concurrency mechanism.

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
- `specs/releases/<id>/verdicts/<sha>.handoff.json` — the committed review evidence the PR
  gate reads
- `pyproject.toml` and `CHANGELOG.md` at the release's final-candidate merge

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
