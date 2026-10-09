---
slug: audits-canon
title: audits-canon
tldr: An audit runs bug-history, spec-compliance and memory-drift pillars over one measured window and stores schema-valid findings until terminal disposition.
summary: The three-pillar audit, reproducible finding evidence, terminal disposition vocabulary, single remediation release and atomic archive close.
tags: [audit, findings, bugs, specs, memory]
sources:
  - dadaia_workspace/public/schemas/audits/finding-record-v1.schema.json
  - dadaia_workspace/public/schemas/ADRs/**
  - dadaia_workspace/public/skills/dd-audit-project/**
  - dadaia_workspace/features/specs/doctor_adr.py
---

## Three pillars

- An audit is the full-tree inspection lane and always runs bug history, spec compliance and memory drift together.
- The bug pillar reads current resolution facts and each named `fix_sha`, derives recurrence and diff direction from code, and reports nine forensic metrics. Audit coverage lives in the audit record rather than a field copied into each bug.
- The spec pillar combines doctor output with commit shapes and job-file checks: wave and task write-set disjointness, path coverage, AC test levels, cancellation reasons and post-approval immutability.
- The memory pillar runs each canonical principle's measurement, checks decision pairing and compares product atoms with their source window.

## Findings

- Every finding is one `finding-record-v1` line with immutable id, pillar, severity, refs, claim and reproducible evidence.
- Evidence is a command plus a redacted one-line result. Scratch may accompany it but is never the sole citation.
- A finding is born `open` and moves to `resolved`, `superseded` or `rejected`. Resolved and superseded name the remediation release; rejected names the reason.
- `audit.py disposition` rewrites only the governance triple. It rejects an unknown finding, invalid evidence or a second inconsistent disposition.

## Close

- `audit.py close <audit> --sha <window-end>` refuses while any finding remains open or the findings name more than one remediation release.
- Close appends one audit-history record with the window sha, pillar counts and disposition counts, then removes the live audit directory atomically.
- A closed audit with a remediation release is resolved; without one it is rejected.

## Dependencies

[[bug-ledger]], [[release-lifecycle]], [[workspace-doctor]], [[ARCHITECTURE]], [[QUALITY]].
