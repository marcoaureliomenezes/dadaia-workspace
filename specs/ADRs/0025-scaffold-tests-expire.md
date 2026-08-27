# ADR 0025 — SCAFFOLD tests expire

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Scaffolding is legitimate: a test written to drive one release's construction and then removed.
What is not legitimate is scaffolding that stays forever, because it accumulates as slop that
runs on every push, fails for reasons nobody owns, and inflates the suite's apparent coverage.
An expiry field turns the promise into a date the suite can check: a SCAFFOLD naming a release
that has already been archived is red until a `qa-engineer` verdict renews or removes it. The
archive-membership check matches directory names exactly, with no `v`-prefix normalisation,
because this workspace carries legacy `vM.m.p` archives from a numbering track that predates
the current canon and silently equating the two forms would fabricate a match.

## Decision
We will expire SCAFFOLD tests: every `Intent: SCAFFOLD` header names `expires: <M.m.p>`, and a
SCAFFOLD naming an archived release fails the suite until a `qa-engineer` verdict renews or
deletes it.

## Consequences
+ Temporary tests are genuinely temporary, and the deadline is enforced by the suite rather
  than remembered by a person.
+ Renewal is a recorded verdict with evidence, not a silent edit.
− A useful SCAFFOLD needs an explicit renewal at each expiry, which costs a QA decision.
− Exact archive matching means a mis-typed release name reads as unexpired; the header is
  reviewed at birth for that reason.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_test_suite_ratchets.py -k v28` (`expires:`
present; exact archive-directory membership).
