# ADR 0026 — One number per parameter

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The LARGE-test cap existed twice: the stewardship parameters file said 30, and the quality
memory atom said 100. Two homes for one parameter is worse than none — a reader picks the one
that suits the decision at hand, and neither number was ever wrong enough to be corrected.
This is the reader/writer drift that hand-kept duplicates always produce, the same class of
defect the `modules =` list showed in the layering contracts (ADR 0007). The disposition is a
single literal home plus references everywhere else, measured by counting competing homes and
ratcheting that count to zero.

## Decision
We will keep one number per parameter: the stewardship parameters file is the LARGE cap's only
literal home, and every other doctrine file references it and carries no number of its own.

## Consequences
+ Tuning a parameter is one edit, and no document can silently disagree with it.
+ The competing-home count is a mechanical measure of the drift, not a review opinion.
− Reading a doctrine file now requires one hop to the parameters file for the value.
− The check covers the LARGE cap's home specifically; other duplicated numbers are only
  reachable by extending it.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v29`
(competing-literal-home count, pinned at 0 after the duplicate was deleted).
