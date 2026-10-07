---
slug: QUALITY
title: Quality Assurance
tldr: QA principles, test architecture and the gates every change passes.
summary: The Principles section holds the quality principles, changed only by an accepted ADR; the Test architecture and Gates sections describe how the project is verified today.
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

Size by what a test reaches, never its folder: SMALL = no process and no real git; MEDIUM =
a subprocess or real git; LARGE = `tests/e2e`. Test basics: the root `AGENTS.md` map §1.

## Gates

The repo's `verify-task:` line runs green before any task-closing commit, its `verify:` line before every push.

<!-- dadaia:fixed slop-tests -->
<!-- /dadaia:fixed slop-tests -->
