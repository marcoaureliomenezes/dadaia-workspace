# ADR 0010 — Suppressed layering edges are capped and ratchet down

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Every `ignore_imports` entry is a suppressed layering violation: `lint-imports` stays green
precisely because the edge is ignored, so nothing fails as the list grows. That is the exact
shape of the erosion this workspace has already lived through — architect finding F10 named
it, and the CLI edge class proved it by growing by two in one release without anyone noticing.
A cap turns the list into a number that can only move on purpose. Today it stands at 17
(`features-no-infrastructure` 7, `features-no-subprocess` 3, `features-no-cross-feature` 5,
`cli-no-infrastructure` 2) after T-050-29 made three hidden `reconcile` edges visible.

## Decision
We will cap the total number of suppressed layering edges, pin it per family, and ratchet it
only downward: adding an edge requires a rationale comment on the edge in `setup.cfg` **and**
a bump of the recorded cap in the same commit; removing one lowers both, also in the same
commit. The `setup.cfg` header comment states the same numbers so a reader sees the debt
without running anything.

## Consequences
+ Architecture debt grows only with a reviewer looking at the diff that grows it.
+ The per-family pin localises the growth — a spike in one family is visible, not averaged
  away by a removal elsewhere.
− Legitimate transitional edges cost two coordinated edits and a review conversation.
− The header comment is kept in sync by discipline; the test, not the comment, is the
  authority (they disagreed before this release and the comment was the stale one).

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py`
(exact-equality total cap 17, per-family pins 7/3/5/2, sanctioned-source check).
