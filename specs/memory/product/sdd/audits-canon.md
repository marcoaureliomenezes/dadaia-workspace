---
slug: audits-canon
title: audits-canon
category: product
tldr: Audits are committed spec artifacts — three pillars over a sha window, findings as JSONL records, dispositioned by exactly one remediation release.
summary: An audit is a committed folder holding AUDIT.md and FINDINGS.jsonl; three pillars always run together over the window since the last audited milestone.
tags: [sdd, audits, findings, governance, evidence]
---

## Shape

- The audit is the only full-tree inspection lane; every other quality boundary is diff-scoped.
- It is a committed spec artifact, not a report: `AUDIT.md` carries scope, the window `[from-sha, to-sha]`, method per pillar, eight forensic metrics as `baseline → measured`, the score and the summary.
- `FINDINGS.jsonl` carries one record per finding, appended once; `specs/audits/AGENTS.md` holds the scoped law and the index, and the HTML report is derived, never a substitute.
- `specs/audits/**` is ADDITIVE and writable in any mode while `_archive/` is FROZEN, so the archive move is a `git mv`.
- `project-auditor` writes `specs/audits/**` plus `BUGS.jsonl` through the record store's one seam ([[sdd-bug-backlog-governance]]); no CLI verb and no hook exists.
- `finding-record-v1` splits per property into immutable — `id`, `pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim`, `evidence` — and mutable `disposition`, `release`, `reason`.
- A remediation release rewrites the governance triple in place, leaving every other byte identical.
- `evidence` is a reproducible command plus a hand-redacted one-line result, never replaced by a capture.
- Before the audit is trusted the whole folder runs through the same detector a push uses.

## Lifecycle

- The window is `[from-sha, HEAD]`, `from-sha` being the newest `audited` milestone found across the live `RELEASE.json`, `specs/releases/_archive/**` and `releases_histo.jsonl`; `_ideas/` is not scanned.
- The audit sets its own `audited` milestone at the end, so the chain never gaps, and all three pillars run together — a run reporting one of them is incomplete.
- Pillar 1, bug history, covers every record whose registration or resolution sha falls in the window, measuring recurrence, fix-induced bugs, resolutions with no cause or regression seam, unrouted net-positive diffs, commit-shape conformance, a hunk changing an immutable core field (HIGH), and a stored provenance sha disagreeing with derivation.
- Pillar 1 is the single writer of the derived cache, writing `audited` and the four provenance fields in one atomic rewrite.
- Pillar 2, spec compliance, runs `dadaia specs doctor --json` over every release in the window and checks v6-canon conformance, milestone completeness, SPEC provenance and `**Consumes:**`, and commit shapes via `git log`.
- Pillar 3, memory and constitution drift, runs every Part-1 principle through the check its own `Measured by:` line names, compares product atoms against the code they describe, and makes a Part-1 principle changed without an accepted ADR a HIGH finding.
- An audit is suggested every five releases and never mandatory, once five `shipped` milestones accrued since the last `audited`.
- One audit generates exactly one remediation release giving every finding a terminal disposition — `fixed`, `superseded` by a broader picked item, or `deferred`/`rejected` routed to intake.
- The folder moves to `_archive/` only when no record is `open`, claim and evidence staying immutable ([[specs-doctor]]).

## Dependencies

[[sdd-bug-backlog-governance]], [[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
