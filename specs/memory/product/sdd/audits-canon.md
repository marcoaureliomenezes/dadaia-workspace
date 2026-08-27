---
slug: audits-canon
title: audits-canon
category: product
tldr: Audits are committed spec artifacts — three pillars over a sha window, findings as JSONL records, dispositioned by exactly one remediation release.
summary: >-
  An audit is a committed artifact under `specs/audits/<YYYYMMDD>-<slug>/`, holding `AUDIT.md`
  for scope, window, method and score and `FINDINGS.jsonl` for one record per finding with an
  immutable claim and a mutable governance triple. Three pillars always run together — bug
  history, spec compliance, and memory/constitution drift — over the window running from the
  newest `audited` milestone to HEAD, computed from the release streams alone and never from
  `_ideas/`. Pillar one measures eight forensic metrics and is the single writer of every
  bug record's derived provenance cache, in the same atomic rewrite that stamps `audited`.
  Every `evidence` value is a reproducible command plus a redacted one-line result, so a
  finding read months later can be re-run; a temp-lane path is a pointer, never the citation.
  The cadence is suggested every five releases and never mandatory, no CLI verb or hook
  exists, and one audit binds exactly one remediation release that gives every finding a
  terminal disposition before the folder may archive.
tags:
- sdd
- audits
- findings
- governance
- evidence
last_updated: '2026-08-27'
release_origin: 0.5.0
---

## Purpose

An audit is the workspace's only full-tree inspection lane, and it exists to make the
bug-recurrence loop **measurable** rather than argued. Every other quality boundary is
diff-scoped: the PR security verdict, the six-axis code review, the segment QA close. The
audit is where a chain of fixes is read as a chain.

It is a **committed spec artifact**, not a report. `specs/audits/<YYYYMMDD>-<slug>/` holds:

| Member | Content |
|---|---|
| `AUDIT.md` | scope; the window `[from-sha, to-sha]` and the releases inside it; method per pillar; the eight forensic metrics with `baseline → measured`; the score; the operator-facing summary |
| `FINDINGS.jsonl` | one record per finding, appended once |

`specs/audits/AGENTS.md` carries the scoped law and the index of audits; there is no
`README.md`. The HTML report and handoff remain the operator-facing emission, but they are
**derived from** the committed folder and never a substitute for it — a convention with no
committed data behind it is how drift starts.

`specs/audits/**` is an ADDITIVE path, writable in any mode; `specs/audits/_archive/` is
FROZEN, so the archive move is a `git mv` outside the file-tool envelope. `project-auditor`'s
write allowlist is exactly `specs/audits/**` plus `specs/bugs/BUGS.jsonl` for governance
fields, written through the bug record store's one seam so the write is redacted and atomic
([[sdd-bug-backlog-governance]]). The allowlist is projection-time documentation, not a
write-time control; what is mechanically true is the FROZEN archive.

**There is no CLI verb and no hook.** The auditor writes the folder with its file tools.
Skills instruct the procedure; audits measure conformance from git and JSONL history; hooks
and the CLI validate only at the publication boundary.

## Evidence Model

`finding-record-v1` (`additionalProperties: false`) splits per property, the same shape the
bug record uses:

| Category | Fields |
|---|---|
| Immutable | `id` (`<audit-slug>-F<nnn>`), `pillar` (`bugs \| specs \| memory`), `severity`, `refs` (file:line, bug ids, commit shas, release ids), `claim` (one sentence), `evidence` |
| Mutable governance | `disposition` (`open \| fixed \| superseded \| deferred \| rejected`), `release`, `reason` |

A remediation release rewrites the governance triple **in place**, leaving every other byte of
the line identical.

**`evidence` is the reproducible command plus a redacted one-line result** — for example
`git show <sha> --stat -- <module> → 2 files changed, second render path added`. A
`.dadaia/tmp/**` capture may accompany it as a convenience pointer and never replace it: that
lane is garbage-collected at three days, so a path-only citation decays into an unverifiable
claim. The one-line result is redacted **by hand**, because the auditor writes with file tools
and no seam can redact for it; pillar-3 tool runs emit runner-absolute paths routinely, so a
transcript is never pasted, only its conclusion. Before the audit is trusted, the whole folder
is run through the same detector a push uses and the zero-hit result is recorded.

## Lifecycle

**The window.** An audit runs over `[from-sha, HEAD]`, where `from-sha` is the newest `audited`
milestone found by scanning the live release's `RELEASE.jsonl`, `specs/releases/_archive/**`
and `releases_histo.jsonl`. `_ideas/` is not scanned — a pre-approval release is SPEC-only and
carries no stream, so looking there could only ever return nothing. The audit appends its own
`audited` milestone at the end, so the chain never gaps. The same window definition is cited,
not restated, by the bug-fix lineage duty.

**All three pillars run together, always** — a run reporting one of them is incomplete, not
lenient.

- **Pillar 1 — bug history.** Input is every bug record whose registration or resolution sha
  falls in the window. It measures recurrence (same `surface`/`component` re-registered after a
  resolution), fix-induced bugs (a resolution diff whose touched files appear in a later bug's
  refs, with a `caused_by: none` contradicted by the diff as its own finding), resolutions with
  no cause or no regression seam, net-positive diffs that never routed to `software-architect`,
  commit-shape conformance read from `git log`, an implausibly short registration→resolution
  interval (the no-red-loop signature), a hunk that changes an **immutable core field** of an
  existing record (HIGH — the detector that makes seam-level immutability auditable, since
  nothing prevents a file-tool rewrite), and a stored provenance sha that disagrees with the
  derivation. It consumes only `resolution_granularity == "exact"` shas as diffable lineage and
  records the rest as coarse. It carries **eight forensic metrics** — per-bug diff
  attributability, evidence-triple coverage, fix-shape ratio, same-surface re-bug rate at 3 d
  and 14 d, hand-kept-list touch count, test-layer bug share, scanner-vs-prose recurrence, and
  sweep closures mis-filed as `resolved` — each reported with its baseline and, where one
  exists, its target.

  Pillar 1 is the **single writer of the derived cache**: on each record it reviews it writes
  `audited` plus `registration_commit`, `registration_granularity`, `resolved_commit` and
  `resolution_granularity` in **one** atomic in-place rewrite through the bug record store.

- **Pillar 2 — spec compliance.** `dadaia specs doctor --json` across every release in the
  window; conformance to the v6 canon; `RELEASE.jsonl` milestone completeness (`defined` /
  `implemented` / `shipped`, each with a sha); SPEC provenance and `**Consumes:**`;
  purge-on-pick executed in the SPEC commit; and commit-shape discipline via `git log`.

- **Pillar 3 — memory and constitution drift.** Every Part-1 principle of the memory trio is
  **run through the check its own `Measured by:` line names** and the result recorded; product
  atoms are compared against the code they describe; constitution violations are reported; and
  a **Part-1 principle changed without an accepted ADR** in the same commit is a HIGH finding.
  Its stated limit is honest: pillar 3 cannot detect an *agent-written* `accepted`, because
  commit identity is shared — attribution is discipline, the pairing is the detector.

**Cadence and disposition.** An audit is **suggested every five releases and never mandatory**;
the operator triggers it, and `project-manager` surfaces the suggestion once five `shipped`
milestones have accrued since the last `audited`. One audit generates **exactly one**
remediation release, and that release gives **every** finding a terminal disposition — `fixed`,
`superseded` by a broader picked item, or `deferred`/`rejected` with a reason routed to intake.
Triage cannot silently drop a finding. The folder moves to `specs/audits/_archive/` only when
no record is `open`; the original claim and evidence are immutable, a disposition is appended
to the record's governance fields and never woven into the finding text.

`specs doctor` enforces both ends by **folding `FINDINGS.jsonl`**, never by regexing prose: an
`open` record inside an archived audit is SPEC-DOC-036, an ERROR; a live audit whose records
are all terminal and each name a disposing release is SPEC-DOC-038, an archive-due WARNING. An
archived audit predating the schema carries no `FINDINGS.jsonl` and is skipped by the fold with
a named WARN, never an error. Directory naming follows the collision-safe shape whose single
home is `core/workspace_layout.py`.

## Runtime State

- `specs/audits/<YYYYMMDD>-<slug>/AUDIT.md` — scope, window, method, metrics, score, summary
- `specs/audits/<YYYYMMDD>-<slug>/FINDINGS.jsonl` — one record per finding
- `specs/audits/AGENTS.md` — the scoped law and the audit index
- `specs/audits/_archive/<audit>/` — FROZEN; reached only by `git mv`, once fully dispositioned
- `specs/releases/<id>/RELEASE.jsonl` — the `audited` milestone that anchors the next window
- `specs/bugs/BUGS.jsonl` — the `audited` stamp and the four derived provenance fields
- `.dadaia/reports/<context>/project-auditor/<UTC>-<slug>/` — the derived operator emission

## Dependencies

[[sdd-bug-backlog-governance]], [[specs-doctor]], [[sdd-gate-v3]], [[agent-comms]].
