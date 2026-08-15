---
title: "Mechanical enforcement of the test intent docstring (P9)"
status: candidate
opened: 2026-08-14
description: >-
  v0.7.0 CLOSURE backlog return, materialized 2026-08-14 (grill ADR #5 — the CLOSURE
  claimed this routing but it never happened). CLOSURE text: "Mechanical enforcement
  of the intent docstring (P9). 384 existing files are non-compliant, so a check today
  would be unsatisfiable — a defect in the check under the Satisfiable Diagnostics law.
  Enforceable once the companion remediation lands." The companion remediation is the
  (rewritten) test-suite-remediation-stewardship entry; this check stays blocked on it.
intents:
  - subject:
      kind: doc
      ref: memory/quality-assurance.md#Anti-Slop
    change: >-
      Once the suite remediation brings existing test files into intent-docstring
      compliance, add the mechanical check (lint/CI) that refuses a new test without a
      declared intent/size — satisfiable by construction only after the remediation,
      per the Satisfiable Diagnostics law.
---

# Mechanical enforcement of the test intent docstring (P9)

## Description

See frontmatter. Provenance: `specs/_archive/releases/v0.7.0/CLOSURE.md` §"Backlog
returns", second item (destination `backlog/candidates.md`). Dependency:
`test-suite-remediation-stewardship` must land first — enforcing today would be an
unsatisfiable diagnostic (the defect class the law forbids).

## Acceptance criteria

The check exists, runs in CI, fails only on genuinely undeclared tests, and was turned
on only after the compliance remediation; zero false positives on the remediated suite.
