# ADR 0020 — `specs upgrade` and `specs doctor` do not grow

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
The forensic behind release 0.5.0 traced one bug chain to these two verbs: a `specs upgrade`
that emitted atoms violating the frontmatter schema bred four follower bugs in eight days.
The structural reading is that both verbs had become branch farms — every prior fix added
another case — so each new fix had more paths to get wrong. The measured baseline at the
start of this release is `#upgrade` CC 26 and `#doctor` CC 30; the migration module behind
the upgrade is additionally pinned by content hash, because the release's own plan cut its
rename automation and any edit to it must justify itself rather than slip in.

## Decision
We will not grow `specs upgrade` and `specs doctor`: their cyclomatic complexity is pinned at
the measured baseline and moves only downward, and `features/migrate/upgrade.py` changes only
with a same-commit justification.

## Consequences
+ The chain-1 surface cannot absorb another special case silently; a fix there must simplify
  or be argued for.
+ A new option renders in its own function, so adding one does not move either ceiling.
− A hash-pinned module makes even a formatting change a deliberate act.
− The pin encodes a complexity level that is still too high; it is a floor for improvement,
  not an endorsement.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_specs_cli_complexity_ratchet.py`
(radon complexity for both functions; pinned SHA-256 of `features/migrate/upgrade.py`).
