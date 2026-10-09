# Concepts

Seven terms, one section each. Their canonical meanings live in
[`CONTEXT.md`](../CONTEXT.md); workspace law lives in
`dadaia_workspace/public/data/AGENTS.md`, and the walkthrough is
[getting started](getting-started.md).

## Context

A *context* is one canonical `specs/` tree owned by one main repository: the unit for
memory, backlog, bugs, releases, reports and handoffs. Associated repositories own
production source only. The registry holds each context ALIVE or DEAD, and a repository
slug belongs to one context.

Resolution proceeds from caller-supplied context, to `DADAIA_CONTEXT`, to the session
record, to the repository containing the current directory. The session's bind names the
context and all its repository slugs; an unbound session owns nothing. Binding also
triggers memory injection.

## Release and candidate

Exactly one *release* is live under `specs/releases/<M.m.p>/`. It has open scope and grows
through closed-scope *candidates*. Each `rc-<N>/` holds `SPEC.md`, `PLAN.md` and
`tasks/<job>.md`; the highest numbered candidate is live. `_RELEASE.json` is the release's
one mutable state document: `phase`, the three milestones and an append-only `log` whose
new entries are `milestone`, `note`, `summary` or closure `memory`.

Every SPEC begins with one `**Origin:**` line: `operator-demand`, or the canonical
backlog/bugs/findings clauses. `release.py check` traces those ids through the closure
summary. Release ids are bare SemVer and move only at an operator-approved deploy.

## The flow

Every demand takes one of two arms. Arm A moves through backlog or operator demand,
as-is review, grill, approved SPEC/PLAN/job files, test-first tasks, one review per job,
reconciliation, the work-to-integration merge and the promote-or-continue choice. Jobs
and tasks are the only implementation levels.

Arm B proposes and registers a confirmed bug, establishes lineage, lands a lowest-level
RED case, fixes the owning seam, proves GREEN and resolves the record with `cause`,
`solution`, `caused_by` and `fix_sha`. A block-list bug uses a hotfix job; other bugs enter
approved candidate scope. Documents record the flow; there is no in-repository flow engine.

## The gate

The pre-tool gate evaluates the root whitelist and SDD gate in that order. The root
`AGENTS.md` defines protected, additive and mutating paths plus every fail-open case. Git
chokepoints independently enforce branch names, canonical specs and privacy. Every BLOCK
carries one executable `fix:` line or one operator act.

## Memory

*Memory* is current product truth: `specs/memory/product/**`, `ARCHITECTURE.md` and
`QUALITY.md`. A bound session receives the constitution, technical bootstrap, catalog
digest and open worktrees. Candidate closure runs drift, reconciles every affected atom,
writes exactly one release `memory` entry and regenerates the catalog. Memory contains no
release history.

## Bugs and backlog

`specs/bugs/BUGS.jsonl` holds one record per bug, appended once. New records use
`open | resolved | superseded | rejected`; resolution persists `cause`, `solution`,
`caused_by` and `fix_sha`, while git supplies the implementation diff. The next SPEC's
bug-window review owns maturity, and the closure summary owns delivered and carried scope.

`specs/backlog/BACKLOG.json` is the operator's active demand queue. An entry is created by
`backlog.py new`, picked through a SPEC Origin clause and removed exactly once by
`backlog.py exit`, which appends its terminal history record.

## Audits

An *audit* is the full-tree inspection lane. A live audit directory holds `AUDIT.md` and
`FINDINGS.jsonl`; its three pillars are bug history, spec compliance and memory drift over
the window since the newest archived audit. The bug pillar reports nine forensic metrics.
An audit generates at most one remediation release. `audit.py disposition` moves each
finding to `resolved`, `superseded` or `rejected`; `audit.py close` refuses while any
finding is open, then appends one audit-history record and removes the live directory.
