# ADR 0022 — Quarantine requires a registered bug

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Quarantine is the honest way to keep a flaky test in the tree without gating on it — and the
dishonest way to make a red suite green. The difference is whether the failure is registered
as a bug that someone owns. Without that link, the quarantine lane becomes a graveyard: the
suite reports green, the defect is real, and nobody can enumerate what was set aside. The
mark is therefore refused at collection unless it names a bug, in both the serial and the
xdist paths, and every gating selector excludes the lane so a quarantined test can never be
mistaken for coverage.

## Decision
We will gate quarantine on a registered bug: a `quarantine` mark without a `bug=` reference
refuses collection with an actionable message, and the quarantine lane is excluded from every
gating selector.

## Consequences
+ The set of set-aside failures is always enumerable from the bug ledger.
+ A green run with quarantined tests is legitimately green, because the lane is out of the
  gate by design.
− Quarantining costs a bug registration, deliberately — it is not a one-line escape.
− A test can still rot inside the lane if its bug is never worked; the ledger, not the suite,
  surfaces that.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "quarantine"`
(collection refusal serial and under xdist; selector exclusion).
