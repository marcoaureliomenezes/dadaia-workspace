# What the bug ledger taught

Every bug this workspace ever had is one line in `specs/bugs/BUGS.jsonl`: one record
per bug, appended once, keyed by its id, with git history as that line's change log.
There is no event store and no derived cache — a record's mutable governance fields are
rewritten in place, its seven git-derived provenance keys were retired, and git stays
the only authority for git facts. Each record names its `surface`, its `component`, the
evidence of its RED loop and its seam test, whether the fix left the feature smaller or
larger (`diff_direction`), and its lineage: `caused_by`, the id of the bug whose fix
made this one possible.

That last field is why the ledger is readable as a history rather than a pile. Follow
`caused_by` and bug families appear — chains of three, four, five records on the same
surface, each one the price of the previous fix.

## The counts at the 0.4.7 closure

<!-- derived-from: sdd-bug-backlog-governance sha256:753748a55aa3 -->

A snapshot, not a live figure: these are the numbers the ledger held when release 0.4.7
closed. Re-measure them at any time with the ledger's own `stats` verb.

| Status | Records |
|---|---|
| resolved | 497 |
| superseded | 9 |
| rejected | 5 |
| deferred | 3 |
| **total** | **514** |

| Severity | Records |
|---|---|
| CRITICAL | 38 |
| HIGH | 231 |
| MEDIUM | 157 |
| LOW | 88 |

`resolved` is the only status that requires a regression seam. A sweep closure is
`superseded`; a reopen is a new record declaring `caused_by`. Nothing is closed by
agreement.

## Lesson 1 — a per-caller fix breeds the next caller's bug

<!-- derived-from: sdd-bug-backlog-governance sha256:753748a55aa3 -->

Four records, one missing guard. `context-alive-sweeps-unrelated-worktree-changes`
(MEDIUM) →  `context-repo-add-accepts-foreign-context-slug` (HIGH) →
`context-create-accepts-slug-owned-by-another-context` (HIGH) →
`import-registers-unvalidated-slugs-that-doctor-fix-inv5-rmtrees` (HIGH). The slug
allowlist lived in the CLI command module; the foreign-owner refusal lived inside the
service. Each fix added the check at the caller that had just been caught, so the third
writer — the import path — inserted an unvalidated slug, and the repair sweep deleted a
directory on it. The first three fixes are recorded `net-positive`: they grew the
feature. The fourth is `net-negative`: it gave registry insertion one guarded seam and
had every writer delegate to it. The family stopped there.

## Lesson 2 — a per-measurement exclusion breeds the next measurement's bug

<!-- derived-from: QUALITY sha256:0355c414bb59 -->

Four records, one enumeration.
`no-ratchet-against-frozen-clock-tests-that-age-fixtures-by-the-real-clock` (LOW) →
`frozen-clock-ratchet-scans-tests-tmp-scratch-dir` (LOW) →
`v26-ratchet-scans-tests-tmp-scratch-dir-xdist-race` (MEDIUM) →
`tests-tree-walkers-outside-the-ratchets-still-race-the-xdist-quarantine-probe`
(MEDIUM). Each ratchet walked the test tree itself, so each in turn counted scratch
files a concurrent worker had written, and each was fixed by a special-case exclusion
of its own. The fix that ended it deleted those exclusions: every suite ratchet now
enumerates one set, tracked files only, and a scratch file is outside the measurement
by construction rather than by a list somebody has to remember to extend.

## Lesson 3 — a derived cache breeds a bug per environment that derives it

<!-- derived-from: sdd-bug-backlog-governance sha256:753748a55aa3 -->

Bug records once cached facts git already knew, among them the commit that resolved
them. `contract-coverage-ci-shallow-checkout-collapses-resolved-commit-derivation-to-head`
(HIGH) was the shallow CI checkout collapsing that derivation onto the head commit; its
fix deepened the checkouts, and `release-workflow-shallow-checkout-...` (HIGH) arrived
with the next workflow that had not been deepened. Both are `net-positive`. What ended
the family was deleting the cache: the seven provenance keys are retired, the loader
ignores exactly those keys, the serializer never emits them, and `dadaia doctor --fix`
strips one from any record still carrying it. A field that cannot be stale cannot be
derived wrong.

## The standing order the lessons produced

<!-- derived-from: QUALITY sha256:0355c414bb59 -->
<!-- derived-from: sdd-bug-backlog-governance sha256:753748a55aa3 -->

The workspace is in a permanent state of architecture review, oriented by its bug
history:

- Read the ledger before proposing a fix. Diagnosis opens with a lineage duty over the
  recent records sharing this bug's surface or component, and the link is declared at
  resolution as `caused_by: <bug-id> | none`, with evidence.
- Prefer the deletion-shaped fix. A correct fix usually removes a branch, collapses two
  paths into one, or moves logic back inside the module that owns it. A fix that adds a
  flag, a wrapper, a second code path or a per-caller check is how a family grows.
- Record the direction. Every resolution states whether the diff left the feature
  smaller or larger, and every review verdict states the bug-surface delta — "tests
  green" is not a verdict.
- Let numbers refuse growth. Module size, complexity, nesting, private-symbol imports
  in tests and the slop counts are pinned at their measured values and move downward
  only; each raise is justified in the closure record that raises it.
- Keep one home per number. Two homes for one parameter guarantee two different values.

Next: [the bug loop](bug-loop.md) — register, RED, fix, resolve, in commands. Or start
at the [quickstart](quickstart.md).
