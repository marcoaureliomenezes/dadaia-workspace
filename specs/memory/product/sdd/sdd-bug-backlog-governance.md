---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: One record per bug through one write seam, a live-photo backlog with histo exits, the RELEASE.jsonl milestone fold, and five isolated commit shapes.
summary: >-
  `specs/bugs/BUGS.jsonl` carries one record per bug — never an event stream — with three
  declared field categories (immutable core, write-once, mutable governance) and a closed
  `surface` enum derived from the feature-package inventory. Exactly one write seam reaches
  it, the generic id-keyed record store, which sanitizes then masks through a schema-derived
  field set and rewrites in place through the atomic-write primitive's compare-then-swap, so
  a rewrite is refused rather than applied to a tree the writer never saw. Five CLI verbs
  expose it — `append`, `status`, `stats`, `update`, `archive` — and coherence is surfaced as
  a warning, never a block. Provenance shas are a derived cache over an all-refs
  `--full-history` walk whose sole writer is the audit's first pillar. The backlog is a live
  photo of `## ACTIVE` alone, every exit appending one rewritable record to
  `backlog_histo.jsonl`. A release's phase and its milestone facts are the fold of an
  append-only `RELEASE.jsonl`, which also carries the closure narrative; release ids are bare
  semver and `_ideas/` holds a SPEC only. Work runs on one live feature branch through an rc
  ladder that ends review, closure, archive, ship.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
last_updated: '2026-08-27'
release_origin: 0.5.0
---

## Bugs

`specs/bugs/BUGS.jsonl` is the single canonical bug ledger: **one record per bug, appended
once**, keyed by `id`. There is no event stream, no state machine and no fold — a bug's
present state is the one line that carries it, and git history is that line's change log.
`bugs status` and `bugs stats` render the ledger; agents never hand-author a Markdown bug
file and never delete bug history.

`bug-record-v1.schema.json` (`additionalProperties: false`) declares **three field
categories, per property**:

| Category | Fields | Rule |
|---|---|---|
| Immutable core | `id`, `ts`, `reported_by`, `title`, `severity`, `surface`, `component`, `context`, `symptom`, `repro`, `expected` | set at registration, never changed |
| Write-once | `root_cause`, `solution`, `evidence_loop`, `evidence_seam`, `evidence_diff`, `diff_direction`, `superseded_by`, `migration_note` | legitimately absent until first set, immutable afterwards |
| Mutable governance | `status`, `cause`, `caused_by`, `lineage_source`, `registration_commit`, `registration_granularity`, `resolved_commit`, `resolution_granularity`, `resolved_release`, `audited` | rewritten in place, in the record's own line |

`status` is `open | resolved | superseded | deferred | rejected`. A **pick is not a status**:
the definition commit already records it. A **sweep closure is `superseded`**, never
`resolved` — `resolved` requires a regression seam — with `superseded_by` naming what met the
need. A **reopen is a new record** with a new `id` declaring `caused_by: <prior-id>`.

`surface` is a **closed enum with one source**: the `dadaia_workspace/features/*/` package
inventory on disk (24 packages), plus the non-feature layers `core`, `infrastructure`, `cli`,
`hooks`, `tests`, `public-assets`, plus `unknown`. A contract test asserts the enum's feature
arm equals the import-linter independence contract's `modules =` list, which itself equals the
packages on disk — a package added tomorrow goes RED in one place. `component` keeps the
free-text `path#symbol` precision, so recurrence is grouped on the enum rather than guessed
from 86 distinct hand-typed strings.

The three evidence fields are the ledger's only structured evidence: `evidence_loop` (the
red-loop command actually run), `evidence_seam` (the regression test's boundary) and
`evidence_diff` (what the diff did), with `diff_direction` closing them onto
`net-negative | net-neutral | net-positive`.

### The write seam

**One seam, every writer.** `features/bugs`'s record store is the only code path that writes
a governance field — registration, resolution, and the audit's `audited`/provenance rewrite
alike. It sits on the generic `infrastructure/jsonl_record_store.py`, a `JsonlRecordStore`
keyed by `id` whose parse/serialise pair is injected through a `core.protocols` record
protocol; each feature owns its own model (`core/models/{bugs,findings,backlog}.py`) and
receives its own store instance from the container, so **no module knows more than one record
shape**.

Every write passes the seam in a fixed order — **sanitize, then mask** — each exactly once.

**Sanitation** deletes the characters that break a record or a terminal: the C0/C1/DEL control
range including ESC, plus U+0085 and the Unicode line/paragraph separators U+2028/U+2029. TAB,
LF and CR are **preserved** — JSON string escaping already makes them harmless inside a value
and the reader splits on a literal newline rather than the wider terminator set a naive
`splitlines()` recognises. Deleting them once cost every multi-line field its word boundaries,
silently, which is why the rule is narrow by design. Characters are deleted rather than
escaped so a term an author split with one of them re-joins into a contiguous substring the
masking pass can still catch.

**Masking** consumes the operator denylist through the **same loader the push-boundary scan
uses** ([[sdd-gate-v3]]) — one loader, two consumers — on top of the home-path and IPv4
patterns. The field set is **read from the schema at load time**: there is no module-level
field tuple anywhere in `core/models/{bugs,findings,release_events}.py`, because a mirror is a
hand-kept list wearing a derivation's name and it twice missed a newly added free-text field.
`core` never imports the loader; the terms arrive from the composition root, keeping the ring
boundary intact. The same redaction covers the backlog histo writer.

**The rewrite is a compare-then-swap.** A governance update is read-modify-write, so it goes
through `core/atomic_write.py` carrying `expected_previous`. The re-read is the **last** thing
the primitive does before `os.replace` — after the temp sibling is already serialized — so
nothing but the comparison itself sits in the gap; a caller doing its own re-read around a
separate call could never close it, because its check necessarily precedes the serialization a
concurrent writer can land inside. When the live file no longer matches, the primitive raises
`ConcurrentModificationError` and the store re-raises its own stale-write error rather than
replacing. **One race semantics: refuse-stale, then the caller retries.** Nothing blocks,
nothing is lost, and a rewrite is never applied to a tree the writer did not see.

### CLI surface

Five verbs, all over the one seam: `dadaia bugs append` (registration), `status`, `stats`,
`update` (the governance-write door — `--set key=value`, refusing an immutable core field and
a second write to a write-once field), and `archive`. There is **no `--event` flag** and no
`resolve` verb.

`dadaia bugs archive` is idempotent: terminal records older than 90 days move to
`specs/bugs/_archive/bugs_histo.jsonl`, one record per line; a second run is a no-op and newer
records are untouched. `specs doctor` emits SPEC-DOC-041, an **overdue WARN**, when terminal
records past the threshold are still live. The legacy `specs/bugs/_archive/archive.jsonl`
(114 `{file, content}` records) stays byte-frozen and is never converted.

Coherence — resolved without `cause`/`caused_by`/`resolved_release`, superseded without
`superseded_by`, a surviving v5 `"event"`-keyed line — is surfaced by `bugs status` and by
`specs doctor` (SPEC-DOC-033) with the **exit code unchanged**. Nothing about the record
contract blocks a write: it is audited, not gated.

Every dadaia-workspace production defect encountered while using the tool is registered before
the turn ends. Expected validation failures and mistakes in throwaway scripts are not product
bugs.

### Resolution

A bug is fixed **on the spot** — register → root-cause → RED reproducing test → fix → GREEN →
`status: resolved` with evidence → commit. Releases are never created to fix bugs. The fix
runs on the **one live feature branch**, in whatever phase that branch is in, with no
ceremony: no SPEC, PLAN, TASKS or release directory.

Diagnosis is a **method, not an exhortation**. The skill that operates it carries seven
ordered phases, each ending on a criterion a reader can check without judgement:

- **Phase 0 — lineage duty.** Before any hypothesis, filter the ledger for records sharing
  this bug's `surface` enum value or its `component`, inside the audit window (from the newest
  `audited` milestone to HEAD; the whole file when none). The read is **capped at the 20 most
  recent matching records** ordered by resolution date, and **only those with
  `resolution_granularity == "exact"` are diffed** — a `release-squash` or `ledger-only` sha is
  named as coarse rather than diffed as if it were the fix. The phase ends by declaring
  `caused_by: <bug-id>` or `caused_by: none` **with its evidence**, in the record and echoed in
  the fix commit body. At three bugs a day an uncapped filter is 100–300 records per fix, which
  is how a procedure becomes a ritual nobody performs.
- **Phases 1–6** — a reproduction loop observed red before any hypothesis; minimisation until
  every remaining element is load-bearing; falsifiable hypotheses one at a time, each carrying
  the observation that would kill it; instrumentation of the executed path rather than reading
  code for a theory; a regression test at the **correct seam** — the boundary the bug actually
  crossed; and removal of the instrumentation.

**The no-correct-seam clause:** when no correct seam exists, the absence *is* the finding — an
architecture finding is registered and `software-architect` is dispatched before the fix
proceeds. **The `caused_by` clause:** a `caused_by` pointing at a prior fix triggers the
standing architecture-review order — the fixer shows the structural cause and a diff that does
not grow the feature, and a **net-positive** diff routes to `software-architect` before the
commit.

### Provenance

`registration_commit` and `resolved_commit` are a **cache over git, never a second truth**.
The derivation lives in `core/bug_provenance.py` — pure, stdlib-only, over an iterator of
`(sha, parents, date, touched_paths, added_lines)`, with git access supplied by a
`core.protocols` history reader implemented in `infrastructure/git_subprocess.py` and injected
by the container.

The walk is **all refs, chronological, first-add wins**: candidate commits come from
`git log --all --full-history --no-merges --reverse --date-order -- specs/bugs/`, and for each
`bug_id` the first commit adding a registration line supplies `registration_commit` while the
first adding a terminal line supplies `resolved_commit`. Only *additions* count, so a later
squash or ship commit that re-adds the same line never wins. **`--full-history` is
load-bearing**: without it git's history simplification prunes ledger-touching commits on
merged side branches and the derivation silently under-reports.

Each derived sha is stored with its own granularity marker, from one closed vocabulary
computed structurally from the diff:

| Marker | Meaning |
|---|---|
| `exact` | the commit adds exactly one bug's line **and** touches a file outside `specs/` |
| `release-squash` | the commit adds more than one bug's line |
| `ledger-only` | the commit adds exactly one bug's line and touches no file outside `specs/` |

`resolved_commit` stays `null` at resolve time — a commit cannot contain its own sha. The
**only writer of the cache is the audit's first pillar** ([[audits-canon]]), which writes
`audited` and all four provenance fields in a single atomic in-place rewrite through this same
seam, and reports a stored value that disagrees with the derivation as a finding. There is no
follow-up ledger commit.

`cause` and `caused_by` are never fabricated for history: a value populated from prose carries
`lineage_source: "text-reference"` so a reader knows it is inferred, and everything else is
`null`. The v5→v6 line **classifier** is permanent (`core/bug_provenance.py`) because this
repository's git history is v5-shaped forever; the v5 **fold adapter** and its legacy-surface
mapping table live in `features/bugs/migrate_v5.py`, imported by nothing permanent and
deletable whole.

### Commit shapes

Five isolated write shapes, **measured by the audit from `git log`, never by a hook**. Their
one operative home is `dd-gitflow-default` §3a; the product truth is that each stages nothing
else, so the audit can diff it.

| Shape | Staged alone | Message |
|---|---|---|
| Bug registration | `specs/bugs/BUGS.jsonl` | `chore(bugs): report <id>` |
| Backlog entry / ADR proposal | `specs/backlog/BACKLOG.md`, or the new `specs/ADRs/NNNN-<slug>.md` | `chore(backlog): add <slug>` / `docs(adr): propose NNNN-<slug>` |
| Bug fix — one commit, no second | code + regression test + the `BUGS.jsonl` line | `fix(<scope>): <what> (resolves <id>)` |
| Release definition | SPEC + PLAN + TASKS + purge-on-pick + the picked bugs' records; an `_ideas/` variant carries the SPEC only | one bundled commit |
| ADR acceptance | the ADR's status flip + the Part-1 principle hunk it admits | `docs(adr): accept NNNN-<slug>` |

A resolve is **not followed by a push** (the operator asks for that), and the preflight runs
before a push because it is an always-on rule, never because a hook forces it.

## Backlog

The backlog is the operator's demand queue: only the operator creates demand.
`project-manager` curates it as a single source, `specs/backlog/BACKLOG.md`, which is a **live
photo — `## ACTIVE` only**. The in-file `## LEDGER` section is retired. Every other agent
reads it freely and none writes to it.

**Exits move to a histo file.** Leaving `ACTIVE` appends one record
`{ts, slug, disposition, reason, release, by, entry_md}` — the full entry snapshot — to
`specs/backlog/_archive/backlog_histo.jsonl`, through the same write-time redaction the bug
ledger uses. The disposition vocabulary is unchanged. Consumption is executed at two moments
against **one** record: `project-manager`'s purge-on-pick removes the `## ACTIVE` subsection in
the same commit that creates the release SPEC and appends the (often provisional) exit record;
the closure disposition sweep **rewrites that same record's** `disposition`/`reason`/`release`
in place to its terminal token. Never a second line. `**Consumes:**` in a SPEC is provenance,
not a call site — no verb reads it.

Intake is operator-gated. No agent materializes an entry: a residual found at a closure, review
or audit is only listed as an intake candidate, and `project-manager` compiles those residuals
into an intake report — the ordinary handoff-first shape with a human target — that the
operator approves, rejects or discards before anything reaches `ACTIVE`. The one carve-out is a
deferral the operator ratified during a release: already-approved intake, not re-adjudicated.
Only an **actionable defect** reaches an intake report; a record-only observation terminates in
the release's closure record.

Curation is continuous, not a release-boundary event. Every touch runs a staleness scan and a
dedup scan of the whole file, so a near-duplicate subject is merged into the existing item
instead of filed twice. Nothing is deleted: an item leaves `ACTIVE` only by gaining its histo
record. The entry schema, the intake protocol and the terminal disposition vocabulary have
exactly one home — the `dd-backlog-definition` skill.

The single source is physical. `specs/backlog/` holds exactly `BACKLOG.md`, `AGENTS.md` and
`_archive/`; `remote-bugs/` is retired. There are no per-entry files in the live tree, and
`specs/backlog/_archive/` is the historical store for every superseded entry file, the retired
`candidates.md` index, `backlog_histo.jsonl`, and `consumed_backlog_histo.jsonl` — the 18
relocated per-release `consumed_backlog.json` sidecars, one record per release carrying its
consumed slugs.

`features/backlog/document.py` parses the document into a typed model with its roots injected
and no I/O outside the supplied path. An `### <slug>` ACTIVE subsection carries five required
keys — `Title`, `Opened` (`YYYY-MM-DD`), `Status`, `Description`, `Provenance` — plus the
optional `Intents`, holding the typed `intents[]` YAML in a fenced span. Parsing is diagnostic
and never throws: a malformed subsection or an unparseable intents block is captured as a
located error naming section, slug and line, and an absent document is an empty model.

`dadaia backlog doctor` validates that model with **three** codes. **BL-SCHEMA** — a located
parse error, an invalid status token, a slug outside `^[a-z][a-z0-9-]+$`, or an item at
`candidate` or beyond with no bound or an unresolvable `intents[]` subject (`idea` stays
exempt). **BL-CONFLICT** — two ACTIVE items sharing an anchor with an incompatible change.
**BL-STALE** — an ACTIVE item already consumed or dispositioned, read from
`consumed_backlog_histo.jsonl`, from its own histo exit record, or from its own terminal status.
**BL-DUP is deleted, not disabled**: with the ledger out of the document, a duplicate ledger
line is structurally impossible. `dadaia backlog new <slug>` appends one conformant subsection
at `status: idea`, creates the document when absent, and refuses a slug already present.
`specs doctor` backstops from the other side with SPEC-DOC-031 and SPEC-DOC-035, both WARNING.

## Branches And Stage Placement

The branch contract has exactly two homes: one section of the law states it, and the universal
skill `dd-gitflow-default` operates it. This atom restates neither — it records only where work
is placed. Three branch patterns exist and no fourth (`hotfix/*` is retired, reachable only on
an explicit operator request), and exactly one feature branch is live at a time.

Stage placement is therefore trivial: **every agent stage runs on the one live feature branch**
— backlog definition, research, bug registration, release definition and release implementation
alike, with a commit after every registration. `develop` and `main` are pull-request targets
only; neither is ever a working branch, and a local commit on either could never be published.

## Merge Cadence

Each release directory carries **`RELEASE.jsonl`**, an append-only stream of
`release-event-v1` records with the envelope `{ts, event, agent, data}` and no `session_id` —
a harness session id is protected local state and never enters a governance record. Exactly
**seven** kinds exist: `phase`, `defined`, `implemented`, `shipped`, `audited`, `rc`, `note`.
`ACTIVE.md` and `CLOSURE.md` are retired with no replacement file.

The fold has **one home and one reader**: `core/release_events.py` parses and folds, contains
no write call and no file I/O at all, and `features/specs/doctor_release.py` owns the single
disk read. The **last `phase` record wins** — that fold is what resolves the active release and
phase for the SDD gate, the doctor and every navigating agent. The three sha-bearing
milestones are immutable facts and the fold takes the **first** record of each, reporting a
later duplicate as SPEC-DOC-043, a WARNING that never blocks. `defined` carries `{sha, pr}` at
the definition promotion commit; `implemented` carries `{sha, rc}` written at the **final-`rc`
QA close, on that closed commit's sha** rather than the merge commit; `shipped` carries
`{sha, pr, tag}` at the ship merge; `audited` carries `{sha, audit}`.

Records are appended by agents with file tools — no code writes the stream. That is sound
because the file is **append-only**: no read-modify-write, so `O_APPEND`'s race-benign property
is kept for free, which is exactly the property the bug ledger had to give up.

**The closure narrative lives in `note` records**, keyed by `data.kind` — `closure-summary`,
`closure-size-accounting`, `closure-drift` (one per drift), `closure-test-dispositions`,
`closure-artifact-gc`. Everything else the retired `CLOSURE.md` carried has a **native** home
instead: dispositions in `backlog_histo.jsonl`'s `release` field and `BUGS.jsonl`'s
`resolved_release`; tasks in `TASKS.md`'s `[x]` markers and their commits; validations in the
per-task handoffs and the trio's verdicts; memory updates in the atom diffs themselves;
record-only observations in the reviewer's own findings array; intake candidates handed
directly to the PM's intake report; and the archive decision implicit in the `git mv` plus the
`phase: ARCHIVED` record.

Release ids are **bare semver**. A `v` prefix names the retired spec-lineage axis and resolves
only for read-only lookups of an already-archived directory; nothing can mint a `v`-prefixed
id. `specs/releases/_ideas/<id>/` holds a **SPEC only** — it carries no `RELEASE.jsonl`, is
never an audit-window source, and is refused as an evidence root by the CI verdict gate.

`develop` advances only by pull request from the live feature branch, at two kinds of moment:
once when the definition trio SPEC/PLAN/TASKS is `Aprovado`, and once per **release candidate**
thereafter. `main` advances only by pull request from `develop`, at the final candidate. Both
edges are gated by a CI check requiring an APPROVED security-reviewer verdict covering the PR
head sha, read from committed evidence ([[sdd-gate-v3]]).

There is **no alpha and no beta**. A release matures through `rc-N` only, and `rc-N` is a state
of the specs — it lives in the `phase` record's `data.segment` and in TASKS, never in a branch
name. `rc-1` burns when the whole implemented scope is validated, gate-green and closed by QA.
Each later `rc` is an adjustment round over that same scope, discovered by exercising the
merged `develop`: one candidate per merge, and **no new backlog ever enters a candidate**. If
nothing is found, the final candidate is `rc-1`. An internal work boundary inside a release — a
segment closed by a committed QA review — is not a candidate: it never merges and burns no
`rc`.

A release ends in one fixed order: **review → closure → archive → ship**. The pre-PR six-axis
code review of the delta runs on the **thawed** tree, before the `git mv` that freezes the
release directory. Inside closure the order is memory update → the closure `note` records →
disposition sweep → artifact GC → archive. A group of completed tasks is one commit; a release
defined and reviewed is a mandatory commit and push.

Task reservations stay observable even when the worker cannot commit. A dispatcher relaying
work for a **shell-less sub-agent** commits that sub-agent's `[ ]`→`[-]` flip **before**
relaying the next work item, never batched at the end.

## Release And Audit

Release definition records exactly which backlog and bug inputs are consumed; at pick time,
open bugs and undispositioned audits outrank fresh backlog. Closure gives each consumed item a
terminal disposition and evidence.

Residual routing is calibrated by signal class, so the operator's demand queue receives demand
and nothing else. Reviews still find and record **everything** — never-silent holds, every
observation kept in its reviewer's findings array. What differs is where an observation
terminates: a **record-only** observation (INFO-grade, awareness-only, or already fixed at HEAD)
lands in the closure `note` records or the reviewer handoff and stops there; only an
**actionable defect** — LOW or above with a concrete fix surface — becomes an intake candidate.
Zero observations are lost either way.

Audits are committed spec artifacts under `specs/audits/`, run as three pillars over a sha
window, and dispositioned by exactly one remediation release — the full contract is
[[audits-canon]]. One audit generates exactly one remediation release, that release gives every
finding an explicit disposition, and the folder archives only when no finding is `open`.

Bug, backlog, and audit paths are additive and writable without a bind or concurrency lock.
Production release artifacts and code follow the ordinary path and phase rules.

A **merge** is blocked until an APPROVED security-reviewer handoff covers the pull request's
head sha; a push is blocked only by the branch policy, the content scan and an unresolvable
runner. The gating review is diff-based only; a full-tree scan exists solely in the audit lane.
This is a quality boundary, not a concurrency mechanism.

## Runtime State

- `specs/bugs/BUGS.jsonl` — the one canonical ledger, one record per bug
- `specs/bugs/_archive/bugs_histo.jsonl` — records archived by `dadaia bugs archive`;
  `specs/bugs/_archive/archive.jsonl` — the byte-frozen legacy store
- `specs/backlog/BACKLOG.md` — the live photo, `## ACTIVE` only
- `specs/backlog/_archive/backlog_histo.jsonl` — one rewritable exit record per slug;
  `consumed_backlog_histo.jsonl` — the relocated per-release consumed-slug records
- `specs/releases/<id>/RELEASE.jsonl` — phase, milestones and the closure narrative;
  `specs/releases/_archive/releases_histo.jsonl` — the back-filled milestone blocks
- `specs/releases/_ideas/<id>/SPEC.md` — a pre-approval SPEC, and nothing else
- `.dadaia/reports/<context>/project-manager/<UTC>-intake/` — the operator-facing intake
  report and its handoff
- `specs/audits/<YYYYMMDD>-<slug>/` and, once dispositioned, `specs/audits/_archive/<audit>/`
- `specs/releases/<id>/verdicts/<sha>.handoff.json` — the committed review evidence the PR
  gate reads; `specs/releases/<id>/reviews/` — the segment and release review artifacts
- `pyproject.toml` and `CHANGELOG.md` at the release's final-candidate merge

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[audits-canon]], [[agent-comms]].
