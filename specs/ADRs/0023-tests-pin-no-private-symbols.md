# ADR 0023 — Private-symbol imports in tests ratchet down

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
A test that imports `_private_helper` binds the suite to an implementation detail: the
refactor that should have been free breaks a hundred tests, so the refactor does not happen
and the structure stays wrong. That is the erosion path this workspace's standing order
exists to stop, expressed in the test suite instead of production. The count is measured
AST-exactly rather than by grep, because a single-line grep undercounts multi-line
`import (...)` continuations — which is exactly how an earlier, too-optimistic baseline for
this very metric was produced.

## Decision
We will ratchet private-symbol imports in `tests/**` downward only, from the measured ceiling
(60 statements across 54 files) toward zero; the only exception is a per-statement
`# allow-private-import: <reason>` marker, never a file-level exemption.

## Consequences
+ Refactoring a private helper stops being a suite-wide event, so structural fixes get cheaper
  over time.
+ Each surviving exception carries its own recorded reason at the import that needs it.
− A test that genuinely needs an internal seam must either justify the exception or motivate a
  public seam.
− The count is a proxy: it measures coupling, not test quality.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v26` (AST-exact
count; DOWN-only ratchet).
