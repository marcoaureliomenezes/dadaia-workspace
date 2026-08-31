---
name: dadaia-test-stewardship
description: >
  Use when: writing a new test, reviewing a test file, closing a release or task
  (the demotion step), a test is reported flaky, or a test is a deletion candidate.
  The single operational home of the test lifecycle — intent taxonomy, admission,
  size tiers, demotion, deletion, flake/quarantine, artifact hygiene, health. The
  law (`DADAIA.md` §7 (Quality)) states five points once; this skill is where they
  operate.
tldr: "Declare intent, pass admission, size-tier, demote/delete with evidence, quarantine flakes with a bug id."
---

# dadaia-test-stewardship

> Universal skill, read natively by every entry harness.
> Numeric values live in `PARAMETERS.md` (sibling) — this workspace's declared defaults, re-parameterized per consumer.

## 1. When

- Writing a new test.
- Reviewing a test file.
- Closing a release or task (the demotion step).
- A test is reported flaky.
- A test is a deletion candidate.

## 2. Steps

1. Declare intent in the module docstring: `Intent: <KIND> — <AC id | bug-id | task-id>` — never as a pytest marker.
2. Pick the kind: CONTRACT (permanent, asserts an AC or bug fix), SENTINEL (permanent, 1 per seam max).
3. Pick the kind (continued): SCAFFOLD (temporary, expires at its task/release closure), QUARANTINE (temporary, carries a bug id).
4. Treat an undeclared test as SCAFFOLD — the default is to die, not to stay.
5. Admit a new test only if it compiles, runs deterministically, and adds real detection (new coverage or kills a new mutant).
6. Reject change-detector tests, tautologies, reflex-regenerated snapshots, and brittle tests appeased instead of fixed/deleted.
7. Place at the cheapest tier that detects the failure: `unit`+`contract` = SMALL, `integration` = MEDIUM, `e2e` = LARGE.
8. Justify any tier heavier than the cheapest detecting one, written inline in the test.
9. Fix the tier, never raise the timeout default, when a test needs more time than its tier allows.
10. At closure (never mid-task), yield file:line of the replacement SMALL/MEDIUM coverage for every demoted LARGE.
11. Keep a demoted LARGE only as the seam's single SENTINEL, otherwise record the demotion map in `_RELEASE.json`'s `log`.
12. Delete only when a decision-table criterion is true (§4), citing the evidence in the commit.
13. Never delete a tombstone test's target without deleting the test itself — it validates a historical event, not live behavior.
14. Never let the implementer prune to go green — pruning is a `qa-engineer` verdict; `software-engineer` executes the commit.
15. On a flaky-event: mark `quarantine` with a required bug id, and register the bug, as one act.
16. Escalate an unresolved quarantine to `disabled` at 30 days; restore to normal after 30 clean days.
17. Delete a `disabled` test with no registered plan after 1 release.
18. Bound diagnostic reruns at 3 attempts; block admission of new LARGE tests while quarantine sits at cap.
19. Keep capture failure-gated (screenshot only-on-failure; trace/video retain-on-failure or on-first-retry), never unconditional.
20. Delete a probe/generator/release script with no referenced invoker at curation.
21. Watch flake rate, wall-clock trend, and failure-to-defect ratio continuously — never calendar-only.
22. Run mutation testing 1x/release, off the push path; a test killing no mutant and not a SENTINEL enters curation.

## 3. Done when

- Every new test carries an intent docstring and passed the admission filter.
- Every demoted LARGE has a replacement file:line or is the seam's sole SENTINEL, recorded in `_RELEASE.json`'s `log`.
- Every deleted test cites its decision-table criterion and evidence.
- Every quarantined test carries a registered bug id.

## 4. References

- `PARAMETERS.md` — LARGE cap, flake ceiling, quarantine cap/escalation, timeouts, wall-clock budget, mutation cadence.
- Deletion criteria table: feature removed, duplicate coverage, tautology/no-op, reflex snapshot, zero-defect flake history, expired quarantine.
- `dadaia-task-manager` — reservation/commit discipline for the agent executing a curation verdict.
- `dd-release-implement` — where the demotion map lands at closure.
- `dd-audit-project` Dimension E — detection-quality scoring for drift audits.
- `dadaia-handoff-emitter` — handoff emission for a steward verdict.
- `DADAIA.md` §5 (Where things are written) — artifact retention/repo-cleanliness (unchanged by this skill).
- `DADAIA.md` §7 (Quality) — the five-point law this skill operates.
