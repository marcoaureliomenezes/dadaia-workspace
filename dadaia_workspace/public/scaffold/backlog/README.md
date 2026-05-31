# Backlog

This directory contains backlog entry files for this Spec Context Project.

## Authoring Rules

- Each backlog entry is a single Markdown file named `<slug>.md` where `<slug>` matches
  `^[a-z][a-z0-9-]+$`.
- Files are created with `dadaia backlog new <slug>` — do NOT create them manually to
  ensure canonical frontmatter.
- Required frontmatter fields:
  - `title`: short human-readable name
  - `status`: one of `idea`, `candidate`, `deferred`, `rejected`
  - `opened`: ISO date (YYYY-MM-DD)
  - `description`: one-paragraph description of the need
- Backlog entries are **not** specs. They do not authorise implementation. An entry must
  be promoted to a release (via `dadaia release new`) to enter the SDD lifecycle.
- Never delete backlog entries — change `status` to `rejected` or `deferred` instead.

## Relationship to Releases

A backlog entry may be referenced by a release SPEC using its slug. When a release is
opened to address a backlog item, add `release: <release-id>` to the backlog entry's
frontmatter to track the promotion.
