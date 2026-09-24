---
slug: QUALITY
title: Quality Assurance
tldr: QA principles, test architecture and the gates every change passes.
summary: Part 1 holds the quality principles, changed only by an accepted ADR; the Test architecture and Gates sections describe how the project is verified today.
tags:
  - quality-assurance
  - testing
  - anti-slop
---

## Principles

- TDD: every new behaviour is born with a test that fails first; a bug fix reproduces the
  defect in a test before the fix.
- Reviews judge the artifact by its SPEC; an absent history is no ground for rejection.

## Test architecture

Size by directory: SMALL = `tests/unit` + `tests/contract`; MEDIUM = `tests/integration`;
LARGE = `tests/e2e`. Full protocol: the `dd-test-stewardship` skill.

## Gates

Tests, lint and typecheck run green before any task-closing commit and before every push.

<!-- dadaia:fixed slop-tests -->
<!-- /dadaia:fixed slop-tests -->
