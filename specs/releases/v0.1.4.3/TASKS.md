# TASKS: v0.1.4.3 - report-retention

**Status:** Aprovado
**Release ID:** v0.1.4.3
**Owner:** product-engineer
**Created:** 2026-06-04

---

## Execution Order

Maximum one `[-]` at a time unless this file is amended with explicit disjoint
write sets.

```text
T-RET-01 -> T-RET-02 -> T-RET-03 -> T-RET-04 -> T-RET-05 -> T-RET-06
```

---

## Tasks

### T-BUG-REPORTS-01 - Fix Reports tab report routing and indexing

- **Status:** [x]
- **Owner:** software-engineer-python + frontend-engineer
- **Reviewers before approval:** qa-engineer, code-reviewer
- **Target files:** `dadaia_workspace/features/panel/views/api.py`, `dadaia_workspace/features/panel/views/assets/js/reports.js`, focused panel reports tests

Fix the Reports tab click/delete URL construction and report listing contract.
The current browser bug encodes `/` as `%2F`, causing `GET /reports/<path>` from
the real panel button flow to return HTTP 404 even when the direct
slash-preserving URL returns HTTP 200.

Also fold `BUG-PANEL-REPORTS-01` into this release: `/api/reports` must discover
real HTML reports under `.dadaia/reports/**`, enrich them from canonical
`.dadaia/handoff/**` and legacy adjacent `.dadaia/reports/**/*.handoff.json`
sidecars, skip self-referential/source-file handoffs, deduplicate to one row per
HTML report, and delete matching canonical plus legacy handoffs when the user
manually deletes a report.

### T-RET-01 - Implement report retention domain service

- **Status:** [x]
- **Owner:** software-engineer-python
- **Reviewers before approval:** qa-engineer, code-reviewer, security-reviewer
- **Target files:** `dadaia_workspace/features/reports_retention/**` or nearest existing reports feature, `tests/unit/features/reports_retention/**`

Create the retention model that discovers reports and handoffs, computes
effective timestamps, loads/saves `.dadaia/states/report_retention.json`, marks
reports marked important/unimportant, and returns cleanup candidates. Include
unit tests for 48-hour TTL, path normalization, important state, and malformed
state handling.

### T-RET-02 - Implement safe cleanup execution

- **Status:** [-]
- **Owner:** software-engineer-python + security-reviewer
- **Reviewers before approval:** qa-engineer, code-reviewer, security-reviewer
- **Target files:** retention service, `tests/unit/features/reports_retention/**`, `tests/contract/**`

Delete old non-important report nodes safely. Cover report-plus-handoff deletion,
legacy sidecars, orphan handoffs, dry-run non-mutation, and traversal rejection.
Deletion must never escape `.dadaia/reports/` or `.dadaia/handoff/`.

### T-RET-03 - Add reports retention CLI commands

- **Status:** [ ]
- **Owner:** software-engineer-python
- **Reviewers before approval:** qa-engineer, code-reviewer, security-reviewer
- **Target files:** `dadaia_workspace/cli/commands/reports.py`, CLI tests

Add:

```bash
dadaia reports cleanup [--older-than 48h] [--dry-run] [--json]
dadaia reports mark-important <report-or-handoff-path> [--reason <text>]
dadaia reports unmark-important <report-or-handoff-path>
dadaia reports important [--json]
```

Return clear operator messages and JSON output suitable for panel reuse.

### T-RET-04 - Extend Reports panel API and UI

- **Status:** [ ]
- **Owner:** frontend-engineer + software-engineer-python
- **Reviewers before approval:** qa-engineer, code-reviewer, security-reviewer, design-specialist
- **Target files:** `dadaia_workspace/features/panel/views/api.py`, panel route/container wiring, `dadaia_workspace/features/panel/views/assets/js/reports.js`, focused panel tests

Show important/expiring state in the Reports tab and add accessible
Important/Unmark important actions. Extend `/api/reports` with retention fields.
Add panel mutations to mark and unmark a report as important. Keep manual delete
behavior intact. The Reports API/panel startup path must run cleanup for expired
non-important reports older than 48 hours.

### T-RET-05 - Add doctor/status visibility

- **Status:** [ ]
- **Owner:** software-engineer-python + qa-engineer
- **Reviewers before approval:** code-reviewer, security-reviewer
- **Target files:** doctor or reports status surface, tests

Expose stale report count, stale handoff count, orphaned handoff count,
important report count, and malformed retention state. Generic doctor must not
delete reports as a surprising side effect.

### T-RET-06 - Validate, review, and emit implementation handoffs

- **Status:** [ ]
- **Owner:** qa-engineer + code-reviewer + security-reviewer
- **Reviewers before approval:** product-engineer
- **Target files:** `.dadaia/reports/**`, `.dadaia/handoff/**`

Run the required validation commands, review deletion safety, review panel UX,
and emit QA/code/security handoffs. The release is not done until all required
reviewers approve the same implementation artifact.

---

## Decisions Before Approval

- Default TTL: 48 hours.
- User-facing protection label: Important.
- Cleanup trigger: explicit CLI plus Reports panel startup/listing path.
- No background cleanup daemon in this release.
