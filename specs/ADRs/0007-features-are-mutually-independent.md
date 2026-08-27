# ADR 0007 — Features are mutually independent

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
Cross-feature erosion is the mechanism behind this workspace's bug loop: one feature reaches
into a sibling's internals, the sibling changes, and the fix lands as a branch inside the
reaching feature instead of at the boundary. The `independence` contract was introduced to
stop it, but its `modules =` list is hand-kept — and the S4 inventory measured the drift that
hand-kept lists always produce: 20 of 24 packages were listed, so three real sibling imports
(`reconcile.service` → `capabilities`, → `migrate.legacy_dadaia_dirs`, → `migrate.state_v2`)
were invisible to the only check that measures feature independence. Promoting the principle
over that state would have made it false at birth. T-050-29 listed all 24 packages, declared
the three edges with reasons, moved the cap 14 → 17, and added the on-disk equality assertion.

## Decision
We will keep features mutually independent: they compose through the container, never through
sibling imports, and a helper two features need lives in each of them (duplication over
coupling). The contract's `modules =` list equals the feature packages on disk, so a new
package is inside the check the moment it exists.

## Consequences
+ A new cross-feature edge from any feature — including a brand-new one — fails the contract.
+ The three `reconcile` edges are now visible, capped debt with a named rewrite, instead of
  silent coupling.
− Deliberate duplication of small helpers across features is accepted as the cheaper failure.
− A genuinely needed sibling capability costs a container-mediated rewrite, not an import.

## Confirmation
Measured by: `lint-imports --config setup.cfg --no-cache` — contract
`features-no-cross-feature` (5 declared edges) — plus
`pytest -p no:cacheprovider tests/contract/test_import_linter_ignore_cap.py` (V32: `modules =`
equals the `dadaia_workspace/features/*/__init__.py` package set on disk).
