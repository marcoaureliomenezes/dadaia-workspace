---
name: dd-code-review
description: >
  Use when reviewing a job, plain change, PR, branch or commit range, or when an audit
  or curation verdict needs the Bug-surface axis. Three axes reported side by side —
  Standards (repo conventions, twelve Fowler smells, SLOP.md S1-S10), Spec (the diff does
  what the approved SPEC and job files say, nothing more), Bug-surface (ledger evidence
  that the touched feature's bug surface shrank, held or grew) — plus six lenses, ending
  in an APPROVED/REJECTED verdict. Returns findings; the implementer writes the fix.
compatibility: Standalone Agent Skill. Inside a dadaia-workspace (pip install dadaia-workspace) it also drives the SDD lifecycle — specs, backlog, bugs, releases.
---

# dd-code-review

Three axes, run as three sequential passes. Findings from different
axes are reported side by side with equal weight, so no axis hides another's finding.

## 1. When

1. Inside a dadaia workspace, open `specs/memory/AGENTS.md` (the area's scoped law) and follow it — the diff is
   judged against current product truth.
2. Reviewing a PR, branch or commit range before the candidate's PR.
3. A curation, architecture or audit verdict needs the Bug-surface axis (§4).

## 2. Axis 1 — Standards

- The repo's own documented conventions come FIRST and always override the baseline.
- Skip anything tooling already enforces (lint, typecheck and import-rule findings are not review findings).
- Baseline: the twelve Fowler smells, each reported as a labelled judgement call:
  Mysterious Name · Duplicated Code · Feature Envy · Data Clumps · Primitive Obsession ·
  Repeated Switches · Shotgun Surgery · Divergent Change · Speculative Generality ·
  Message Chains · Middle Man · Refused Bequest.
- Judge size by responsibility: a long method, a class with many methods or a file doing several jobs — one reason to change per class and per method.
- Slop signals S1-S10, each with its diff check: [`SLOP.md`](SLOP.md) — reported inside this axis.

## 3. Axis 2 — Spec

- Read `<specs-dir>/releases/<v>/rc-<N>/SPEC.md` (`**Status:** Approved`) and the job's `rc-<N>/tasks/<job>.md`.
- Does the diff do what they say — nothing more, nothing less?
- Scope growth beyond the task's declared write set is a finding, even when the code is good.
- Acceptance criteria without corresponding evidence (test/assertion) is a finding.
- Read `rc-<N>/PLAN.md` §1 (As-is review) beside the SPEC and job files: a DELETE or REBUILD unit the range leaves unchanged is HIGH.
- A KEEP unit the range grew is a finding.
- A worktree's (`worktrees/AGENTS.md`) commits follow the `dd-gitflow-default` §3a rows of what they write.

## 4. Axis 3 — Bug-surface

- Pull the touched feature's ledger slice: `grep -h '"surface": "<surface>"' <specs-dir>/bugs/BUGS.jsonl <specs-dir>/bugs/_archive/bugs_histo.jsonl`.
- Answer WITH EVIDENCE: did this diff reduce, keep, or increase the feature's bug surface?
- The operator's rule applied as a review axis: a diff that GROWS the feature is a stop —
  a branch, flag, special case, second code path or cross-feature reach-in added by a fix
  is a layer; name it and recommend the replace-don't-layer shape instead.
- A fix whose `caused_by` is not `none`: inspect the named commit per `.agents/skills/dd-bug-resolution/LINEAGE.md` §Read persisted facts; a patch where a REBUILD of the unit was due is a finding.

## 4a. The root-cause and approval bars

- A fix qualifies only when it reproduces the failure on the executed path, tests for the real reason, fixes the cause and proves it green — a workaround or symptom patch is a finding.
- The verdict is the enum `APPROVED`/`REJECTED`: on a worktree, written by `verdict.py` (`worktrees/AGENTS.md` §2); on a PR, returned as text the main thread quotes (`dd-gitflow-default` §3b).
- A green internal gate that diverges from real consumer behavior is itself a bug.

## 5. Done when — the report carries

- Findings carry: axis, severity (CRITICAL/HIGH/MEDIUM/LOW/INFO), `file:line`, what the code does, fix direction (never code).
- The three axes appear side by side in the report; the verdict (`APPROVED`/`REJECTED` — the handoff schema's enum) follows the caller persona's rules.
- Every verdict states the Bug-surface answer with ledger evidence, because a green suite says nothing about whether the feature grew.

## 6. The six lenses

One reviewer, six checklists applied on every verdict; the engineer anticipates them.

- **Architecture** — root cause named; the diff shrinks or keeps the feature; per PLAN §1.1 row, every `deleted` gone and every `consults` calls the authority (S4/S5/S10).
- **Security** — OWASP top 10, secrets, dependency CVEs (the ecosystem's dependency audit), CWE id per finding.
- **QA** — every acceptance scenario has evidence; the pyramid holds; tests keep the root map §1 basics; pruning only by a curation verdict; a bug fix adds a case and rewrites no assert (`git diff -U0 <base>...HEAD -- <the repo's test globs> | grep -E '^-.*<assertion keywords>'` prints nothing) — a miss is HIGH, verdict REJECTED.
- **Product** — the diff matches SPEC scope; memory atoms still tell the truth (`.agents/skills/dd-release-implementation/MEMORY-UPDATE.md`).
- **Audit** — `dd-audit-project` pillars over the window, `SLOP.md` S1-S10 in pillar 2; findings, never fixes.
- **AI surface** — every agent, skill, rule or hook change satisfies the fifteen rules of `.agents/skills/dd-ai-eng-knowhow/AUTHORING.md`.

## 7. References

- [`SLOP.md`](SLOP.md) — slop signals S1-S10 and their diff checks.
