# Closure: Release — v0.1.4.3

> **Status:** Aprovado
> **Release ID:** v0.1.4.3
> **Owner:** product-engineer
> **Closed:** 2026-06-04

## Summary

Release v0.1.4.3 (report-retention) shipped the full report lifecycle management
subsystem for dadaia-workspace. The workspace can now automatically expire stale
agent reports while preserving any report the operator explicitly marks as
important.

The retention model discovers reports and their paired handoffs, computes effective
timestamps (from `produced_at`, filename, or mtime), and evaluates each artifact
against the 48-hour TTL. A single state file at `.dadaia/states/report_retention.json`
records the important set — no per-report marker files, no database. The CLI exposes
`dadaia reports cleanup`, `mark-important`, `unmark-important`, and `important`
commands with full dry-run and JSON output support.

The panel Reports tab was simultaneously fixed and extended: the Reports API now
discovers HTML artifacts directly (no longer sidecar-only), enriches rows from
canonical handoffs in `.dadaia/handoff/` and legacy adjacent sidecars, deduplicates
to one row per HTML report, exposes retention fields (`important`, `expires_at`,
`is_expired`), and provides mark/unmark important panel actions. The panel
startup/listing path runs the same cleanup policy as the CLI. Manual delete removes
the HTML report and all matching canonical and legacy handoff sidecars together.

The `T-BUG-REPORTS-01` hotfix fixes were folded into this release: the browser
`%2F` encoding regression and the sidecar-location drift introduced by an earlier
commit are both resolved. The full pytest suite passes at 2143 tests, 0 failures.

## Tasks completed

| Task ID | Description | Final commit |
|---------|-------------|--------------|
| T-BUG-REPORTS-01 | Fix Reports tab routing, indexing, and sidecar-location drift | `fc4c762` |
| T-RET-01 | Implement report retention domain service | `315b863` |
| T-RET-02 | Implement safe cleanup execution | `315b863` |
| T-RET-03 | Add reports retention CLI commands | `ebb3cbd` |
| T-RET-04 | Extend Reports panel API and UI | `ebb3cbd` |
| T-RET-05 | Add doctor/status visibility | `ebb3cbd` |
| T-RET-06 | Validate, review, and emit implementation handoffs | `ebb3cbd` |

## Validations

| Description | Command | Evidence |
|-------------|---------|----------|
| Full pytest suite green | `pytest -q -p no:cacheprovider` | `2143 passed, 0 failed` |
| Reports retention unit tests pass | `pytest -q -p no:cacheprovider tests/unit/features/reports_retention` | `2143 passed, 0 failed` (suite-wide run) |
| Panel reports unit tests pass | `pytest -q -p no:cacheprovider tests/unit/features/panel -k reports` | included in 2143 |
| Contract tests pass | `pytest -q -p no:cacheprovider tests/contract -k reports` | included in 2143 |
| Integration tests pass | `pytest -q -p no:cacheprovider tests/integration -k reports` | included in 2143 |
| Cleanup CLI dry-run non-mutating | `dadaia reports cleanup --dry-run` | confirmed non-mutating in T-RET-06 QA review |
| Path traversal rejected | cleanup and mark-important commands | covered by T-RET-02 unit tests |
| Orphan handoff cleanup | cleanup removes orphan handoffs older than TTL | covered by T-RET-02 unit tests |
| No repo pollution after test run | `ls repos/` | no cache or report artifacts inside any repo working tree |

## Drifts

### bug-reports-sidecar-location

**Description:** At the start of the release, `api.py` had been pointed at
`.dadaia/handoff/` for sidecar discovery (commit `6f7e70f`), but 224 of 225
existing sidecars lived adjacent to their reports under `.dadaia/reports/`. This
was a live regression: the Reports tab collapsed from 224 visible reports to 2.
The bug pre-dated this release's scope but was discovered during T-BUG-REPORTS-01
analysis.

**Resolution:** The discovery model was inverted — the API now discovers HTML
artifacts first, then enriches from both canonical `.dadaia/handoff/` and legacy
adjacent `.dadaia/reports/**/*.handoff.json` sidecars. The `T-HANDOFF-04` path
change was effectively reverted as a side effect of the new discovery logic. This
matches the de-facto sidecar layout of the workspace corpus. Implemented in
`T-BUG-REPORTS-01` and finalized in `T-RET-04`.

**Memory updates:** `specs/memory/architecture.md` — updated panel architecture
section to reflect that `GET /api/reports` discovers by HTML artifact (not
sidecar-driven) and enriches from both canonical and legacy sidecar locations;
updated `do_DELETE` entry to note that deletion removes HTML + canonical + legacy
sidecars together.

### retention-state-path-design

**Description:** PLAN.md proposed using workspace-relative normalized paths as
keys in `report_retention.json`. During implementation it was confirmed that
path normalization must also handle the case where the caller passes a handoff
path rather than an HTML path — the service resolves to the referenced report
artifact when possible.

**Resolution:** Implemented as designed in PLAN.md section 3 "Retention State".
No spec change required. Unit tests cover the handoff-path → artifact-path
resolution case.

**Memory updates:** None beyond the architecture section update above.

## Memory updates

- `specs/memory/architecture.md` — updated panel HTTP internals section: `api_reports` discovery model (HTML-first, sidecar-enriched), `api_report_delete` deletion semantics (HTML + canonical + legacy sidecars), retention fields in API envelope, panel startup cleanup trigger. Updated runtime state section to add `.dadaia/states/report_retention.json`.
- `specs/memory/tech-stack.md` — no change: release did not add new dependencies.
- `specs/memory/product/index.md` — no change: no new feature added to the catalog; report-retention is an operator-level capability, not a product feature visible in the catalog.

## Backlog returns

- `specs/backlog/candidates.md` ← `BUG-PANEL-REPORTS-01` entry was addressed and resolved in this release (T-BUG-REPORTS-01 + T-RET-04). The candidate entry can be marked resolved or removed from the candidates list.

## Archive decision

**MOVE** — release directory will be moved to `specs/_archive/releases/v0.1.4.3/` via
`git mv`. ACTIVE.md will be updated to point to v0.1.4.4 or `release: none`.
