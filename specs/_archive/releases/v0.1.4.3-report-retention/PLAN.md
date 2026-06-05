# PLAN: v0.1.4.3 - report-retention

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Strategy

Implement retention as a small workspace feature with one durable state file,
CLI commands, panel integration, and focused tests.

Do not add a daemon. Do not add a database. Do not create per-report marker
files. Keep the cleanup predictable: explicit CLI command plus panel
startup/listing cleanup for expired non-important reports.

## 2. Execution Order

```text
T-RET-01 -> T-RET-02 -> T-RET-03 -> T-RET-04 -> T-RET-05 -> T-RET-06
```

## 3. Design

### Retention State

Runtime state file:

```text
.dadaia/states/report_retention.json
```

Shape:

```json
{
  "version": 1,
  "important": {
    ".dadaia/reports/<context>/<agent>/<file>.html": {
      "marked_at": "2026-06-04T00:00:00Z",
      "reason": "operator requested"
    }
  }
}
```

Use workspace-relative normalized paths as keys. A handoff path passed to
`mark-important` resolves to the referenced report artifact when possible. If
the handoff has no artifact path, mark the handoff path itself as important.

### Cleanup Discovery

Build a report graph from:

- `.dadaia/reports/**/*.html`
- `.dadaia/reports/**/*.handoff.json` for legacy compatibility
- `.dadaia/handoff/**/*.handoff.json`

Each graph node is one logical report artifact:

- report path;
- canonical handoff paths that reference it;
- legacy sidecar paths that reference it or share the same stem;
- effective timestamp;
- important status;
- cleanup eligibility reason.

### Deletion Rules

Delete all files in an eligible node together. Never delete an important path.
When a handoff references a missing artifact and is older than the TTL, delete
the handoff unless it is important.

Use `Path.resolve()` and `relative_to()` against the workspace root to prevent
path traversal.

### CLI

Extend the existing reports command group instead of adding a new top-level
command:

```text
dadaia reports cleanup
dadaia reports mark-important
dadaia reports unmark-important
dadaia reports important
```

`cleanup --json` returns machine-readable counts and entries for panel use.

### Panel

Extend `/api/reports` entries with:

- `important: boolean`
- `expires_at: string | null`
- `is_expired: boolean`
- `retention_reason: string | null`

Add panel API mutations:

- `POST /api/reports/<path>/important`
- `DELETE /api/reports/<path>/important`

Keep existing `DELETE /api/reports/<path>` for manual deletion.

The Reports API/panel startup path runs cleanup for reports older than 48 hours
that are not important. Cleanup failures are surfaced as a non-blocking warning
in API metadata and logs; they must not make the panel unusable.

### Tests

Use temp workspaces under pytest `tmp_path`. Disable pytest cache with
`-p no:cacheprovider`. Do not write test reports or temp files inside the repo.

Test dimensions:

- 48-hour TTL calculation by `produced_at`, filename timestamp, and mtime fallback;
- important/unimportant state persistence;
- cleanup dry-run;
- cleanup deletes report plus handoff;
- cleanup preserves important reports;
- orphan handoff cleanup;
- path traversal rejection;
- panel API envelope and mutation behavior;
- panel UI rendering for important/expiring state.

## 4. Implementation Surfaces

Area | Likely files
---|---
Reports retention service | `dadaia_workspace/features/reports_retention/**` or existing reports feature if a local pattern fits better
CLI | `dadaia_workspace/cli/commands/reports.py`
Panel API | `dadaia_workspace/features/panel/views/api.py`, panel handler route table/container wiring
Panel UI | `dadaia_workspace/features/panel/views/assets/js/reports.js`, related CSS tokens if needed
Validation/tests | `tests/unit/features/reports_retention/**`, `tests/unit/features/panel/**`, `tests/contract/**`, `tests/integration/**`

## 5. Review And QA Contract

Before implementation starts, required reviewers must agree that:

- `qa-engineer` accepts the 48-hour TTL, dry-run, important/unimportant panel,
  and orphan cleanup acceptance tests.
- `security-reviewer` accepts path traversal, workspace-boundary, and deletion
  safety checks.
- `code-reviewer` accepts the graph-based cleanup model and no per-report marker
  files.
- `frontend-engineer` or `design-specialist` accepts the Reports tab controls if
  panel UI changes are implemented.

The task remains `[-]` until QA, code review, and security approval handoffs are
all present and approved for the same implementation artifact.

## 6. Validation

Minimum implementation validation:

```bash
pytest -q -p no:cacheprovider tests/unit/features/reports_retention
pytest -q -p no:cacheprovider tests/unit/features/panel -k reports
pytest -q -p no:cacheprovider tests/contract -k reports
pytest -q -p no:cacheprovider tests/integration -k reports
```

If panel UI is changed, add or update the focused browser test for the Reports
tab and store any Playwright output outside the repo under workspace
`.dadaia/tmp/`.

## 7. Hotfix Plan

For `T-BUG-REPORTS-01`, fix the Reports tab URL builder so each path segment is
encoded independently while `/` separators are preserved. Validate both:

- direct report route `/reports/<context>/<agent>/<file>.html`;
- encoded-segment route produced by the Reports tab click handler.
