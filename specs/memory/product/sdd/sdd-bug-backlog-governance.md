---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
category: product
tldr: One record per bug through one write seam, a live-photo backlog with histo exits, and the RELEASE.json state document.
summary: The bug ledger, the backlog live photo and the release state document — one record per bug, one write seam, one exit record per backlog slug, one mutable RELEASE.json per release.
tags: [sdd, governance, release-lifecycle, backlog, bugs, gitflow]
---

## Bugs

- `specs/bugs/BUGS.jsonl` is the single canonical ledger: one record per bug, appended once, keyed by `id`, git history being that line's change log.
- `bug-record-v1.schema.json` names every field and marks it immutable core, write-once or mutable governance.
- `status` is `open | resolved | superseded | deferred | rejected`; `resolved` requires a regression seam, a sweep closure is `superseded_by`, and a reopen is a new record declaring `caused_by`.
- `surface` is a closed enum whose feature arm equals the import-linter independence contract's `modules =` list; `component` is free-text `path#symbol`.
- `features/bugs`'s record store is the only code path that writes a governance field, sanitizing then masking each write once through the push scan's denylist loader, and rewriting compare-then-swap with refuse-stale plus retry ([[sdd-gate-v3]]).
- Five verbs sit over that seam — `append`, `status`, `stats`, `update` (refusing an immutable core field and a second write to a write-once field) and `archive`; no `--event` or `resolve` verb exists.
- `bugs archive` idempotently moves terminal records older than 90 days to `_archive/bugs_histo.jsonl`.
- A bug is fixed on the spot on the live feature branch — register, root-cause, RED test, fix, GREEN, `resolved` with evidence, commit — with no SPEC, PLAN, TASKS or release directory.
- Diagnosis is seven ordered phases, phase 0 being the lineage duty over the 20 most recent records sharing this bug's `surface` or `component` in the audit window, ending in `caused_by: <bug-id> | none` with evidence (`dd-diagnose`).
- `registration_commit` and `resolved_commit` are a git-derived cache (`core/bug_provenance.py`, all-refs first-add-wins over `specs/bugs/`, additions only) at granularity `exact`, `release-squash` or `ledger-only`, only `exact` being diffable lineage; the audit's first pillar is its only writer ([[audits-canon]]).

## Backlog

- Only the operator creates demand; `project-manager` curates `specs/backlog/BACKLOG.json`, whose `active[]` holds the live candidate set, and every other agent reads it.
- `specs/backlog/` holds exactly `BACKLOG.json`, `AGENTS.md` and `_archive/`, the last carrying `backlog_histo.jsonl` and `consumed_backlog_histo.jsonl`.
- Leaving `active[]` appends one record `{ts, slug, disposition, reason, release, by, entry}` to `backlog_histo.jsonl`.
- Consumption executes against that one record twice: purge-on-pick removes the entry in the SPEC-creating commit and appends the provisional exit, and the closure sweep rewrites its `disposition`/`reason`/`release` in place — never a second line.
- A SPEC's `**Consumes:**` line is provenance, not a call site.
- Intake is operator-gated: a residual is listed as an intake candidate for `project-manager`, the one carve-out being a deferral the operator ratified during a release.
- `dadaia backlog doctor` validates the parsed model with BL-SCHEMA (parse, status token, slug, unbound or unresolvable `intents[]` beyond `candidate`), BL-CONFLICT (two active items sharing an anchor incompatibly) and BL-STALE (an active item already consumed), backstopped by SPEC-DOC-031 and SPEC-DOC-035.

## The release state document

- Each release directory carries `RELEASE.json`, a mutable `release-state-v1` document parsed by `core/release_state.py` and updated with file tools.
- `phase` is a plain top-level field — no stream, no fold — beside `release`, `rc`, the milestones `defined`, `implemented`, `shipped`, `audited`, and a `log` array.
- Milestones are immutable once set, each carrying its sha: `defined` at the definition promotion commit, `implemented` at the final-`rc` QA close, `shipped` at the ship merge, `audited` at the audit.
- `rc-N` is a state of the specs living in `rc`/`segment` and in TASKS, never a branch name; an internal segment closed by a committed QA review burns no `rc`.
- The closure narrative lives in `log` entries `{ts, agent, kind, text}` over `closure-summary`, `closure-size-accounting`, `closure-drift`, `closure-test-dispositions` and `closure-artifact-gc`.
- Everything else has a native home: dispositions in the histo and `BUGS.jsonl`, tasks in `TASKS.md` markers, validations in handoffs and verdicts, memory updates in atom diffs, archival in `phase: ARCHIVED`.
- Inside closure the order is memory update, closure log entries, disposition sweep, artifact GC, archive, with the pre-PR six-axis review running on the thawed tree.
- Release ids are bare semver; a `v` prefix resolves only for a read-only lookup of an archived directory.
- `specs/releases/_ideas/<id>/` holds a SPEC only — no `RELEASE.json`, never an audit-window source or evidence root.

## Dependencies

[[specs-doctor]], [[sdd-gate-v3]], [[audits-canon]], [[agent-comms]].
