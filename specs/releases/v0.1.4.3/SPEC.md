# SPEC: v0.1.4.3 - report-retention

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## 1. Objective

Stop stale agent reports from flooding the workspace while preserving reports
the user explicitly marks as important.

Reports are operational evidence, not permanent product memory. By default they
must expire quickly. The workspace must keep the Reports tab useful, keep
`.dadaia/reports/` and `.dadaia/handoff/` small, and avoid making users manually
delete old throwaway reports.

## 2. Product Rule

Default rule:

```text
Delete reports older than 48 hours unless the user explicitly marks them as
important in the panel.
```

This applies to:

- HTML reports under `.dadaia/reports/<context>/<agent>/*.html`
- canonical handoffs under `.dadaia/handoff/<context>/*.handoff.json`
- legacy adjacent handoff sidecars under `.dadaia/reports/**` when still present

The cleanup must delete a report and all machine records that reference it as
one logical artifact. It must not leave orphaned handoffs or orphaned HTML.

## 3. Product Requirements

### PR-1: 48-Hour Default Retention

Any report whose effective timestamp is older than 48 hours is eligible for
cleanup.

Timestamp precedence:

1. `produced_at` from canonical handoff JSON when available and valid.
2. Timestamp parsed from report or handoff filename when available.
3. File modification time as fallback.

### PR-2: Explicit Important Protection

Users must be able to mark a report as important in the Reports tab. Important
reports are protected from TTL cleanup.

Protection is explicit. A report is not important merely because it has
findings, is opened in the panel, belongs to a specific agent, or has a high
severity.

Canonical storage for important state:

```text
.dadaia/states/report_retention.json
```

The state file records workspace-relative artifact paths, important-mark
timestamp, and optional reason. Do not create one marker file per report.

### PR-3: CLI Management

The CLI must expose report retention commands:

```bash
dadaia reports cleanup [--older-than 48h] [--dry-run] [--json]
dadaia reports mark-important <report-or-handoff-path> [--reason <text>]
dadaia reports unmark-important <report-or-handoff-path>
dadaia reports important [--json]
```

`cleanup --dry-run` must show exactly what would be deleted and why.

### PR-4: Panel Integration And Cleanup Trigger

The Reports tab must let the user:

- see whether a report is marked important;
- mark a report as important;
- remove important protection;
- delete a report manually as today;
- understand when a report is eligible for automatic cleanup.

The UI must avoid vague labels. Use direct terms such as `Important`, `Marked
important`, and `Expires in`.

When the panel starts or the Reports tab/API is loaded, the workspace should run
the same cleanup policy for expired non-important reports. The cleanup must be
bounded and quiet: it may remove expired unimportant reports, but it must not
block panel startup on non-critical cleanup errors. Explicit CLI cleanup remains
available for operators and automation.

### PR-5: Safe Deletion Semantics

Cleanup must be safe and deterministic:

- never delete outside `.dadaia/reports/` or `.dadaia/handoff/`;
- resolve paths with traversal guards;
- delete matching handoff and report artifacts together;
- skip malformed handoff JSON unless it is old and has no important artifact;
- support dry-run without mutation;
- emit a concise cleanup summary.

### PR-6: Workspace Doctor Visibility

`dadaia doctor` or an equivalent report-retention doctor check must surface:

- stale report count;
- stale handoff count;
- orphaned handoff count;
- important report count;
- malformed retention state.

Generic doctor must not remove reports as a surprising side effect. Cleanup is
performed only by report-retention cleanup paths: explicit CLI cleanup or the
Reports panel startup/listing cleanup trigger.

### PR-7: No Repository Pollution

Cleanup state and deleted artifacts are workspace runtime concerns. No report
cleanup state may be written inside a repo working tree. No cache, temp, report,
or handoff cleanup artifact may be created under `repos/**`.

## 4. Non-Goals

- Do not archive expired reports into git.
- Do not move expired reports to a trash folder by default.
- Do not keep reports forever based on severity.
- Do not delete product memory, release specs, closures, screenshots, or test
  artifacts in this release.
- Do not introduce a database dependency.
- Do not run cleanup automatically as a daemon in this release.
- Do not create or use release `v0.1.5`.

## 5. Acceptance Criteria

### AC-1: Cleanup CLI Deletes Old Unimportant Reports

Given reports older than 48 hours under `.dadaia/reports/` and matching handoffs
under `.dadaia/handoff/`, `dadaia reports cleanup` deletes them and reports the
deleted count.

### AC-2: Important Reports Survive Cleanup

Given a report marked important in the panel or by
`dadaia reports mark-important <path>`, cleanup skips that report and its
related handoff even when older than 48 hours.

### AC-3: Removing Important Restores Expiration

Given an old important report, removing the important mark in the panel or by
`dadaia reports unmark-important <path>` removes protection and a subsequent
cleanup deletes the report.

### AC-4: Dry Run Is Non-Mutating

`dadaia reports cleanup --dry-run` lists eligible deletions but does not remove
files or mutate retention state.

### AC-5: Panel Shows Retention State

The Reports tab displays important/expiring state and provides accessible
controls to mark or unmark a report as important. The controls must have clear
labels and 44px touch targets.

### AC-6: Path Safety

Cleanup and important-mark commands reject absolute paths, parent traversal, and
paths outside `.dadaia/reports/` or `.dadaia/handoff/`.

### AC-7: Orphan Cleanup

Cleanup detects and removes old non-important orphan handoffs that reference
missing report artifacts, while preserving important entries.

### AC-8: Panel Cleanup Trigger

When the panel starts or the Reports tab/API is loaded, expired non-important
reports older than 48 hours are removed by the same retention policy used by the
CLI. Important reports remain visible.

### AC-9: Validation

Required validation:

```bash
pytest -q -p no:cacheprovider tests/unit/features/reports*
pytest -q -p no:cacheprovider tests/unit/features/panel/test_*reports*
pytest -q -p no:cacheprovider tests/contract -k reports
pytest -q -p no:cacheprovider tests/integration -k reports
```

No validation command may leave cache, coverage, or report artifacts inside any
repo working tree.

## 6. Decisions

- Default TTL is 48 hours.
- User-facing protection is named `Important`.
- Reports become important only when the user explicitly marks them important in
  the panel or via CLI.
- Cleanup runs through explicit CLI and through the Reports panel startup/listing
  path. No background daemon is introduced in this release.

## 7. Hotfix Scope

This release also includes an immediate Reports tab bug fix:

- The Reports tab must open report paths containing `/` from `/api/reports`.
- The browser must not encode path separators into `%2F` for `/reports/<path>`
  or `/api/reports/<path>` routes.
- The fix is limited to report open/delete URL construction and focused tests.
