---
name: dd-diagnose
description: >
  The diagnosing method for Arm B, called by dd-bug-resolution: seven phases from
  lineage through cleanup, each ending on a checkable Done when. Phase 0 reads the
  bug ledger's lineage before any hypothesis is formed.
tldr: "7-phase diagnosing method: lineage -> red loop -> minimize -> hypotheses -> instrument -> test seam -> cleanup."
applyTo: "specs/bugs/**"
disable-model-invocation: true
---

# dd-diagnose — The Diagnosing Method (Arm B)

> Not hook-enforced. `disable-model-invocation: true` — read on reference from `dd-bug-resolution`, not yet in a persona's `skills:` allowlist.

## 1. When

- Called by `dd-bug-resolution` the moment a bug carries a `reported` event and Arm B begins.
- This skill owns only the method — it never registers, brands, or closes a bug on its own.

## 2. Steps

1. Phase 0 — read the bug ledger for prior fixes to the same `surface`/`component`, in a bounded window (`LINEAGE.md`).
2. Phase 0 — declare `caused_by: <bug_id> | none` and `lineage_source: declared` via `dadaia bugs update`.
3. Phase 0 — echo the same `caused_by:`/`evidence:`/`prior diffs read:` block in the eventual fix commit body.
4. Phase 1 — red loop: reproduce the failure exactly (real command, real environment, real path) before any hypothesis.
5. Phase 2 — minimize the reproduction until every remaining element is load-bearing (removing any stops the failure).
6. Phase 3 — write 3-5 falsifiable hypotheses before touching code, each paired with a killing observation.
7. Phase 4 — instrument (probes/logs/asserts) on the executed path; never read code for a theory.
8. Phase 5 — write the regression test at the correct seam, intent/size declared at birth (`dadaia-test-stewardship` §A).
9. Phase 5 — if no correct seam exists, register an architecture finding and dispatch `software-architect` before fixing.
10. Phase 6 — remove every phase-4 probe; the diff must leave the touched feature smaller or equal, never bigger.
11. Route a `caused_by` naming a prior bug to `software-architect` before the commit, if the diff is net-positive.
12. Hand back to `dd-bug-resolution` at phase 6, GREEN — never append `resolved` or a commit shape from this skill.

## 3. Done when

- Phase 0: `caused_by`/`lineage_source` declared on this bug's record, echoed in the fix commit body.
- Red loop captured before any hypothesis; repro minimized to load-bearing.
- Surviving hypothesis confirmed by instrumentation, not by reading code.
- Test lands at the correct seam, or an architecture finding is registered first.
- Cleanup done (probes gone, diff smaller or equal); GREEN.

## 4. References

- `LINEAGE.md` — phase 0 in full: window, filter, cap, diff-trust rule.
- `dd-bug-resolution` — bug lifecycle, commit shape, branch, concurrency, the `resolved` write.
- `dadaia-test-stewardship` §A — intent/size declaration.
- `DADAIA.md` §7 (Quality) — root-cause law, net-positive routing.
