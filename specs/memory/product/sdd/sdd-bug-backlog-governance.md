---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: One record per bug through one write seam, a live-photo backlog with histo exits, the RELEASE.jsonl milestone fold, and five isolated commit shapes.
summary: The bug ledger, the backlog live photo, the release-event stream and the branch/merge cadence — one record per bug, one write seam, one exit record per backlog slug, and a folded `RELEASE.jsonl` per release.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
---

## Bugs

`specs/bugs/BUGS.jsonl` is the single canonical bug ledger: **one record per bug, appended
once**, keyed by `id`. There is no event stream, no state machine and no fold — a bug's
present state is the one line that carries it, and git history is that line's change log.

`bug-record-v1.schema.json` (`additionalProperties: false`) declares three field
categories, per property:

| Category | Fields | Rule |
|---|---|---|
| Immutable core | `id`, `ts`, `reported_by`, `title`, `severity`, `surface`, `component`, `context`, `symptom`, `repro`, `expected` | set at registration, never changed |
| Write-once | `root_cause`, `solution`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction`, `superseded_by`, `migration_note` | absent until first set, immutable afterwards |
| Mutable governance | `status`, `cause`, `caused_by`, `lineage_source`, `registration_commit`, `registration_granularity`, `resolved_commit`, `resolution_granularity`, `resolved_release`, `audited` | rewritten in place |

`status` is `open | resolved | superseded | deferred | rejected`. A pick is not a status. A
sweep closure is `superseded` with `superseded_by` naming what met the need — `resolved`
requires a regression seam. A reopen is a new record with a new `id` declaring
`caused_by: <prior-id>`.

`surface` is a closed enum with one source: the `dadaia_workspace/features/*/` package
inventory on disk (24 packages) plus `core`, `infrastructure`, `cli`, `hooks`, `tests`,
`public-assets` and `unknown`; a contract test asserts its feature arm equals the
import-linter independence contract's `modules =` list. `component` keeps free-text
`path#symbol` precision. The evidence fields are `evidence_loop` (the red-loop command
run), `evidence_seam` (the regression test's boundary) and `evidence_diff`, closed by
`diff_direction` onto `net-negative | net-neutral | net-positive`.

### The write seam

`features/bugs`'s record store is the only code path that writes a governance field. It
sits on the generic `infrastructure/jsonl_record_store.py`, a `JsonlRecordStore` keyed by
`id` whose parse/serialise pair is injected through a `core.protocols` record protocol;
each feature owns its model (`core/models/{bugs,findings,backlog}.py`) and gets its own
store instance from the container, so no module knows more than one record shape.

Every write passes the seam in a fixed order — **sanitize, then mask** — each once.

- **Sanitation** deletes the C0/C1/DEL control range including ESC, plus U+0085 and
  U+2028/U+2029. TAB, LF and CR are preserved. Characters are deleted rather than escaped,
  so a term split by one of them re-joins into a substring the masking pass catches.
- **Masking** consumes the operator denylist through the same loader the push-boundary
  scan uses ([[sdd-gate-v3]]), on top of the home-path and IPv4 patterns. The field set is
  read from the schema at load time, never a module-level tuple, and the terms arrive from
  the composition root so `core` never imports the loader. The backlog histo writer uses
  the same redaction.
- **The rewrite is a compare-then-swap** through `core/atomic_write.py` carrying
  `expected_previous`; a mismatch raises `ConcurrentModificationError`, which the store
  re-raises as its own stale-write error. Semantics are refuse-stale, then retry.

### CLI surface

Five verbs over the one seam: `dadaia bugs append`, `status`, `stats`, `update` (the
governance door — `--set key=value`, refusing an immutable core field and a second write
to a write-once field) and `archive`. There is no `--event` flag and no `resolve` verb.

`bugs archive` is idempotent: terminal records older than 90 days move to
`specs/bugs/_archive/bugs_histo.jsonl`, one per line, and a second run is a no-op;
`specs doctor` emits SPEC-DOC-041 as an overdue WARN. The legacy
`specs/bugs/_archive/archive.jsonl` stays byte-frozen. Coherence gaps — resolved without
`cause`/`caused_by`/`resolved_release`, superseded without `superseded_by`, a surviving v5
`"event"`-keyed line — are surfaced by `bugs status` and `specs doctor` (SPEC-DOC-033)
with the exit code unchanged. The record contract is audited, never gated.

### Resolution

A bug is fixed on the spot — register → root-cause → RED reproducing test → fix → GREEN →
`status: resolved` with evidence → commit — on the one live feature branch, in whatever
phase it is in, with no SPEC, PLAN, TASKS or release directory. Releases are never created
to fix bugs.

Diagnosis is a method of seven ordered phases. **Phase 0 is the lineage duty**: before any
hypothesis, filter the ledger for records sharing this bug's `surface` or `component`
inside the audit window (newest `audited` milestone to HEAD; the whole file when none),
capped at the 20 most recent matching records by resolution date, diffing only those with
`resolution_granularity == "exact"`. It ends by declaring `caused_by: <bug-id>` or
`caused_by: none` with evidence, in the record and in the fix commit body. Phases 1-6 are
a reproduction loop observed red before any hypothesis, minimisation, falsifiable
hypotheses one at a time, instrumentation of the executed path, a regression test at the
boundary the bug actually crossed, and removal of the instrumentation.

When no correct seam exists the absence is the finding: an architecture finding is
registered and `software-architect` dispatched before the fix proceeds. A `caused_by`
pointing at a prior fix requires the structural cause and a diff that does not grow the
feature; a net-positive diff routes to `software-architect` before the commit.

### Provenance

`registration_commit` and `resolved_commit` are a cache over git, never a second truth.
`core/bug_provenance.py` derives them — pure and stdlib-only over an iterator of
`(sha, parents, date, touched_paths, added_lines)`, with git access from a
`core.protocols` history reader implemented in `infrastructure/git_subprocess.py`.

The walk is all refs, chronological, first-add wins:
`git log --all --full-history --no-merges --reverse --date-order -- specs/bugs/`. For each
`bug_id` the first commit adding a registration line supplies `registration_commit` and
the first adding a terminal line supplies `resolved_commit`; only additions count, and
`--full-history` is load-bearing against history simplification on merged side branches.

| Granularity | Meaning |
|---|---|
| `exact` | adds exactly one bug's line **and** touches a file outside `specs/` |
| `release-squash` | adds more than one bug's line |
| `ledger-only` | one bug's line, no file outside `specs/` |

`resolved_commit` stays `null` at resolve time — a commit cannot contain its own sha. The
only writer of the cache is the audit's first pillar ([[audits-canon]]), which writes
`audited` and all four provenance fields in one atomic in-place rewrite through this seam.
`cause` and `caused_by` are never fabricated: a value populated from prose carries
`lineage_source: "text-reference"`. The v5→v6 line classifier is permanent in
`core/bug_provenance.py`; the v5 fold adapter lives in `features/bugs/migrate_v5.py`,
imported by nothing permanent.

### Commit shapes

Five isolated write shapes, measured by the audit from `git log`, never by a hook; the
operative home is `dd-gitflow-default` §3a and the product truth is that each stages
nothing else.

| Shape | Staged alone | Message |
|---|---|---|
| Bug registration | `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| Backlog entry / ADR proposal | `specs/backlog/BACKLOG.md`, or the new `specs/ADRs/NNNN-<slug>.md` | `chore(backlog): add <slug>` / `docs(adr): propose NNNN-<slug>` |
| Bug fix — one commit, no second | code + regression test + the `BUGS.jsonl` line | `fix(<scope>): <what> (resolves <id>)` |
| Release definition | SPEC + PLAN + TASKS + purge-on-pick + the picked bugs' records; an `_ideas/` variant carries the SPEC only | one bundled commit |
| ADR acceptance | the ADR's status flip + the Part-1 principle hunk it admits | `docs(adr): accept NNNN-<slug>` |

A resolve is not followed by a push; the preflight runs before a push because it is an
always-on rule.

## Backlog

The backlog is the operator's demand queue: only the operator creates demand.
`project-manager` curates one source, `specs/backlog/BACKLOG.md`, a live photo carrying
`## ACTIVE` only; every other agent reads it and none writes it.

Leaving `ACTIVE` appends one record
`{ts, slug, disposition, reason, release, by, entry_md}` to
`specs/backlog/_archive/backlog_histo.jsonl`, through the same write-time redaction the
bug ledger uses. Consumption is executed at two moments against **one** record:
purge-on-pick removes the `## ACTIVE` subsection in the same commit that creates the
release SPEC and appends the (often provisional) exit record; the closure disposition
sweep rewrites that record's `disposition`/`reason`/`release` in place to its terminal
token. Never a second line. `**Consumes:**` in a SPEC is provenance, not a call site.

Intake is operator-gated: no agent materializes an entry. A residual found at a closure,
review or audit is listed as an intake candidate, and `project-manager` compiles those
into an operator-facing intake report decided before anything reaches `ACTIVE`; the one
carve-out is a deferral the operator ratified during a release. Only an actionable defect
reaches an intake report — a record-only observation terminates in the closure notes.
Curation is continuous: every touch runs a staleness scan and a dedup scan of the whole
file, and an item leaves `ACTIVE` only by gaining its histo record. The entry schema,
intake protocol and disposition vocabulary have one home, `dd-backlog-definition`.

The single source is physical: `specs/backlog/` holds exactly `BACKLOG.md`, `AGENTS.md`
and `_archive/`, the last holding superseded entry files, `backlog_histo.jsonl` and
`consumed_backlog_histo.jsonl`.

`features/backlog/document.py` parses the document into a typed model with its roots
injected and no I/O outside the supplied path. An `### <slug>` ACTIVE subsection carries
five required keys — `Title`, `Opened` (`YYYY-MM-DD`), `Status`, `Description`,
`Provenance` — plus optional `Intents` holding typed `intents[]` YAML in a fenced span.
Parsing is diagnostic and never throws: a malformed subsection or unparseable intents
block becomes a located error naming section, slug and line, and an absent document is an
empty model.

`dadaia backlog doctor` validates that model with three codes: **BL-SCHEMA** (a located
parse error, an invalid status token, a slug outside `^[a-z][a-z0-9-]+$`, or an item at
`candidate` or beyond with no bound or unresolvable `intents[]` subject — `idea` exempt);
**BL-CONFLICT** (two ACTIVE items sharing an anchor with an incompatible change); and
**BL-STALE** (an ACTIVE item already consumed or dispositioned). `dadaia backlog new
<slug>` appends one conformant subsection at `status: idea`, creates the document when
absent, and refuses a slug already present. `specs doctor` backstops with SPEC-DOC-031 and
SPEC-DOC-035, both WARNING.

## Branches and stage placement

The branch contract has two homes: one law section states it and `dd-gitflow-default`
operates it. Three branch patterns exist and no fourth, and exactly one feature branch is
live at a time. **Every agent stage runs on that one live feature branch** — backlog
definition, research, bug registration, release definition and implementation alike, with
a commit after every registration. `develop` and `main` are pull-request targets only.

## Merge cadence

Each release directory carries `RELEASE.jsonl`, an append-only stream of
`release-event-v1` records with the envelope `{ts, event, agent, data}` and no
`session_id`. Exactly seven kinds exist: `phase`, `defined`, `implemented`, `shipped`,
`audited`, `rc`, `note`. Records are appended by agents with file tools — no code writes
the stream, which is sound because the file is append-only.

The fold has one home and one reader: `core/release_events.py` parses and folds with no
write call and no file I/O, and `features/specs/doctor_release.py` owns the single disk
read. The **last `phase` record wins**, resolving the active release and phase for the SDD
gate, the doctor and every navigating agent. The three sha-bearing milestones are
immutable facts and the fold takes the **first** record of each, reporting a later
duplicate as SPEC-DOC-043 (WARNING): `defined` carries `{sha, pr}` at the definition
promotion commit, `implemented` carries `{sha, rc}` written at the final-`rc` QA close on
that closed commit's sha, `shipped` carries `{sha, pr, tag}` at the ship merge, and
`audited` carries `{sha, audit}`.

**The closure narrative lives in `note` records**, keyed by `data.kind`:
`closure-summary`, `closure-size-accounting`, `closure-drift` (one per drift),
`closure-test-dispositions`, `closure-artifact-gc`. Everything else has a native home —
dispositions in `backlog_histo.jsonl`'s `release` field and `BUGS.jsonl`'s
`resolved_release`, tasks in `TASKS.md`'s `[x]` markers and their commits, validations in
the per-task handoffs and the trio's verdicts, memory updates in the atom diffs, and the
archive decision in the `git mv` plus the `phase: ARCHIVED` record.

Release ids are bare semver; a `v` prefix resolves only for read-only lookups of an
already-archived directory. `specs/releases/_ideas/<id>/` holds a SPEC only — no
`RELEASE.jsonl`, never an audit-window source, refused as an evidence root by the CI
verdict gate.

`develop` advances only by pull request from the live feature branch, at two kinds of
moment: once when the definition trio is `Aprovado`, and once per release candidate
thereafter. `main` advances only by pull request from `develop`, at the final candidate.
Both edges are gated by the committed security verdict ([[sdd-gate-v3]]).

There is no alpha and no beta. A release matures through `rc-N` only, and `rc-N` is a
state of the specs — it lives in the `phase` record's `data.segment` and in TASKS, never
in a branch name. `rc-1` burns when the whole implemented scope is validated, gate-green
and closed by QA; each later `rc` is an adjustment round over that same scope, one
candidate per merge, and no new backlog ever enters a candidate. An internal segment
closed by a committed QA review is not a candidate and burns no `rc`.

A release ends in one fixed order: **review → closure → archive → ship**. The pre-PR
six-axis code review runs on the thawed tree, before the `git mv` that freezes the release
directory; inside closure the order is memory update → the closure `note` records →
disposition sweep → artifact GC → archive. A group of completed tasks is one commit. A
dispatcher relaying work for a shell-less sub-agent commits that sub-agent's `[ ]`→`[-]`
flip before relaying the next work item.

## Release and audit

Release definition records exactly which backlog and bug inputs are consumed; at pick time
open bugs and undispositioned audits outrank fresh backlog, and closure gives each
consumed item a terminal disposition and evidence. Audits are committed spec artifacts
under `specs/audits/`, run as three pillars over a sha window and dispositioned by exactly
one remediation release ([[audits-canon]]).

A **merge** is blocked until an APPROVED security-reviewer handoff covers the PR head sha;
a **push** is blocked only by branch policy, the content scan and an unresolvable runner.

## Runtime state

- `specs/bugs/BUGS.jsonl`; `specs/bugs/_archive/{bugs_histo.jsonl,archive.jsonl}`
- `specs/backlog/BACKLOG.md`;
  `specs/backlog/_archive/{backlog_histo,consumed_backlog_histo}.jsonl`
- `specs/releases/<id>/RELEASE.jsonl`; `specs/releases/_archive/releases_histo.jsonl`;
  `specs/releases/_ideas/<id>/SPEC.md`
- `specs/releases/<id>/verdicts/<sha>.handoff.json`; `specs/releases/<id>/reviews/`
- `specs/audits/<YYYYMMDD>-<slug>/` and `specs/audits/_archive/<audit>/`
- `.dadaia/reports/<context>/project-manager/<UTC>-intake/`
- `pyproject.toml` and `CHANGELOG.md` at the final-candidate merge

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[audits-canon]], [[agent-comms]].
