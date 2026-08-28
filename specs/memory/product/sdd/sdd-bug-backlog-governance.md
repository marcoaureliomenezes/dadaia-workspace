---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: One record per bug through one write seam, a live-photo backlog with histo exits, and the RELEASE.json state document.
summary: The bug ledger, the backlog live photo and the release state document — one record per bug, one write seam, one exit record per backlog slug, and one mutable `RELEASE.json` per release.
tags:
- sdd
- governance
- release-lifecycle
- backlog
- bugs
- gitflow
---

## Bugs

`specs/bugs/BUGS.jsonl` is the single canonical ledger: one record per bug, appended once, keyed by
`id`. No event stream, no state machine, no fold — a bug's state is its one line, and git history is
that line's change log. `bug-record-v1.schema.json` (`additionalProperties: false`) names the fields
and marks each per property as immutable core, write-once, or mutable governance.

`status` is `open | resolved | superseded | deferred | rejected`; a pick is not a status. A sweep
closure is `superseded` with `superseded_by`; `resolved` requires a regression seam. A reopen is a
new record with a new `id` declaring `caused_by: <prior-id>`. `surface` is a closed enum whose one
source is the `features/*/` package inventory on disk plus `core`, `infrastructure`, `cli`, `hooks`,
`tests`, `public-assets`, `unknown`, its feature arm asserted equal to the import-linter
independence contract's `modules =` list; `component` keeps free-text `path#symbol` precision.
Evidence is `evidence_loop`, `evidence_seam` and `evidence_diff`, closed by `diff_direction` onto
`net-negative | net-neutral | net-positive`.

`features/bugs`'s record store is the only code path that writes a governance field. Every write is
**sanitize, then mask**, each once: sanitation deletes the control ranges (preserving TAB/LF/CR) by
deletion rather than escaping, so a split term re-joins for the masking pass; masking consumes the
operator denylist through the same loader the push-boundary scan uses ([[sdd-gate-v3]]). The rewrite
is a compare-then-swap: refuse-stale, then retry. The backlog histo writer uses the same redaction.
Five verbs sit over that seam — `append`, `status`, `stats`, `update` (the governance door, refusing
an immutable core field and a second write to a write-once field) and `archive`; there is no
`--event` flag and no `resolve` verb. `bugs archive` moves terminal records older than 90 days to
`_archive/bugs_histo.jsonl`, idempotently; the legacy `_archive/archive.jsonl` stays byte-frozen.
Coherence gaps are surfaced by `bugs status` and SPEC-DOC-033 with the exit code unchanged — the
record contract is audited, never gated.

**Resolution.** A bug is fixed on the spot — register → root-cause → RED test → fix → GREEN →
`status: resolved` with evidence → commit — on the one live feature branch, in whatever phase it is
in, with no SPEC, PLAN, TASKS or release directory. Releases are never created to fix bugs.
Diagnosis is seven ordered phases; **phase 0 is the lineage duty**: filter the ledger for records
sharing this bug's `surface` or `component` inside the audit window, capped at the 20 most recent by
resolution date, diffing only those with `resolution_granularity == "exact"`, and ending in
`caused_by: <bug-id>` or `caused_by: none` with evidence, in the record and in the fix commit body.
When no correct seam exists the absence is the finding: an architecture finding is registered and
`software-architect` dispatched before the fix proceeds, as does any net-positive diff.

**Provenance.** `registration_commit` and `resolved_commit` are a cache over git, never a second
truth, derived by `core/bug_provenance.py` from an all-refs chronological first-add-wins walk over
`specs/bugs/` in which only additions count; granularity is `exact` (one bug's line plus a file
outside `specs/`), `release-squash` or `ledger-only`. `resolved_commit` stays `null` at resolve
time, and the only writer of the cache is the audit's first pillar ([[audits-canon]]). A `cause` or
`caused_by` populated from prose carries `lineage_source: "text-reference"`; neither is ever
fabricated. Five isolated write shapes exist, measured by the audit from `git log` and never by a
hook; their operative home is `dd-gitflow-default`, and each stages nothing else.

## Backlog

Only the operator creates demand. `project-manager` curates one source,
`specs/backlog/BACKLOG.json`, whose `active[]` holds the live candidate set; every other agent reads
it and none writes it. `specs/backlog/` holds exactly `BACKLOG.json`, `AGENTS.md` and `_archive/`,
the last holding `backlog_histo.jsonl` and `consumed_backlog_histo.jsonl`.

Leaving `active[]` appends one record `{ts, slug, disposition, reason, release, by, entry}` to
`backlog_histo.jsonl`. Consumption executes at two moments against **one** record: purge-on-pick
removes the entry in the same commit that creates the release SPEC and appends the (often
provisional) exit record; the closure disposition sweep rewrites that record's
`disposition`/`reason`/`release` in place to its terminal token. Never a second line.
`**Consumes:**` in a SPEC is provenance, not a call site.

Intake is operator-gated: no agent materializes an entry. A residual found at a closure, review or
audit is listed as an intake candidate for `project-manager`'s operator-facing intake report; the
one carve-out is a deferral the operator ratified during a release, and a record-only observation
terminates in the closure notes instead. Every touch runs a staleness and dedup scan of the whole
document. Entry schema, intake protocol and disposition vocabulary: `dd-backlog-definition`.
`dadaia backlog doctor` validates the parsed model with **BL-SCHEMA** (a located parse error, an
invalid status token, a bad slug, or an item at `candidate` or beyond with no bound or unresolvable
`intents[]` subject — `idea` exempt), **BL-CONFLICT** (two active items sharing an anchor with an
incompatible change) and **BL-STALE** (an active item already consumed or dispositioned);
`specs doctor` backstops with SPEC-DOC-031 and SPEC-DOC-035.

## The release state document

Each release directory carries `RELEASE.json`, a mutable `release-state-v1` document parsed by
`core/release_state.py`: `phase` is a plain top-level field — no stream, no fold — beside `release`,
`rc`, the milestone objects `defined`, `implemented`, `shipped` and `audited`, and a `log` array.
Agents update it with file tools. `phase` resolves the active release and phase for the SDD gate,
the doctor and every navigating agent. The milestones are immutable once set, each carrying its sha
plus its own fields — `defined` `{sha, ts, pr}` at the definition promotion commit, `implemented`
`{sha, rc}` at the final-`rc` QA close, `shipped` `{sha, pr, tag}` at the ship merge, `audited`
`{sha, audit}`. `rc-N` is a state of the specs living in `rc`/`segment` and in TASKS, never a branch
name; an internal segment closed by a committed QA review burns no `rc`.

**The closure narrative lives in `log` entries** — `{ts, agent, kind, text}` — over the kinds
`closure-summary`, `closure-size-accounting`, `closure-drift` (one per drift),
`closure-test-dispositions` and `closure-artifact-gc`. Everything else has a native home:
dispositions in `backlog_histo.jsonl` and `BUGS.jsonl`, tasks in `TASKS.md` markers and their
commits, validations in handoffs and verdicts, memory updates in the atom diffs, the archive
decision in the `git mv` plus `phase: ARCHIVED`. Inside closure the order is memory update → closure
log entries → disposition sweep → artifact GC → archive, the pre-PR six-axis code review running on
the thawed tree before the `git mv` that freezes the directory.

Release ids are bare semver; a `v` prefix resolves only for read-only lookups of an already-archived
directory. `specs/releases/_ideas/<id>/` holds a SPEC only — no `RELEASE.json`, never an
audit-window source, refused as an evidence root by the CI verdict gate. Audits are committed spec
artifacts dispositioned by exactly one remediation release ([[audits-canon]]).

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[audits-canon]], [[agent-comms]].
