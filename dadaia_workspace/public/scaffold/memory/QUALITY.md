---
slug: QUALITY
title: Quality Assurance
tldr: QA principles, test architecture and the gates every change passes.
summary: The Principles section holds the quality principles; the Test architecture and Gates sections describe how the project is verified today.
tags:
  - quality-assurance
  - testing
  - anti-slop
---

## Principles

No principle is recorded yet.

## Test architecture

Size by what a test reaches: SMALL = no process and no real git; MEDIUM =
a subprocess or real git; LARGE = `tests/e2e`. Test basics: the root `AGENTS.md` map §1.

## Gates

The repo's tracked `verify:` line runs once, at the merge; nothing reruns it before a push.

<!-- dadaia:fixed slop-tests -->
<!-- /dadaia:fixed slop-tests -->
