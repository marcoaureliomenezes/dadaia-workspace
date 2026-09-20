---
slug: QUALITY
title: Quality Assurance
tldr: QA standards, anti-slop rules, and test discipline for this workspace.
summary: Documents QA standards, anti-slop laws, test discipline (TDD, no fabricated tests), and the pre-commit/pre-push gate sequence.
tags:
  - quality-assurance
  - testing
  - anti-slop
---

## Quality standards

**Greenfield baseline (holds until the first release consolidates the project's own):**

- TDD: every new behaviour is born with a test that fails first; a bug fix reproduces the
  defect in a test before the fix.
- Tests run with the bare command — `pyproject.toml` redirects every cache out of the repo —
  and must be green before any task-closing commit.
- Reviews judge the artifact presented by the criteria above; in a new context, an absent
  history is no ground for rejection — the current SPEC defines the baseline.

## Test discipline

Size by directory: SMALL = `tests/unit` + `tests/contract`; MEDIUM = `tests/integration`;
LARGE = `tests/e2e`. Full protocol (intent, admission, demotion, pruning,
flaky/quarantine): the `dd-test-stewardship` skill. Project-level law: the constitution's
"Test discipline" section.

<!-- dadaia:fixed slop-tests -->
<!-- /dadaia:fixed slop-tests -->
