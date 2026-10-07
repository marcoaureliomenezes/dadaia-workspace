# What the bug ledger taught

Every bug this workspace has is one line in `specs/bugs/BUGS.jsonl`: one record per
bug, appended once, keyed by its id, with git history as that line's change log and no
git-derived fact in the record. Each record names its `surface`, its `component`, the
candidate it was found in, the evidence of its red loop, and its lineage: `caused_by`, the
bug or task whose fix wrote the lines this fix corrects. Whether the fix left the feature
smaller or larger is derived from its fix commits by `bugs.py fix`, never stored.

That last field is why the ledger reads as a history rather than a pile. Follow
`caused_by` and bug families appear — chains of records on the same surface, each one
the price of the previous fix.

## Measuring the ledger

<!-- derived-from: bug-ledger sha256:1f1d4608155e -->

The numbers are never copied into a page; the ledger's own verbs measure them.

```bash
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py stats
python3 .agents/skills/dd-bug-resolution/scripts/bugs.py status --all
```

`status` is `open | resolved | superseded | deferred | rejected`, and a terminal status
is reached only through its transition, each refusing an incomplete call: `resolve`
requires the red-loop evidence and a `caused_by` link checked against the blame of the
staged fix; `supersede`
names the record that replaces it; a reopen is a new record. Nothing is closed by
agreement.

## Lesson 1 — a per-caller fix breeds the next caller's bug

<!-- derived-from: context-management sha256:2d908837d9f6 -->
<!-- derived-from: bug-ledger sha256:1f1d4608155e -->

When a guard lives at the caller that was just caught, the next caller without it is
the next bug in the family, and each such fix is `net-positive`: it grows the feature.
The structure that ends the family is one guarded seam every writer delegates to. The
context registry is the example: a repo slug belongs to one context, and `create`,
`repo add` and `.dadaia/.venv/bin/dadaia import` pass one ownership check; `INV-6` reports any
multi-owner slug already on disk.

## Lesson 2 — a per-measurement exclusion breeds the next measurement's bug

<!-- derived-from: QUALITY sha256:73c99333cf6b -->

When each measurement walks the tree itself and is fixed by its own special-case
exclusion, the next measurement counts the same stray files. The structure that ends
the family is one enumeration: every guard check enumerates the same set —
`scripts/guards/run.py`'s `tracked()` over `git ls-files` — so a scratch file another
process writes is outside the measurement by construction, not by a list somebody has
to remember to extend.

## Lesson 3 — a derived cache breeds a bug per environment that derives it

<!-- derived-from: bug-ledger sha256:1f1d4608155e -->
<!-- derived-from: QUALITY sha256:73c99333cf6b -->

A record that caches a fact git already knows is wrong in every environment that
derives it differently — a shallow checkout first among them. The structure that ends
the family is deleting the cache: a bug record carries no git-derived fact, and git
history is that line's change log. No CI job fetches history for a bug record's sake.

## The standing order the lessons produced

<!-- derived-from: QUALITY sha256:73c99333cf6b -->
<!-- derived-from: bug-ledger sha256:1f1d4608155e -->

The workspace is in a permanent state of architecture review, oriented by its bug
history:

- Read the ledger before proposing a fix. Resolution opens with lineage over at most
  the 20 most recent records sharing this bug's surface or component, and the link is
  declared at resolution as `caused_by: <bug-id> | <task-id> | none`, picked from the
  blame candidates; a unit with two or more prior
  fixes is rebuilt, never patched a third time.
- Prefer the deletion-shaped fix. A fix whose diff grows the touched feature is routed
  to the architecture lens before it lands.
- Record the direction. Every review verdict states the bug-surface delta from
  `bugs.py stats` — "tests green" is not a verdict.
- Let ratchets refuse growth. Private-symbol imports in tests (P-23) and the slop
  counts are pinned at their measured values and move downward only.
- Keep one home per definition (V37).

Next: [the bug loop](bug-loop.md) — register, RED, fix, resolve, in commands. Or start
at the [quickstart](quickstart.md).
