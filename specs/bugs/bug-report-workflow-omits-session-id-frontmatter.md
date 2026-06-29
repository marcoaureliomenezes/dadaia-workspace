---
name: bug-report-workflow-omits-session-id-frontmatter
status: Open
severity: HIGH
reported: 2026-06-29
surface: lifecycle bug_report workflow / specs doctor TREE-7
session_id: null
---

# Bug-report workflow omits required `session_id:` frontmatter

**Symptom:** `dadaia lifecycle bug report` writes Markdown bug records without the
required `session_id:` frontmatter field. `dadaia specs doctor` then fails TREE-7 for
each generated bug file.

**Repro:**

1. Run `dadaia lifecycle bug report ... --harness fake --json`.
2. Inspect the generated `specs/bugs/<slug>.md`.
3. Run `dadaia specs doctor --specs-dir repos/dadaia-workspace/specs`.

**Expected:** The bug-report workflow writes a doctor-valid bug file, including
`session_id: null` when the session id is unknown.

**Actual:** Generated bug files omitted `session_id:`, producing TREE-7 errors until
the field was manually added.

**Fallback note:** This bug was recorded by direct Markdown fallback because the
`bug_report` workflow is the component being reported; using it again would create
another invalid bug record needing manual repair.
