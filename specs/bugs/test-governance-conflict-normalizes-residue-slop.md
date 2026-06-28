---
name: test-governance-conflict-normalizes-residue-slop
status: Closed
severity: HIGH
reported: 2026-06-28
resolved_in: v0.1.34
surface: tests/AGENTS.md + tests/contract/README.md + tests/contract/test_lifecycle_asymmetry_map.py
session_id: null
---

**Resolution (v0.1.34):** Reconciled the governance conflict in favor of the
behavior-first `tests/AGENTS.md` law. `specs/memory/quality-assurance.md` now defines
the canonical quality schema and residue exception rule. `tests/contract/README.md`
no longer declares residue grep as the canonical delete/orphan contract and no longer
requires a per-feature lifecycle-asymmetry map. The enforcing meta-test
`tests/contract/test_lifecycle_asymmetry_map.py` was removed. Obvious residue-only
contract tests for plugin-install wording and retired bash hooks were deleted, and the
retired-model contract was reduced to the current registry behavior check.

**Symptom:** The test suite keeps accumulating tests for retired implementation
history and deleted surfaces. During a suite audit, collection found about 4.2k
tests for the current `dadaia-workspace` repo, with multiple active contract
tests permanently pinning absence of retired terms, deleted modules, legacy
scripts, and every `features/` subpackage's lifecycle-asymmetry map entry.

**Expected:** Test governance should enforce the current `tests/AGENTS.md`
standard: a test must be able to fail for a meaningful regression in current
product behavior, public contract, security boundary, data integrity, or a real
user journey. Tests that only prove deleted code remains deleted should not be
added unless they protect a documented security or compatibility boundary.

**Root cause:** The repository has contradictory authoritative guidance:

- `tests/AGENTS.md` says "Do not add tests that only prove deleted code remains
  deleted" and bans retired invariants unless they protect a documented
  security or compatibility contract.
- `tests/contract/README.md` says "A residue grep is the canonical contract form
  for the delete/orphan path" and requires every `features/` subpackage to be
  represented in a lifecycle-asymmetry coverage map.
- `tests/contract/test_lifecycle_asymmetry_map.py` mechanically enforces that
  map against every live feature package, so adding or keeping feature packages
  creates permanent pressure to add coverage rows or GAP entries even when the
  feature is read-only, scaffold-only, or not part of the product's current
  critical behavior.

This conflict makes slop growth policy-compliant from one document while
forbidden by another. The issue is not one bad test; the policy surface itself
rewards residue contracts.

**Evidence:** Existing tests include residue contracts for plugin-install
wording, retired bash hook scripts, retired model IDs, session-bound context
residue, session-store ownership residue, and panel deleted-auth symbols. Some
of these may be valid compatibility/security checks, but the current governance
does not force that distinction before making them permanent.

**Needed fix:** Reconcile the test-governance documents into one rule: residue
grep tests are allowed only for a named current security, compatibility, or
public-contract boundary with an owner and retirement condition. Replace the
feature-wide lifecycle-asymmetry map enforcement with behavior-owned contracts
for the small set of current critical flows: Spec Context Projects, Panel, and
dadaia-workflows/lifecycle.
