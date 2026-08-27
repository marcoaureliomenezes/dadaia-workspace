# ADR 0024 — Test intent is declared at birth

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
A test with no declared intent cannot be stewarded: nobody can tell later whether it pins a
contract, guards a regression, or was scaffolding written to reach green once. Undeclared
tests are what made the suite unprunable — every deletion proposal turned into an
archaeology exercise, and the audit that finally pruned it had to reconstruct intent from
`git log`. Declaring intent in the module docstring at creation time is the cheapest possible
moment to record it, and the floor turns "we should" into a measurement that cannot regress.

## Decision
We will declare intent at birth: every `tests/**/test_*.py` module docstring carries an
`Intent: <KIND> — <ref>` header, and the count of files that do ratchets upward only from the
measured floor toward full coverage.

## Consequences
+ Stewardship decisions (keep, demote, delete) read the intent instead of reconstructing it.
+ New files are the cheap place to close the gap, and the floor guarantees the gap only
  shrinks.
− Legacy files without a header remain until someone touches them; the floor tolerates them
  but never lets the number fall.
− The check counts headers, not their accuracy — a wrong `Intent:` is a review matter.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v27` (module-docstring
`Intent:` coverage; UP-only ratchet, floor 108).
