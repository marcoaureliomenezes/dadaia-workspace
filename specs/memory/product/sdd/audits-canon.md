---
slug: audits-canon
title: audits-canon
category: product
tldr: Audits are committed spec artifacts — three pillars over a sha window, findings as JSONL records, dispositioned by exactly one remediation release.
summary: An audit is a committed folder under `specs/audits/<YYYYMMDD>-<slug>/` holding `AUDIT.md` and `FINDINGS.jsonl`; three pillars always run together over the window since the last `audited` milestone.
tags:
- sdd
- audits
- findings
- governance
- evidence
---

## Shape

The audit is the workspace's only full-tree inspection lane; every other quality boundary is
diff-scoped. It is a committed spec artifact, not a report: `AUDIT.md` carries scope, the window
`[from-sha, to-sha]` and the releases inside it, method per pillar, the eight forensic metrics as
`baseline → measured`, the score and the operator-facing summary; `FINDINGS.jsonl` carries one
record per finding, appended once. `specs/audits/AGENTS.md` holds the scoped law and the audit
index; the HTML report and handoff are derived, never a substitute.

`specs/audits/**` is ADDITIVE and writable in any mode; `_archive/` is FROZEN, so the archive move
is a `git mv`. `project-auditor`'s write allowlist is `specs/audits/**` plus `specs/bugs/BUGS.jsonl`
for governance fields through the record store's one seam ([[sdd-bug-backlog-governance]]). There is
no CLI verb and no hook: the auditor writes the folder with its file tools.

`finding-record-v1` (`additionalProperties: false`) splits per property into immutable — `id`,
`pillar` (`bugs | specs | memory`), `severity`, `refs`, `claim`, `evidence` — and mutable governance
— `disposition` (`open | fixed | superseded | deferred | rejected`), `release`, `reason`. A
remediation release rewrites the governance triple in place, leaving every other byte identical.
`evidence` is a reproducible command plus a hand-redacted one-line result; a `.dadaia/tmp/**`
capture may accompany it as a pointer and never replace it. Before the audit is trusted the whole
folder is run through the same detector a push uses, with the zero-hit result recorded.

## Lifecycle

**The window** is `[from-sha, HEAD]`, `from-sha` being the newest `audited` milestone found by
scanning the live release's `RELEASE.json`, `specs/releases/_archive/**` and
`releases_histo.jsonl`; `_ideas/` is not scanned. The audit sets its own `audited` milestone at the
end, so the chain never gaps. **All three pillars run together, always** — a run reporting one of
them is incomplete.

- **Pillar 1 — bug history**, over every bug record whose registration or resolution sha falls in
  the window, measuring recurrence, fix-induced bugs, resolutions with no cause or no regression
  seam, net-positive diffs that never routed to `software-architect`, commit-shape conformance from
  `git log`, implausibly short registration→resolution intervals, a hunk changing an immutable core
  field (HIGH), and a stored provenance sha disagreeing with the derivation; only
  `resolution_granularity == "exact"` shas are diffable lineage. Pillar 1 is the **single writer of
  the derived cache**, writing `audited` and the four provenance fields in one atomic rewrite.
- **Pillar 2 — spec compliance**: `dadaia specs doctor --json` across every release in the window;
  v6-canon conformance; `RELEASE.json` milestone completeness, each with a sha; SPEC provenance and
  `**Consumes:**`; purge-on-pick executed in the SPEC commit; commit-shape discipline via `git log`.
- **Pillar 3 — memory and constitution drift**: every Part-1 principle of the memory trio is run
  through the check its own `Measured by:` line names and the result recorded; product atoms are
  compared against the code they describe; constitution violations are reported; a Part-1 principle
  changed without an accepted ADR in the same commit is a HIGH finding. Stated limit: pillar 3
  cannot detect an agent-written `accepted`, because commit identity is shared.

**Cadence and disposition.** An audit is suggested every five releases and never mandatory,
`project-manager` surfacing the suggestion once five `shipped` milestones have accrued since the
last `audited`. One audit generates exactly one remediation release, giving every finding a terminal
disposition — `fixed`, `superseded` by a broader picked item, or `deferred`/`rejected` with a reason
routed to intake. The folder moves to `_archive/` only when no record is `open`; claim and evidence
stay immutable and the disposition is written to the governance fields, never woven into the finding
text. `specs doctor` enforces both ends by folding `FINDINGS.jsonl` ([[specs-doctor]]).

## Dependencies

[[sdd-bug-backlog-governance]], [[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
