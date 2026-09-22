---
slug: audits-canon
title: audits-canon
tldr: Audits are committed spec artifacts — three pillars over a sha window, JSONL findings moved by audit.py disposition, archived by audit.py close.
summary: An audit is a committed folder holding AUDIT.md and FINDINGS.jsonl; three pillars always run together over the window since the newest archived audit; a finding's disposition and the archive are two CLI verbs, each all-or-nothing and each leaving one governance event.
tags: [sdd, audits, findings, governance, evidence]
sources:
  - dadaia_workspace/features/specs/doctor_closure_audit.py
  - dadaia_workspace/public/skills/dd-audit-project/**
  - dadaia_workspace/public/schemas/audits/**
---

## Shape

- The audit is the only full-tree inspection lane; every other quality boundary is diff-scoped.
- It is a committed spec artifact, not a report: `AUDIT.md` carries scope, the window `[from-sha, to-sha]`, method per pillar, eight forensic metrics as `baseline → measured`, the score and the summary.
- `FINDINGS.jsonl` carries one record per finding, appended once with file tools (immutable core, like an ADR); `specs/audits/AGENTS.md` holds the scoped law and the index, and the HTML report is derived, never a substitute.
- `specs/audits/**` is ADDITIVE and writable bound or not; `code-reviewer` (the audit lens) writes the folder, and `BUGS.jsonl` only through the bug verbs ([[sdd-bug-backlog-governance]]).
- `finding-record-v1` splits per property into immutable — `id`, `pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim`, `evidence` — and mutable `disposition`, `release`, `reason`; `disposition` is `open resolved superseded deferred rejected`, the terminal four being `core.models.histo.FINDINGS_DISPOSITIONS`; `dadaia doctor`'s `ledgers` section validates every committed line (`LEDGER-FINDINGS-SCHEMA`, [[workspace-doctor]]).
- `evidence` is a reproducible command plus a hand-redacted one-line result, never replaced by a capture.
- Before the audit is trusted the whole folder runs through the same detector a push uses.

## Verbs

- `audit.py disposition <dir> <finding-id> --disposition resolved|superseded|deferred|rejected [--release <id>] [--reason <text>]` rewrites one finding's governance triple in place through `FindingRecord.apply_governance_update` inside `JsonlRecordStore.update`, every other byte identical; `resolved`/`superseded` need `--release`, `deferred`/`rejected` need `--reason` (`core.models.histo.REQUIRED_EVIDENCE`).
- `audit.py close <dir> --sha <window-end>` refuses while any finding is `open` (naming the id), appends the one `audits_histo.jsonl` `histo-record-v1` line — `disposition: resolved`, `release` = the one remediation release, `summary` = the per-disposition counts, `entry = {sha, pillars: {bugs, specs, memory}, dispositions}` — and deletes the directory; all-or-nothing, the histo append last.
- Both live in `features/specs/audit.py`; `<dir>` is confined to `specs/audits/` (an escape of any shape names the live audits), every refusal is an `AuditError` carrying exactly one `fix:` line, and each verb leaves one governance event ([[sdd-bug-backlog-governance]]).
- `SPEC-DOC-036` (an `open` finding in an archived audit) and `SPEC-DOC-038` (a live audit whose findings are all terminal) police both directions, their `fix:` lines naming the two verbs ([[workspace-doctor]]).

## Lifecycle

- The window is `[from-sha, HEAD]`, `from-sha` being the newest record in `audits/_archive/audits_histo.jsonl` (the whole history when it is empty); an audit is not a release milestone — `_RELEASE.json` carries no `audited` field — and `_ideas/` is never scanned.
- All three pillars run together — a run reporting one of them is incomplete.
- Pillar 1, bug history, covers every record whose registration or resolution falls in the window (git history of `BUGS.jsonl`, no stored provenance), measuring recurrence, fix-induced bugs, resolutions with no cause or regression seam, unrouted net-positive diffs, commit-shape conformance and a hunk changing an immutable core field (HIGH); registrations per session read the governance events; the `audited` field is its one stamp, written through `bugs.py update --set`.
- Pillar 2, spec compliance, runs `dadaia doctor --json` over the tree (`specs` and `ledgers` sections) and checks canon conformance, `_RELEASE.json` milestone completeness, SPEC provenance and `**Consumes:**`, and commit shapes via `git log` ([[workspace-doctor]]).
- Pillar 3, memory and constitution drift, runs every Part-1 principle through the check its own `Measured by:` line names, compares product atoms against the code they describe, and makes a Part-1 principle changed without an accepted ADR a HIGH finding.
- An audit is suggested every five releases and never mandatory — five `releases_histo.jsonl` records since the newest archived audit.
- One audit generates exactly one remediation release giving every finding a terminal disposition — `resolved`, `superseded` by a broader picked item, or `deferred`/`rejected` routed to intake — and closes at that release's disposition sweep.

## Dependencies

[[sdd-bug-backlog-governance]], [[workspace-doctor]], [[sdd-gate-v3]], [[agent-comms]].
