---
name: dadaia-test-stewardship
description: >
  Use when: writing a new test, reviewing a test file, closing a release or task
  (the demotion step), a test is reported flaky, or a test is a deletion candidate.
  The single operational home of the test lifecycle — intent taxonomy, admission,
  size tiers, demotion, deletion, flake/quarantine, artifact hygiene, health. The
  law (`DADAIA.md` §7 (Quality)) states five points once; this skill is where they
  operate.
---

# dadaia-test-stewardship

> Universal skill — read natively by every entry harness, no per-harness derivation.
> Numeric values below are this workspace's declared defaults, in `PARAMETERS.md`
> (sibling); a consumer workspace re-parameterizes them without forking this protocol.

## A — Intent taxonomy

Every test declares intent in its **module docstring** — `Intent: <KIND> — <AC id |
bug-id | task-id>` — **never as a pytest marker**: the marker namespace already binds
`contract` to the layer `tests/contract/`; an intent marker of the same name would
silently re-tier tests and corrupt every `-m` selector in CI.

| Kind | Lifetime | Meaning |
|---|---|---|
| CONTRACT | permanent | Asserts an AC or a bug fix |
| SENTINEL | permanent | The single integration test of one seam (max 1 per seam) |
| SCAFFOLD | temporary | Guides an in-progress task/release; expires at its closure |
| QUARANTINE | temporary | Flaky, under investigation, carries a bug id |

A test that pins a bug fix is CONTRACT — `REGRESSION`/`BUG` are not tokens.

An **undeclared test is SCAFFOLD** — the default is to die, not to stay.

## B — Admission filter

A new test enters the permanent suite only if it: (1) compiles and runs; (2) is
deterministic; (3) adds real detection — covers previously-uncovered behavior **or**
kills a mutant no current test kills. One test per behavior, asserting only on
observable effect.

Prohibited: change-detector tests (mirror the implementation); tautologies (expected
value computed by re-running the code under test); reflex-regenerated snapshots (no
human review of the diff); brittle tests apeased instead of fixed or deleted.

## C — Size tiers (mapped to the existing pytest markers)

SMALL = `unit` + `contract`; MEDIUM = `integration`; LARGE = `e2e`. No new tier marker
is introduced. Assert at the cheapest tier that detects the failure; a larger tier
requires a written justification inline in the test.

| Tier (marker) | Timeout default | Owner rule |
|---|---|---|
| `unit` | 10 s | — |
| `contract` | 30 s | — |
| `integration` | 60 s | — |
| `e2e` (LARGE) | 120 s | every file names an owner |

A test that needs more time than its tier's timeout is **mis-tiered** — fix the tier,
never raise the default. LARGE cap is declared in PARAMETERS.md as a WARN, not a hard failure,
until the count is achievable (companion release's job).

## D — Demotion (at closure, never mid-task)

Each LARGE that validated a feature either (a) yields file:line of the equivalent
SMALL/MEDIUM coverage that now carries the assertion, or (b) is kept as the seam's
single SENTINEL. Deleting coverage without the map is cheating; deleting it with the
map is engineering. The demotion map — deleted LARGE → replacement file:line — is
recorded in `CLOSURE.md` (`dd-release-implement`'s closure steps own the exact block).

## E — Deletion criteria and the tombstone ban

**Decision table — delete when any column is true, cite the evidence in the commit:**

| Criterion | Evidence required |
|---|---|
| (a) Feature removed | link to the removal commit/task |
| (b) Duplicate coverage exists | file:line of the equivalent test |
| (c) Tautology / no-op | shows the assertion never consults the product |
| (d) Reflex-regenerated snapshot | no human review of the diff on last change |
| (e) Failure→defect ratio ≈ 0 | flake/failure history with zero real defects found |
| (f) Expired quarantine/skip, no owner action | see §F escalation |

**Tombstone ban.** A test whose central assertion is the *absence* of something
removed — a deleted feature now 404s, a module became a stub, a directory/repo was
removed, an old migration no longer exists — validates a historical event, not a live
behavior. It is born SCAFFOLD of the release that removed the thing and dies at that
release's closure; the memory of the removal belongs to `CLOSURE.md` / changelog /
product memory, never the suite.

**Separation of powers.** The implementer never prunes to go green. Pruning is a
`qa-engineer` verdict carrying this table's evidence at `file:line`; `software-engineer`
executes the commit, quoting the verdict's evidence.

## F — Flake and quarantine pipeline

**Decision table — flaky-event flow:**

| Event | Action |
|---|---|
| Test observed pass+fail on the same code | Mark `quarantine` (bug id required) + register the bug — same act, immediate |
| 30 days in quarantine, unresolved | Escalate to `disabled` |
| 30 clean days | Restore to normal status |
| `disabled` + 1 release with no registered plan | Delete |
| Diagnostic rerun | Bounded at 3 attempts |
| Quarantine at cap | Blocks admission of new LARGE tests until it empties |

A `quarantine` mark without a registered bug id is refused at collection. Skip/disabled
with no plan for more than 1 release is deletion deferred — delete at the next curation
pass, per criterion (f) above.

## G — Artifact hygiene

Capture is failure-gated by default (screenshot only-on-failure; trace/video
retain-on-failure or on-first-retry) — never unconditional. Where artifacts are
written, retention, and repo-cleanliness are governed by `DADAIA.md` §5 (Where things
are written) — this skill adds nothing there, it only marks capture as failure-gated.
Probes, one-off generators
and release scripts with no referenced invoker are SCAFFOLD: delete at curation if
nothing calls them.

## H — Health, cadence and measurement

Three metrics stay visible continuously (never calendar-only): flake rate, wall-clock
trend, failure→defect ratio per test.

**Decision table — audit trigger (fires the full structural review, not calendar-based):**

| Trigger | Threshold |
|---|---|
| Wall-clock growth without equivalent new behavior | > 25 % |
| Flake rate | above the ceiling (PARAMETERS.md) |
| LARGE count | above the project's declared cap (PARAMETERS.md) |
| Quarantine | at cap (PARAMETERS.md) |

Mutation testing runs 1×/release, off the push path, as the judge of detection value —
a test that kills no mutant and is not a SENTINEL enters the next curation pass under
criterion E(c)/(e). Tool selection is deferred (companion release).

## I — Parameter package (declared adjustable defaults)

The numeric values (LARGE cap, flake ceiling, quarantine cap/escalation, per-test
timeouts, wall-clock budget, mutation cadence) live in `PARAMETERS.md` (sibling) — this
workspace's declared defaults, not universal constants. A consumer workspace
re-parameterizes there without forking this doctrine.

## Curation decision table (create / curate / flaky-event)

| Situation | Action |
|---|---|
| Writing a new test | Declare intent in the docstring (§A); pass the admission filter (§B); place at the cheapest detecting tier (§C) |
| Reviewing an existing test at task/release closure | Apply demotion (§D) for every LARGE that validated the feature; record the map |
| Reviewing a test as a deletion candidate | Walk the §E table; delete only with `file:line` evidence, only as a `qa-engineer` verdict |
| A test is reported flaky | Walk the §F table; quarantine + register the bug in the same act |
| A test's skip/quarantine is expired | Delete under criterion E(f) |

## References, never restatement

- Reservation and commit discipline for the agent executing a curation verdict: the
  `dadaia-task-manager` skill.
- Where the demotion map lands at closure: `dd-release-implement` (the closure steps'
  disposition block).
- Detection-quality scoring for drift audits: `dd-audit-project` Dimension E.
- Handoff emission for a steward verdict: `dadaia-handoff-emitter`.
