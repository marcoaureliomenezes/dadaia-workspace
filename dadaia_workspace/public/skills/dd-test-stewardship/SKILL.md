---
name: dd-test-stewardship
description: >
  The test lifecycle: intent declaration and admission for a new test, size tiers,
  demotion at closure, evidence-gated deletion, flake quarantine, artifact hygiene.
  Use when writing or reviewing a test, closing a release or task, handling a flaky
  test, or judging a deletion candidate.
---

# dd-test-stewardship

> The law (`DADAIA.md` §7) states five points once; this skill is where they operate.
> Numeric values live in [`PARAMETERS.md`](PARAMETERS.md) — this workspace's declared
> defaults, re-parameterized per consumer.

## Intent and admission — writing a new test

- Declare intent in the module docstring: `Intent: <KIND> — <AC id | bug-id |
  task-id>` — never as a pytest marker.
- The kinds: **CONTRACT** (permanent, asserts an AC or bug fix), **SENTINEL**
  (permanent, one per seam max), **SCAFFOLD** (temporary, expires at its
  task/release closure), **QUARANTINE** (temporary, carries a bug id). An undeclared
  test is SCAFFOLD — the default is to die, not to stay.
- Admit a test only if it compiles, runs deterministically, and adds real detection
  (new coverage or kills a new mutant). Change-detector tests, tautologies and
  reflex-regenerated snapshots fail admission; a brittle test is fixed or deleted,
  never appeased.

## Size tiers

- Place at the cheapest tier that detects the failure: `unit`+`contract` = SMALL,
  `integration` = MEDIUM, `e2e` = LARGE; justify any heavier placement inline in the
  test.
- A test needing more time than its tier allows has the wrong tier — fix the tier,
  never raise the timeout default.

## Demotion — closure work, never mid-task

- For every demoted LARGE, yield the `file:line` of the replacement SMALL/MEDIUM
  coverage, or keep it as the seam's single SENTINEL.
- Record the demotion map in `_RELEASE.json`'s `log`
  (`dd-release-implementation`).

## Deletion — a qa-engineer verdict, executed by software-engineer

- Delete only on a decision-table criterion, cited with evidence in the commit:
  feature removed · duplicate coverage · tautology/no-op · reflex snapshot ·
  zero-defect flake history · expired quarantine.
- A tombstone test dies together with its target — it validates a historical event,
  not live behavior.
- Pruning to go green is exclusively a `qa-engineer` verdict; the implementer
  executes the commit.

## Flakes and quarantine

- On a flaky event: mark `quarantine` with a required bug id AND register the bug —
  one act (`dd-bug-registration`); bound diagnostic reruns at 3 attempts.
- Escalate an unresolved quarantine to `disabled` at the `PARAMETERS.md` deadline;
  restore to normal after the clean window; delete a `disabled` test with no
  registered plan after 1 release.
- Block admission of new LARGE tests while quarantine sits at cap.

## Artifact hygiene and health

- Capture is failure-gated: screenshot only-on-failure; trace/video
  retain-on-failure or on-first-retry — never unconditional.
- Delete a probe/generator/release script with no referenced invoker at curation.
- Watch flake rate, wall-clock trend, and failure-to-defect ratio continuously;
  run mutation testing once per release, off the push path — a test killing no
  mutant that is not a SENTINEL enters curation.

## Done when

- Every new test carries an intent docstring and passed admission.
- Every demoted LARGE has a replacement `file:line` or is the seam's sole SENTINEL,
  recorded in `_RELEASE.json`'s `log`.
- Every deleted test cites its criterion and evidence; every quarantined test
  carries a registered bug id.

## References

- [`PARAMETERS.md`](PARAMETERS.md) — LARGE cap, flake ceiling, quarantine
  cap/escalation, timeouts, wall-clock budget, mutation cadence.
- `dd-task-manager` — reservation discipline for a curation-verdict commit.
- `dd-audit-project` — detection-quality scoring for drift audits.
- `DADAIA.md` §5 — artifact retention and repo cleanliness; §7 — the five-point law.
