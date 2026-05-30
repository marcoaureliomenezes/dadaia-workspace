# Bugs

This directory contains bug report files for this Spec Context Project.

## Authoring Rules

- Each bug report is a single Markdown file named `<slug>.md` where `<slug>` matches
  `^[a-z][a-z0-9-]+$`.
- Files are created with `dadaia bug new <slug>` — do NOT create them manually to
  ensure canonical frontmatter.
- Required frontmatter fields:
  - `title`: short human-readable description of the bug
  - `severity`: one of `critical`, `high`, `medium`, `low`, `TBD`
  - `opened`: ISO date (YYYY-MM-DD)
  - `session_id`: the session identifier when the bug was observed, or `null` if unknown
  - `description`: reproduction steps and observed vs. expected behaviour
- Bug reports are **not** specs. They do not authorise implementation changes on their
  own. A bug may be addressed in a dedicated release or as part of an existing one.
- Do NOT delete bug reports once filed. Add a `resolved` field with the release ID when
  the bug is fixed.

## Relationship to Sessions

The `session_id` field links the bug to the session in which it was observed. In Release
2 (`spec-context-session-locks-v1`), `dadaia bug new` will be blocked when no session is
bound. In Release 1, `session_id` is written as `null` when no session is active.
