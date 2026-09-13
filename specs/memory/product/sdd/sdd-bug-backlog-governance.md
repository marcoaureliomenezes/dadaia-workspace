---
slug: sdd-bug-backlog-governance
title: sdd-bug-backlog-governance
tldr: One bug record with closed_at at the terminal transition, a backlog exiting once at closure as one histo record, the release state document and its three verbs.
summary: The bug ledger, the backlog live photo, the release state document and the ADR ledger — one record per bug, one write seam, one histo-record-v1 shape for every exit, one mutable _RELEASE.json per release born and archived by one verb each, every committed record schema-validated by dadaia doctor.
tags: [sdd, governance, release-lifecycle, backlog, bugs, adrs, gitflow]
---

## Bugs

- `specs/bugs/BUGS.jsonl` is the single canonical ledger: one record per bug, appended once, keyed by `id`, git history being that line's change log.
- `bug-record-v1.schema.json` names every field and marks it immutable core, write-once or mutable governance; `core/models/bugs.py` mirrors its `status` and `diff_direction` enums and `evidence_diff` pattern zero-I/O, pinned by `tests/contract/test_bug_record_schema.py`; `dadaia doctor`'s `ledgers` section validates every committed line (`LEDGER-BUGS-SCHEMA`, [[workspace-doctor]]).
- `status` is `open | resolved | superseded | deferred | rejected`; `resolved` requires a regression seam, a sweep closure is `superseded_by`, and a reopen is a new record declaring `caused_by`.
- `closed_at` is stamped once by `BugRecord._reach_terminal`, the one exit every terminal transition ends in: non-null iff `status` is terminal, never earlier than `ts`, never rewritten by `update`.
- `surface` is a closed enum whose feature arm equals the import-linter independence contract's `modules =` list; `component` is free-text `path#symbol`.
- `features/bugs`'s record store is the only code path that writes a governance field, sanitizing then masking each write once through the push scan's denylist loader, and rewriting compare-then-swap with refuse-stale plus retry ([[sdd-gate-v3]]).
- `JsonlRecordStore.scan()` is the ledger's one parser, yielding a `MalformedLine` for a row it cannot read, so every reader — the CLI, the doctor, the audit — diagnoses a bad line identically.
- A terminal status is reachable only through a transition that carries its evidence: `BugRecord.resolve/supersede/defer/reject` raise `IncompleteTransitionError` on missing input, and the model itself refuses a bare `status` or `closed_at` key.
- Nine verbs sit over that seam — `append`, `status`, `stats`, `update` (refusing an immutable core field, a second write to a write-once field, and `status`/`closed_at` outright), `resolve` (deriving `diff_direction` from `--evidence-diff`'s `net-*:` prefix — no separate flag), `supersede`, `defer`, `reject` and `archive`; no `--event` flag exists.
- Legacy v5-fold records carry `migration_note="v5-fold-incomplete"` and warn no further.
- `bugs archive` idempotently moves records whose `closed_at` is older than 90 days (`core/models/bugs.py::BUG_ARCHIVE_THRESHOLD_DAYS`) to `_archive/bugs_histo.jsonl`; `dadaia release rc-archive` and `dadaia release archive` run it; a filing date never makes a record archivable, and `SPEC-DOC-041` warns by the same field.
- A bug is fixed on the spot on the live feature branch — register, root-cause, RED test, fix, GREEN, `resolved` with evidence, commit — with no SPEC, PLAN, TASKS or release directory.
- Diagnosis is seven ordered phases, phase 0 being the lineage duty over the 20 most recent records sharing this bug's `surface` or `component` in the audit window, ending in `caused_by: <bug-id> | none` with evidence (`dd-bug-resolution`).
- `registration_commit` and `resolved_commit` are a git-derived cache (`core/bug_provenance.py`, all-refs first-add-wins over `specs/bugs/`, additions only) at granularity `exact`, `release-squash` or `ledger-only`, only `exact` being diffable lineage; the audit's first pillar is its only writer ([[audits-canon]]).

## Backlog

- Only the operator creates demand; `project-manager` curates `specs/backlog/BACKLOG.json`, whose `active[]` holds the live candidate set, and every other agent reads it.
- `specs/backlog/` holds exactly `BACKLOG.json`, `AGENTS.md` and `_archive/backlog_histo.jsonl`.
- Leaving `active[]` appends one `histo-record-v1` `{id, ts, disposition, release, reason, summary, entry}` to `backlog_histo.jsonl`, `entry` being the removed object and `disposition` one of `delivered superseded rejected`; a deferred item returns to `active[]` rather than exiting.
- A picked item stays `picked` in `active[]` for the whole candidate and exits once, at the closure disposition sweep — never a provisional record at pick time, never a second line for the same slug.
- A SPEC's `**Consumes:**` line is provenance, not a call site.
- Intake is operator-gated: a residual is listed as an intake candidate for `project-manager`, the one carve-out being a deferral the operator ratified during a release.
- The entry schema (`backlog-v1`), the document parser and the doctor validate an entry through one checker; `dadaia doctor`'s `ledgers` section runs `BL-SCHEMA`, `BL-CONFLICT`, `BL-STALE` (a live slug already carrying a histo record, or whose own status is terminal) and `LEDGER-BACKLOG-SCHEMA`/`LEDGER-BACKLOG-HISTO-SCHEMA`, backstopped by `SPEC-DOC-035` ([[workspace-doctor]]).
- `core/models/histo.py` is the one home of the terminal vocabulary `delivered resolved superseded deferred rejected`; each histo — backlog, audits, releases — validates against its own subset, and `HistoRecord.redact` masks every free-text field, `entry` included, through the same primitive the bug record uses.

## The release state document

- Each release directory carries `_RELEASE.json`, one mutable `release-state-v1` document `{schema, release, phase, rc, defined, implemented, shipped, log}` parsed by `core/release_state.py` (no file I/O) and updated with file tools; the filename is the one decider `core.release_state.RELEASE_STATE_FILENAME`.
- The release model is release-candidates (0.4.6, ADRs 0005-0009): exactly one live release named last-published-PyPI + 1 patch, OPEN scope; each candidate is a closed-scope SDD cycle whose trio sits at the release root; `rc` counts the archived candidates under `rc-N/`; the version increments only at operator-approved deploy.
- `phase` is one of `DEFINITION IMPLEMENTATION CLOSURE ARCHIVED` (`core.release_state.PHASES`, the one home the schema enum, the doctor and the release verbs import; the gate reads no phase); `phase` and `rc` are rewritten in place on every transition.
- Milestones carry their sha and are set once: `defined {sha, ts}` by `product-engineer` at the definition promotion commit, `implemented {sha, rc, ts}` by `qa-engineer` at the final-rc QA close, `shipped {sha, pr, ts}` by `dadaia release archive`.
- `log` is the one append-only array — entries `{ts, agent, kind, text}`, `ts` non-decreasing, `kind` one of `note summary size drifts dispositions test-dispositions artifact-gc reviews merge memory` — and the closure narrative's only home; tasks, verdicts and dispositions keep their native homes (`TASKS.md` markers, handoffs, the histos, `BUGS.jsonl`).
- `dadaia release new <id>` is the one birth act: `SPEC.md` stub plus `_RELEASE.json` in `DEFINITION` (`rc: null`, one `note`) written in one transaction, refusing a second live release or an existing artifact with a `fix:` line.
- `dadaia release rc-archive` (continue): validates the whole tree, requires the trio at root, every task `[x]` and phase `CLOSURE`, moves the trio to `rc-N/`, sets `rc = N` and `phase: DEFINITION`, then runs `bugs archive`.
- `dadaia release archive <id> --shipped <sha> --pr <n> --next <M.m.p>` (promote): validates the tree, every task `[x]`, `CLOSURE` and `implemented`; sets `shipped` and `ARCHIVED`, moves the directory to `_archive/<id>/` with its final trio at root, births `<next>` through `release new`, appends one `delivered` record to `releases_histo.jsonl` last, runs `bugs archive`; all-or-nothing, every refusal a `fix:` line; it prints the git `next:` lines (commit, branch delete, cut + `merge -s ours origin/develop`) and never runs git.
- `features/specs/release_tree.py::validate_release_tree` is the one reader of every state document, live and archived, shared by the doctor and both verbs ([[workspace-doctor]]).
- Inside closure the order is memory update, closure `log` entries, disposition sweep, artifact GC, the `feature -> develop` PR, then the promote-or-continue gate; the pre-PR three-axis review runs before the merge.
- Release ids are bare semver; a `v` prefix resolves only for a read-only lookup of an archived directory.
- `specs/releases/_ideas/<id>/` holds a SPEC only — no `_RELEASE.json`, never an audit-window source or evidence root.

## Decisions

- `specs/ADRs/decisions.jsonl` (`decision-record-v1`) is the ADR ledger; a superseded decision keeps its line with `status: superseded` — no `_superseded/` directory exists.
- `measured_by` must match the resolvable pattern the schema enforces — `pytest <path>[::node] [-k …]`, `lint-imports …`, a `SPEC-DOC-nnn`, `WS-…`, `BL-…`, `RELEASE-TREE-…` or `LEDGER-…` code, `dadaia doctor`/`dadaia bugs status` — so every accepted decision names a check that runs.
- A record born from an operator grill ruling is appended `accepted` with the ruling date in `context`; any other record is `proposed` until the operator flips it; `LEDGER-ADR-SCHEMA` validates every committed line ([[workspace-doctor]]).

## Dependencies

[[workspace-doctor]], [[sdd-gate-v3]], [[audits-canon]], [[agent-comms]].
