# LINEAGE.md — Phase 0 in Full

Sibling of `SKILL.md` (`dd-bug-resolution`, Phase 0). The one canonical statement of the lineage window, the filter, and the diff-trust rule.
The audit's pillar 1 cites this section, never restates it — if the two disagree, this file is stale, fix it here.

## The window (stated once)

- The window runs from the newest archived audit to `HEAD`.
- Read `specs/audits/_archive/audits_histo.jsonl` — an audit is not a release milestone.
- Archived facts live in `releases/_archive/releases_histo.jsonl` (no per-release `_RELEASE.json` survives archiving).
- The window is `[newest archived audit's sha, HEAD]`; the whole file when that histo is empty.

## The filter

- A prior record matches when `surface` is an exact match — a closed enum, never a substring guess.
- A prior record matches when `component` is a match — free text, judgement, not a string-equality check.
- Cap: read at most the 20 most recent matching records in the window, ordered by `closed_at` (newest first).

## What to read — and what to distrust

- A record carries no commit sha; find the fix by `git log -S<bug-id> -- specs/bugs/BUGS.jsonl` and read the commit it names.
- A release-squash or ledger-only commit isolates nothing — say the trail is coarse instead of presenting it as "the fix".
- Presenting a coarse diff as the prior fix is fabricated evidence.

## Declare `caused_by`

1. After reading the matching records, declare the link on this bug's own record — never on a prior one.
2. `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <id> --caused-by <prior-bug-id>|none` is the one writer; it is validated against the ledger or the literal `none`.
3. `caused_by: none` carries the same evidentiary weight as naming a bug — the window was read, no link found.
4. Echo the declaration in the fix commit body: `caused_by:`, `evidence:` (what the prior diff did), `prior diffs read:`.
5. ≥ 2 prior fixes on the unit the bug lands in, within the window, make this fix a REBUILD of that unit — never a third patch.
6. Echo `rebuild: <unit> — prior fixes <id>, <id>` (or `rebuild: none`); a rebuild's `--solution` opens with `REBUILD <unit>:`.

## Cost bound

- At most 20 records read, at most 20 `git show` calls, per fix; a wider read is the audit's (`dd-audit-project`).
- This is a reading discipline, not a mechanized scan — no CLI verb enforces the cap, no hook blocks a wider read.
- The audit (pillar 1) measures how well the discipline is followed, over time, across the fleet.
