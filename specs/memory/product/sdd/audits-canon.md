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

## Purpose

The audit is the workspace's only full-tree inspection lane — every other quality boundary
(the PR security verdict, the six-axis code review, the segment QA close) is diff-scoped.
It is where a chain of fixes is read as a chain.

It is a **committed spec artifact**, not a report:

| Member | Content |
|---|---|
| `AUDIT.md` | scope; the window `[from-sha, to-sha]` and the releases inside it; method per pillar; the eight forensic metrics with `baseline → measured`; the score; the operator-facing summary |
| `FINDINGS.jsonl` | one record per finding, appended once |

`specs/audits/AGENTS.md` carries the scoped law and the audit index. The HTML report and
handoff are derived from the committed folder, never a substitute for it.

`specs/audits/**` is ADDITIVE and writable in any mode; `specs/audits/_archive/` is FROZEN,
so the archive move is a `git mv` outside the file-tool envelope. `project-auditor`'s write
allowlist is `specs/audits/**` plus `specs/bugs/BUGS.jsonl` for governance fields, written
through the bug record store's one seam ([[sdd-bug-backlog-governance]]). There is **no CLI
verb and no hook**: the auditor writes the folder with its file tools.

## Evidence model

`finding-record-v1` (`additionalProperties: false`) splits per property:

| Category | Fields |
|---|---|
| Immutable | `id` (`<audit-slug>-F<nnn>`), `pillar` (`bugs \| specs \| memory`), `severity`, `refs` (file:line, bug ids, commit shas, release ids), `claim`, `evidence` |
| Mutable governance | `disposition` (`open \| fixed \| superseded \| deferred \| rejected`), `release`, `reason` |

A remediation release rewrites the governance triple in place, leaving every other byte of
the line identical.

`evidence` is a reproducible command plus a redacted one-line result — for example
`git show <sha> --stat -- <module> → 2 files changed, second render path added`. A
`.dadaia/tmp/**` capture may accompany it as a pointer and never replace it, because that
lane is garbage-collected at three days. The one-line result is redacted by hand, since the
auditor writes with file tools and no seam redacts for it. Before the audit is trusted the
whole folder is run through the same detector a push uses and the zero-hit result recorded.

## Lifecycle

**The window** is `[from-sha, HEAD]`, where `from-sha` is the newest `audited` milestone
found by scanning the live release's `RELEASE.jsonl`, `specs/releases/_archive/**` and
`releases_histo.jsonl`. `_ideas/` is not scanned. The audit appends its own `audited`
milestone at the end, so the chain never gaps.

**All three pillars run together, always** — a run reporting one of them is incomplete.

- **Pillar 1 — bug history.** Input is every bug record whose registration or resolution
  sha falls in the window. It measures recurrence (same `surface`/`component` re-registered
  after a resolution), fix-induced bugs, resolutions with no cause or no regression seam,
  net-positive diffs that never routed to `software-architect`, commit-shape conformance
  read from `git log`, an implausibly short registration→resolution interval, a hunk that
  changes an immutable core field of an existing record (HIGH), and a stored provenance sha
  disagreeing with the derivation. Only `resolution_granularity == "exact"` shas are
  diffable lineage; the rest are recorded as coarse. Its eight forensic metrics are per-bug
  diff attributability, evidence-triple coverage, fix-shape ratio, same-surface re-bug rate
  at 3 d and 14 d, hand-kept-list touch count, test-layer bug share, scanner-vs-prose
  recurrence, and sweep closures mis-filed as `resolved`. Pillar 1 is the **single writer
  of the derived cache**: on each record it reviews it writes `audited`,
  `registration_commit`, `registration_granularity`, `resolved_commit` and
  `resolution_granularity` in one atomic in-place rewrite.
- **Pillar 2 — spec compliance.** `dadaia specs doctor --json` across every release in the
  window; conformance to the v6 canon; `RELEASE.jsonl` milestone completeness (`defined`,
  `implemented`, `shipped`, each with a sha); SPEC provenance and `**Consumes:**`;
  purge-on-pick executed in the SPEC commit; commit-shape discipline via `git log`.
- **Pillar 3 — memory and constitution drift.** Every Part-1 principle of the memory trio
  is run through the check its own `Measured by:` line names and the result recorded;
  product atoms are compared against the code they describe; constitution violations are
  reported; a Part-1 principle changed without an accepted ADR in the same commit is a HIGH
  finding. Its stated limit: pillar 3 cannot detect an agent-written `accepted`, because
  commit identity is shared.

**Cadence and disposition.** An audit is suggested every five releases and never mandatory;
`project-manager` surfaces the suggestion once five `shipped` milestones have accrued since
the last `audited`. One audit generates exactly one remediation release, and that release
gives every finding a terminal disposition — `fixed`, `superseded` by a broader picked
item, or `deferred`/`rejected` with a reason routed to intake. The folder moves to
`specs/audits/_archive/` only when no record is `open`; the claim and evidence stay
immutable and the disposition is written to the governance fields, never woven into the
finding text. `specs doctor` enforces both ends by folding `FINDINGS.jsonl`
([[specs-doctor]]).

## Runtime state

- `specs/audits/<YYYYMMDD>-<slug>/{AUDIT.md,FINDINGS.jsonl}`; `specs/audits/AGENTS.md`
- `specs/audits/_archive/<audit>/` — FROZEN, reached only by `git mv`
- `specs/releases/<id>/RELEASE.jsonl` — the `audited` milestone anchoring the next window
- `specs/bugs/BUGS.jsonl` — the `audited` stamp and the four derived provenance fields
- `.dadaia/reports/<context>/project-auditor/<UTC>-<slug>/` — the derived emission

## Dependencies

[[sdd-bug-backlog-governance]], [[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
