# ADR 0027 — The pyramid shape is measured every run, reported not gated

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Suite shape degrades slowly: each release adds a few end-to-end tests because they are the
easiest to write, and the fast tier's share erodes until the suite is too slow to run before a
push — which is how the local gate and CI stopped agreeing in the first place. A share
measured from a single collection pass costs almost nothing and makes the drift visible per
run. It is deliberately **reported, not gated**: no threshold on a ratio can distinguish a
legitimate spike from erosion, and a gate that fires on a ratio would be argued away rather
than acted on. Stating that limitation in the principle itself is required — promoting a
measure as if it gated would be the fabricated detection this release outlaws.

## Decision
We will measure the pyramid every run: SMALL/MEDIUM/LARGE shares are computed from one
`--collect-only` pass and judged against the 75/20/5 target with a ±5 pp tolerance —
**reported, not gated**; a drift beyond tolerance is a finding raised at release closure.

## Consequences
+ The shape is a number every run prints, so erosion is visible while it is still small.
+ No ratio-based gate exists to be argued around or suppressed.
− The measure never fails on the real repository, so it depends on someone reading the closure
  finding; that dependency is stated rather than hidden.
− The detector itself is only proven on a mutation fixture, which is what keeps it honest.

## Confirmation
Measured by:
`pytest -p no:cacheprovider -s tests/contract/test_test_suite_ratchets.py -k v30` (prints the
tier shares; the detector is proven on a mutation fixture).
