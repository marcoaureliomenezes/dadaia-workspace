---
name: bug-report-workflow-omits-session-id-frontmatter
status: Closed
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

## Resolution

Fixed in v0.1.40 alpha-1 T7.

Root cause: the bug-report workflow had two writers/prompts for the same record
contract. The public `bug_report.bug_write` fragment did not explicitly require
`session_id:`, and the deterministic fake bug-report runtime in `container.py`
materialized Markdown without `session_id: null`. The `FakeAgentRuntime` generic path
also did not materialize bug records, so the workflow contract could pass without
proving the file shape.

Fix:

- `container._bug_report_runtime_factory` now writes `reported:` and
  `session_id: null` in fake bug records and resolves writes through the shared
  workspace-state root.
- `FakeAgentRuntime` now materializes in-scope bug records for bug-report fake runs.
- `public/lifecycle_fragments/bug_report/bug-write.md` now states that `session_id:`
  is mandatory and must be `null` when unknown.

Evidence:

- `pytest -p no:cacheprovider tests/integration/cli/test_lifecycle_bug_report_workflow.py ... -q`
  included the TREE-7 regression and passed in the focused 66-test run.
- `dadaia lifecycle bug report --harness fake --json` completed with status `OK` during
  T7 validation; the temporary smoke bug was removed after verification.
