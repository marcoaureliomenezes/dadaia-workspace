# LINEAGE.md — Phase 0 in Full

Sibling of `SKILL.md` (`dd-bug-resolution`, Phase 0). The one canonical statement of the lineage window, the filter, and the diff-trust rule.
The audit's pillar 1 cites this section, never restates it — if the two disagree, this file is stale, fix it here.

## The window (stated once)

- The window runs from the newest archived audit to `HEAD`.
- Read `specs/audits/_archive/audits_histo.jsonl` — an audit is not a release milestone.
- A shipped release survives whole under `releases/_archive/<v>/` (ADR 0152 (1)); its `_RELEASE.json` `shipped` holds the sha and PR.
- The window is `[newest archived audit's sha, HEAD]`; the whole file when that histo is empty.
- An audit record missing its sha: recover it with `git log -S <audit-id> -- specs/audits`.

## The filter

- A prior record matches when `surface` is an exact match — a closed enum, never a substring guess.
- A prior record matches when `component` is a match — free text, judgement, not a string-equality check.
- Cap: read at most the 20 most recent matching records in the window, ordered by `closed_at` (newest first).

## What to read — and what to distrust

- A record carries no commit sha; `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py fix <bug-id>` prints its fix commits (shape 3 or shape 4) and their numstat, or `unlinked`.
- A release-squash or ledger-only commit isolates nothing — say the trail is coarse instead of presenting it as "the fix".
- Presenting a coarse diff as the prior fix is fabricated evidence.

## Declare `caused_by`

1. After reading the matching records, declare the link on this bug's own record — never on a prior one.
2. Stage the fix first: `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py resolve <id> --caused-by <prior-bug-id>|none` blames the lines the staged diff removes, past commits whose subject ends `(#n)` or starts `refactor(T-`, never in `tests/`, `specs/` or a file `.gitattributes` marks `dadaia-generated`.
3. `resolve` refuses a `--caused-by` outside those candidates, and `none` when any exist, unless `--lineage-reason "<why>"` is given; the reason is stored.
4. `caused_by: X` means the fix of X wrote the lines this fix corrects; `bugs.py update <id> --set caused_by=…` repairs it; every write and `check` refuse a target naming no live or archived record, and a loop.
5. Echo the declaration in the fix commit body: `caused_by:`, `evidence:` (what the prior diff did), `prior diffs read:`.
6. ≥ 2 prior fixes on the unit the bug lands in, within the window, make this fix a REBUILD of that unit — never a third patch.
7. This step is the one producer of the fix commit body's REBUILD line: `rebuild: <unit> — prior fixes <id>, <id>`, or, only when `caused_by` is `none`, `rebuild: none — <reason>`; any other `caused_by` makes the fix a REBUILD of the unit, keeping its tests (0210); a rebuild's `--solution` opens with `REBUILD <unit>:`.

## Cost bound

- At most 20 records read, at most 20 `git show` calls, per fix; a wider read is the audit's (`dd-audit-project`).
- This is a reading discipline, not a mechanized scan — no CLI verb enforces the cap, no hook blocks a wider read.
- The audit (pillar 1) measures how well the discipline is followed, over time, across the fleet.
