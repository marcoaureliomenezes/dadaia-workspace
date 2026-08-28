# LINEAGE.md — Phase 0 in Full

Sibling of `SKILL.md` (`dd-diagnose`). The one canonical statement of the lineage window, the filter, and the diff-trust rule (D8, A7.2/A7.3).
FR14's audit pillar 1 cites this section, never restates it — if the two disagree, this file is stale, fix it here.

## The window (stated once)

- The window runs from the last `audited` milestone to `HEAD`.
- Read the live release's `RELEASE.json` `audited` field, plus every archived release's own `audited` fact.
- Archived facts live in `releases/_archive/releases_histo.jsonl` (no per-release `RELEASE.json` survives archiving, FR5).
- The window is `[newest audited milestone's sha, HEAD]`; the whole file when no `audited` milestone exists yet.
- Never scan `specs/releases/_ideas/**` — a Draft carries no `RELEASE.json` (D10/AS-7), so it carries no milestone.

## The filter

- A prior record matches when `surface` is an exact match — a closed enum, never a substring guess.
- A prior record matches when `component` is a match — free text, judgement, not a string-equality check.
- Cap: read at most the 20 most recent matching records in the window, ordered by resolution date (newest first).
- Approximate the date via `resolved_commit`'s commit date when filled, else the last commit touching that record's line.
- Twenty is the number; a fixer wanting a wider read runs the audit (FR14) instead of widening phase 0.
- At 3.2 bugs/day over a five-release window, an uncapped filter is 100-300 records per fix — a ritual nobody performs.

## What to read — and what to distrust

| `resolution_granularity` | What it means | Action |
|---|---|---|
| `exact` | `resolved_commit` isolates exactly this record's own change | `git show <resolved_commit>` — a real diff; read it |
| `release-squash` | the sha is a whole-release merge; many bugs share it | Distrust it — do not diff it as if it isolated this fix (D-A) |
| `ledger-only` | the sha is only a ledger-touching commit, or unknown | Distrust it — same rule as `release-squash` |
| `null` | never derived | Treat as coarse; do not diff |

- Diffing a `release-squash`/`ledger-only` sha and presenting it as "the fix" is fabricated evidence.
- Say the sha is coarse instead of pretending the diff is the fix.

## Declare `caused_by`

1. After reading the matching records, write to this bug's own record (never a prior one).
2. Run `dadaia bugs update <this-bug-id> --set caused_by=<prior-bug-id-or-none> --set lineage_source=declared`.
3. `caused_by: none` carries the same evidentiary weight as naming a bug — it means the window was read, no link found.
4. This mirrors the migration's own distinction: `null` = never assessed, `"none"` = assessed and cleared (AS-2).
5. Echo the same declaration in the fix commit body, e.g.:

```text
caused_by: codex-live-probe-gate-checks-presence-not-usability
evidence: git show <its resolution sha> added a second render path in the certify skip branch; this bug is that path emitting the raw transcript.
prior diffs read: codex-live-probe-... (exact), certify-cannot-install-installed-provider (ledger-only — not diffed, coarse)
```

- `certify-cannot-install-installed-provider`'s own record carries `resolution_granularity: "release-squash"`.
- That is a live example to distrust rather than diff.

## Cost bound

- At most 20 records read, at most 20 `git show` calls, per fix.
- This is a reading discipline, not a mechanized scan — no CLI verb enforces the cap, no hook blocks a wider read.
- The audit (FR14 pillar 1) measures how well the discipline is followed, over time, across the fleet.

## Why this is not a hook or a CLI verb (D8/D15)

- Phase 0 is a skill-carried procedure the fixer runs, not a gate anyone can be blocked by.
- `dadaia bugs update` (AS-16) is a plain governance-field writer — validates nothing about lineage correctness.
- It only rejects a stale write or an attempt to touch an immutable-core field.
- Whether a fixer actually ran phase 0 and declared an honest `caused_by` is measured after the fact, by the audit.
