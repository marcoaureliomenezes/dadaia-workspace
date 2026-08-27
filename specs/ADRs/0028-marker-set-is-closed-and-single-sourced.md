# ADR 0028 — The pytest marker set is closed and single-sourced

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Markers are the selector vocabulary: CI jobs, the local preflight and the quarantine exclusion
all address the suite through them. The set is declared in two surfaces — the packaging
configuration and the suite's conftest — and if the two drift, a selector silently matches
nothing and a whole tier stops running while every job stays green. A typo'd marker is the
same failure with a smaller blast radius. `flaky` and `quarantine` must always be present,
because the stewardship lanes (ADR 0022) are defined in terms of them.

## Decision
We will keep the pytest marker set closed and single-sourced: the packaging configuration's
`markers` list equals the conftest's known-marker set — unit, contract, integration, e2e,
slow, tmp, flaky, quarantine — and `flaky` and `quarantine` are always among them.

## Consequences
+ A selector can never silently address an empty set through a drifted or misspelled marker.
+ Adding a lane is a deliberate, two-surface change reviewed as a vocabulary extension.
− Ad-hoc local markers are unavailable; a temporary grouping must use a selector expression
  instead.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k marker_set`
(equality of the two surfaces; `flaky`/`quarantine` membership).
