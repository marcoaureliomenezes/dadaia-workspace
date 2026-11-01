---
slug: audits-canon
title: audits-canon
tldr: An audit runs bug-history, spec-compliance and memory-drift pillars over one measured window and stores schema-valid findings until terminal disposition.
summary: The three-pillar audit, reproducible finding evidence, terminal disposition vocabulary, single remediation release and atomic archive close.
tags: [audit, findings, bugs, specs, memory]
sources:
  - dadaia_workspace/public/schemas/ADRs/**
  - dadaia_workspace/public/skills/dd-audit-project/**
  - dadaia_workspace/features/specs/doctor_adr.py
---

## Three pillars

- An audit is the full-tree inspection lane and always runs bug history, spec compliance and memory drift together.
- The bug pillar reads current resolution facts and each fix, found by its `fix(bugs)` or `refactor(bugs)` id line (a group line lists several ids; the recorded `fix_sha` is only a hint a rewrite may orphan, and a release squash is reported as coarse evidence), reads a unit's history by the id-line query, never a stored fix-file field, derives recurrence (a later record whose `component` names a path a prior fix commit touches, registered after that fix's resolution) and diff direction from code, groups re-bugs by the paths each fix commit touches, and reports the forensic metrics `PILLAR-BUGS.md` lists, each against the previous audit's `AUDIT.md` read from git history. Audit coverage lives in the audit record rather than a field copied into each bug.
- The spec pillar combines the doctor's findings at HEAD with commit shapes and job-file checks: tasks with overlapping write sets that ran in parallel, every changed path inside its job's PLAN write set, AC test levels, cancellation reasons and post-approval immutability.
- The memory pillar runs each canonical principle's measurement and compares product atoms with their source window.

## Findings

- Every finding is one `finding-record-v1` line with immutable id, pillar, severity, refs, claim and reproducible evidence, appended by hand; `audit.py check` validates the live findings and the archive, printing each finding with its `fix:` line.
- Evidence is a command plus a redacted one-line result. Scratch may accompany it but is never the sole citation.
- A finding is born `open` and moves to `resolved`, `superseded` or `rejected`. Resolved and superseded name the remediation release; rejected names the reason.
- `audit.py disposition` rewrites only the governance triple. It rejects an unknown finding, invalid evidence or a second inconsistent disposition.

## Close

- `audit.py close <audit> --sha <window-end>` refuses while any finding remains open or the findings name more than one remediation release.
- Close appends one audit-history record with the window sha, pillar counts and disposition counts, then removes the live audit directory atomically.
- A closed audit with a remediation release is resolved; without one it is rejected.

## Dependencies

[[bug-ledger]], [[release-lifecycle]], [[workspace-doctor]], [[ARCHITECTURE]], [[QUALITY]].
