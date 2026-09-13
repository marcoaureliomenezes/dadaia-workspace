---
slug: audits-canon
title: audits-canon
tldr: Audits are committed spec artifacts — three pillars over a sha window read from audits_histo.jsonl, JSONL findings, one remediation release dispositions them.
summary: An audit is a committed folder holding AUDIT.md and FINDINGS.jsonl; three pillars always run together over the window since the newest archived audit, and the archive is one histo-record-v1 line.
tags: [sdd, audits, findings, governance, evidence]
---

## Shape

- The audit is the only full-tree inspection lane; every other quality boundary is diff-scoped.
- It is a committed spec artifact, not a report: `AUDIT.md` carries scope, the window `[from-sha, to-sha]`, method per pillar, eight forensic metrics as `baseline → measured`, the score and the summary.
- `FINDINGS.jsonl` carries one record per finding, appended once; `specs/audits/AGENTS.md` holds the scoped law and the index, and the HTML report is derived, never a substitute.
- `specs/audits/**` is ADDITIVE and writable bound or not; once no finding is `open` the summary lands in `audits/_archive/audits_histo.jsonl` as one `histo-record-v1` `{id, ts, disposition, release, reason, summary, entry}` — `disposition` one of `resolved superseded deferred rejected`, `summary` carrying the window-end sha and the per-pillar counts — and the audit directory is deleted ([[sdd-bug-backlog-governance]]).
- `project-auditor` writes `specs/audits/**` plus `BUGS.jsonl` through the record store's one seam; no CLI verb and no hook exists.
- `finding-record-v1` splits per property into immutable — `id`, `pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim`, `evidence` — and mutable `disposition`, `release`, `reason`; `dadaia doctor`'s `ledgers` section validates every committed line (`LEDGER-FINDINGS-SCHEMA`, [[workspace-doctor]]).
- A remediation release rewrites the governance triple in place, leaving every other byte identical.
- `evidence` is a reproducible command plus a hand-redacted one-line result, never replaced by a capture.
- Before the audit is trusted the whole folder runs through the same detector a push uses.

## Lifecycle

- The window is `[from-sha, HEAD]`, `from-sha` being the newest record in `audits/_archive/audits_histo.jsonl` (the whole history when it is empty); an audit is not a release milestone — `_RELEASE.json` carries no `audited` field — and `_ideas/` is never scanned.
- All three pillars run together — a run reporting one of them is incomplete.
- Pillar 1, bug history, covers every record whose registration or resolution sha falls in the window, measuring recurrence, fix-induced bugs, resolutions with no cause or regression seam, unrouted net-positive diffs, commit-shape conformance, a hunk changing an immutable core field (HIGH), and a stored provenance sha disagreeing with derivation.
- Pillar 1 is the single writer of the bug record's derived cache — its `audited` field and the four provenance fields — one atomic rewrite per reviewed record through `dadaia bugs update --set`.
- Pillar 2, spec compliance, runs `dadaia doctor --json` over the tree (`specs` and `ledgers` sections) and checks canon conformance, `_RELEASE.json` milestone completeness, SPEC provenance and `**Consumes:**`, and commit shapes via `git log` ([[workspace-doctor]]).
- Pillar 3, memory and constitution drift, runs every Part-1 principle through the check its own `Measured by:` line names, compares product atoms against the code they describe, and makes a Part-1 principle changed without an accepted ADR a HIGH finding.
- An audit is suggested every five releases and never mandatory — five `releases_histo.jsonl` records since the newest archived audit.
- One audit generates exactly one remediation release giving every finding a terminal disposition — `fixed`, `superseded` by a broader picked item, or `deferred`/`rejected` routed to intake.
- The folder archives only when no record is `open`, claim and evidence staying immutable; `SPEC-DOC-036` (an `open` finding in an archived audit) and `SPEC-DOC-038` (a live audit whose findings are all terminal) police both directions ([[workspace-doctor]]).

## Dependencies

[[sdd-bug-backlog-governance]], [[workspace-doctor]], [[sdd-gate-v3]], [[agent-comms]].
