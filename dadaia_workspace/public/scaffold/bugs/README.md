# Bugs

This directory holds this Spec Context Project's event-sourced bug ledger: one
append-only JSONL stream, `bugs.jsonl`, validated against the `bug-event-v1` schema.
There is no per-bug Markdown file and no session-lock gate on filing.

## Authoring Rules

- Append events with `dadaia bugs append --bug-id <slug> --event <kind> ...` — do NOT
  hand-edit `bugs.jsonl` to keep every entry schema-valid (`dd-bug-registration`).
- `<slug>` is a stable kebab-case bug identifier reused across every event for the same
  bug (`reported`, then eventually `resolved`/`superseded`/`deferred`/`rejected`).
- `--event reported` (the default) requires `--title`, `--severity`
  (`LOW|MEDIUM|HIGH|CRITICAL`), `--surface`, `--component`, `--context`, `--symptom`,
  `--repro`, and `--expected`; `--tag` is repeatable and optional.
- `reported`, `resolved`, `superseded`, `deferred`, and `rejected` are terminal states —
  at most one terminal event per bug_id. `picked` and `archived` are non-terminal
  annotations layered on an existing stream.
- Bug reports are **not** specs. They do not authorise implementation changes on their
  own. A bug may be addressed in a dedicated release or as part of an existing one.
- Never delete events once appended — the ledger is append-only; a fix closes a bug by
  appending a `resolved` event with `--resolution-evidence`, never by removing history.

## Relationship to Sessions

There is no session-lock gate on filing a bug (NO-LOCKS DOCTRINE): `bugs append` never
blocks on session state. `--reported-by` records the agent/runtime that recorded the
event; concurrent sessions racing to file the same `bug_id` are surfaced, never
prevented — `dadaia bugs status`/`stats` fold the stream into current state.
