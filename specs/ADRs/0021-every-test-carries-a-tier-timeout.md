# ADR 0021 — Every test carries a size tier with an enforced timeout

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
A suite without size discipline degrades in one direction only: a "unit" test acquires a
subprocess, then a real venv build, then a network wait, and the fast tier stops being fast
while nobody notices which test did it. This repository has already paid for that — a suite
rearchitecture was needed to bring runtimes back — so the tier is not documentation, it is a
budget. The timeout is applied at collection from the test's directory tier, and the check is
executed-path: it asserts the marker this very suite's conftest applied to the asserting test
itself, rather than re-reading the configuration that was supposed to apply it.

## Decision
We will give every test a size tier with an enforced timeout applied at collection — unit
10 s, contract 30 s, integration 60 s, e2e 120 s — and an explicit `@pytest.mark.timeout` on a
test is never overridden by the tier default.

## Consequences
+ A test that outgrows its tier fails on time rather than slowing every run silently.
+ The tier of a test is discoverable from where it lives, so cost is predictable per selector.
− A legitimately slow case must move tier or carry its own explicit marker.
− Timeouts are wall-clock and can fire on a loaded machine; that noise is accepted as cheaper
  than an unbounded suite.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_stewardship_mechanics.py -k "timeout"`
(executed-path: the timeout marker on the test's own item).
