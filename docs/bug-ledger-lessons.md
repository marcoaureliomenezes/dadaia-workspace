# What the bug ledger taught

Every bug is one record in `specs/bugs/BUGS.jsonl`, appended once and keyed by id. The
record keeps product facts: where the defect appeared, what contract failed and, after
resolution, its `cause`, `solution`, `caused_by` and `fix_sha`. Git remains the history
of that line and the authority for the implementation diff.

`caused_by` turns the ledger into a navigable history. Follow it and bug families appear:
each link says which prior bug or task wrote the lines corrected by the later fix. Inspect
the persisted `fix_sha` to see what actually changed.

## Measuring the ledger

The ledger verbs report current counts without copying them into prose:

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --all
```

Current bug status is `open | resolved | superseded | rejected`. A terminal status is
written only by its transition. `resolve` requires the diagnosed cause, implemented
solution, lineage link and 40-hex fix sha; `supersede` names the replacement; `reject`
records the reason. A reopen is a new record.

Candidate maturity is not stored on the bug. The next candidate's `SPEC.md`
`## Bug window review` records KEEP or REBUILD: one KEEP leaves the first-level window;
a REBUILD leaves after its tested replacement and a following candidate with no child
bug. The release summary owns delivered, carried and backlog-exit scope.

## Lesson 1 — a per-caller fix breeds the next caller's bug

When a guard lives at only the caller that was caught, the next unguarded caller becomes
the next bug. The structure that ends the family is one deep module every writer uses.
The context registry is the example: `create`, `repo add` and import share one ownership
check, and `INV-6` reports a slug owned by more than one context.

## Lesson 2 — a per-measurement exclusion breeds another measurement bug

When each measurement walks the tree independently, each acquires its own exclusions.
One enumeration restores locality: guard checks operate on the same tracked-file set, so
scratch output is outside the measurement by construction.

## Lesson 3 — a derived cache breeds an environment-specific bug

A ledger field that caches a fact available from git becomes wrong wherever history has a
different shape, especially in a shallow checkout. Persist the `fix_sha`; derive numstat,
direction and maturity from the named commit and the bug-window review when needed.

## Standing order

- Read the matching ledger history before proposing a fix. Inspect at most the 20 most
  recent records and their named fix commits.
- Use `caused_by: <bug-id> | <task-id> | none`; choose `none` only when blame offers no
  candidate. Two prior fixes on the touched module require a REBUILD.
- Prefer a deletion-shaped fix. If the production diff grows, route it through the
  architecture lens.
- Derive the bug-surface delta from `git show <fix_sha>` and report it in review evidence.
- Keep one home per definition and let ratchets move downward.
- Treat an eval BLOCK as a contract failure to diagnose, not a verdict to waive.

Next: [the bug loop](bug-loop.md), or start at the [quickstart](quickstart.md).
