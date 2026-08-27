# LINEAGE.md — Phase 0 in Full

`SKILL.md` (sibling) — `dd-diagnose`. This is the **one** canonical
statement of the lineage window, the filter, and the diff-trust rule (D8, A7.2/A7.3).
FR14's audit pillar 1 **cites this section**, it never restates it — if the two ever
disagree, this file is stale and the disagreement is itself a defect to fix here.

## The window (stated once)

The window runs from the last `audited` milestone to `HEAD`: scan every
`RELEASE.jsonl` — the live release's, every archived release's under
`specs/releases/_archive/**`, and `releases_histo.jsonl` — for the newest `audited`
milestone; the window is `[that milestone's sha, HEAD]`. When no `audited` milestone
exists yet, the window is the whole file. `specs/releases/_ideas/**` is never scanned: a
Draft carries no `RELEASE.jsonl` to fold (D10/AS-7), so it can carry no milestone.

## The filter

A prior record matches when either holds:

- **`surface`** is an exact match — `surface` is a closed enum
  (`bug-record-v1.schema.json`), never a substring guess.
- **`component`** is a match — `component` stays free text (the `path#symbol` precision
  fine-key analysis needs), so this is judgement, not a string-equality check.

**The cap.** Read at most the **20 most recent matching records** in the window,
ordered by resolution date (newest first) — approximate this with the fixing commit's
own date: `resolved_commit`'s commit date when it is already filled, else the date of
the commit that last touched that record's line in `specs/bugs/BUGS.jsonl` (`git log -1
--format=%cI -S '"id": "<bug-id>"' -- specs/bugs/BUGS.jsonl`, or the equivalent for the
one-line-per-record shape actually on disk). Twenty is the number; a fixer who wants a
wider read runs the audit (FR14) instead of widening phase 0. At 3.2 bugs/day over a
five-release window an uncapped filter is 100–300 records per fix — the shape that turns
a procedure into a ritual nobody performs.

## What to read — and what to distrust

For each of the (up to 20) matching records, check `resolution_granularity` before
touching its diff:

| `resolution_granularity` | What it means | Action |
|---|---|---|
| `exact` | `resolved_commit` isolates exactly this record's own change | `git show <resolved_commit>` — a real diff; read it |
| `release-squash` | the sha is a whole-release merge; many bugs share it | **Distrust it.** Do not diff it as if it isolated this fix (D-A) |
| `ledger-only` | the sha is only a ledger-touching commit, or unknown | **Distrust it.** Same rule as `release-squash` |
| `null` | never derived | Treat as coarse; do not diff |

Diffing a `release-squash`/`ledger-only` sha and presenting it as "the fix" is exactly
the fabricated-evidence shape the standing architecture-review order exists to prevent —
say the sha is coarse instead of pretending the diff is the fix.

## Declare `caused_by`

After reading the matching records, write to **this bug's own record** (never to a
prior one):

```bash
dadaia bugs update <this-bug-id> --set caused_by=<prior-bug-id-or-none> \
  --set lineage_source=declared
```

`caused_by: none` carries the same evidentiary weight as naming a bug — it means the
prior diffs in the window were read and no causal link found, not that the check was
skipped. This mirrors the historical distinction the migration already draws: `null` =
never assessed, `"none"` = assessed and cleared (AS-2).

Echo the same declaration in the fix commit body — a real worked example, both bug ids
real records in `specs/bugs/BUGS.jsonl`:

```text
caused_by: codex-live-probe-gate-checks-presence-not-usability
evidence: git show <its resolution sha> added a second render path in the certify skip branch; this bug is that path emitting the raw transcript.
prior diffs read: codex-live-probe-gate-checks-presence-not-usability (exact), certify-cannot-install-installed-provider (ledger-only — not diffed, coarse)
```

`certify-cannot-install-installed-provider`'s own record carries
`resolution_granularity: "release-squash"` — the ledger's live example of a sha this
rule instructs you to distrust rather than diff.

## Cost bound

At most **20 records read, at most 20 `git show` calls, per fix.** This is a reading
discipline, not a mechanized scan — no CLI verb enforces the cap, no hook blocks a wider
read; the audit (FR14 pillar 1) is where the workspace measures how well the discipline
is actually followed, over time, across the fleet.

## Why this is not a hook or a CLI verb (D8/D15)

Phase 0 is a skill-carried procedure the fixer runs, not a gate anyone can be blocked
by. `dadaia bugs update` (AS-16) is a plain governance-field writer — it validates
nothing about lineage correctness and refuses nobody a resolution; it only rejects a
stale write or an attempt to touch an immutable-core field. Whether a fixer actually ran
phase 0, actually read the window, and declared an honest `caused_by` is measured
**after the fact**, by the audit — never enforced at write time.
