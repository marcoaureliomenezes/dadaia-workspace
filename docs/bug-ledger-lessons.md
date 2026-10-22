# What the bug ledger taught

Every bug is one record in `specs/bugs/BUGS.jsonl`, appended once and keyed by id. The
record keeps product facts: where the defect appeared, what contract failed and, after
resolution, its `cause`, `solution`, `caused_by` and `fix_sha`. Git remains the history
of that line and the authority for the implementation diff.

`caused_by` turns the ledger into a navigable history. Follow it and bug families appear:
each link says which prior bug or task wrote the lines corrected by the later fix. Inspect
the fix commit, found by its `fix(bugs)` or `refactor(bugs)` id line, to see what actually changed.

## Measuring the ledger

The ledger verbs report current counts without copying them into prose:

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --all
```

Current bug status is `open | resolved | superseded | rejected`. A terminal status is
written only by its transition; each transition's flags are `bugs.py <verb> --help`. A
reopen is a new record.

Candidate maturity is not stored on the bug. The next candidate's `SPEC.md`
`## Bug window review` judges each fix and never schedules work; the window rule is in
`dd-bug-resolution/LINEAGE.md`, and the review step is in `dd-release-definition/SKILL.md`,
section 1, step 7. The release summary's scope is in
`dd-release-implementation/RELEASE-EVENTS.md`.

## Lesson 1 — a per-caller fix breeds the next caller's bug

When a guard lives at only the caller that was caught, the next unguarded caller becomes
the next bug. The structure that ends the family is one deep module every writer uses.
The context registry is the example: `create`, `repo add` and `init --from` share one ownership
check, and `INV-6` reports a slug owned by more than one context.

## Lesson 2 — a per-measurement exclusion breeds another measurement bug

When each measurement walks the tree independently, each acquires its own exclusions.
One enumeration restores locality: guard checks operate on the same tracked-file set, so
scratch output is outside the measurement by construction.

## Lesson 3 — a derived cache breeds an environment-specific bug

A ledger field that caches a fact available from git becomes wrong wherever history has a
different shape, especially in a shallow checkout. Find the fix by its id line, with the
write-once `fix_sha` only a hint a rewrite may orphan; derive numstat and direction from that
commit.

## Standing order

- Read the matching ledger history before proposing a fix, within the cap that
  `dd-bug-resolution/LINEAGE.md` sets.
- Use `caused_by: <bug-id> | <task-id> | none`; choose `none` only when blame offers no
  candidate. A REBUILD is due as `bugs.py append` prints it.
- Prefer a deletion-shaped fix. If the production diff grows, route it through the
  architecture lens.
- Derive the bug-surface delta from `git show` of the fix commit, found by its `fix(bugs)` or `refactor(bugs)` id line, and report it in review evidence.
- Keep one home per definition and let ratchets move downward.
- Treat an eval BLOCK as a contract failure to diagnose, not a verdict to waive.

Next: [the bug loop](bug-loop.md), or start at the [quickstart](quickstart.md).
