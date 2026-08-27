# specs/bugs/ — Bug Ledger Rules

Scope: this file governs only `specs/bugs/`. It replaces the retired `bugs/README.md`
(v6 canon, FR1) — its content lives here now.

This directory holds this Spec Context Project's event-sourced bug ledger: one
append-only JSONL stream, `BUGS.jsonl`, one record per bug. There is no per-bug
Markdown file and no session-lock gate on filing.

## Authoring Rules

- Append/update records with `dadaia bugs append --bug-id <slug> --event <kind> ...` —
  do NOT hand-edit `BUGS.jsonl` to keep every entry schema-valid
  (`dd-bug-registration`).
- `<slug>` is a stable kebab-case bug identifier reused across every event for the same
  bug (`reported`, then eventually `resolved`/`superseded`/`deferred`/`rejected`).
- `--event reported` (the default) requires `--title`, `--severity`
  (`LOW|MEDIUM|HIGH|CRITICAL`), `--surface`, `--component`, `--context`, `--symptom`,
  `--repro`, and `--expected`; `--tag` is repeatable and optional.
- `reported`, `resolved`, `superseded`, `deferred`, and `rejected` are terminal states —
  at most one terminal event per bug. `picked` and `archived` are non-terminal
  annotations layered on an existing record.
- Bug reports are **not** specs. They do not authorise implementation changes on their
  own. A bug may be addressed in a dedicated release or as part of an existing one.
- Never hand-delete a record once appended — a fix closes a bug by appending a
  `resolved` event with its evidence triple, never by removing history.

## Relationship to Sessions

There is no session-lock gate on filing a bug (NO-LOCKS DOCTRINE): `bugs append` never
blocks on session state. `--reported-by` records the agent/runtime that recorded the
event; concurrent sessions racing to file the same bug are surfaced, never
prevented — `dadaia bugs status`/`stats` fold the ledger into current state.
