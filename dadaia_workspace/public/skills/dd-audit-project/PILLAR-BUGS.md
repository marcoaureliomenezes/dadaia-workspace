# PILLAR-BUGS — bug-history forensics

Disclosed sibling of `SKILL.md`, pillar 1. Input: every `BUGS.jsonl` record whose registration/resolved commit falls inside the window.
Window definition: `SKILL.md`'s window section.

- Only shas carrying `resolution_granularity == "exact"` are diff-able lineage — never `commit_granularity`, which is not a field.
- A `release-squash`/`ledger-only`/`null` sha is counted, never diffed (`dd-bug-resolution`'s `LINEAGE.md` table applies identically here).

## Recurrence and fix-induced bugs — operational, not adjectival (A14.3)

- Recurrence: a later record whose `surface` matches an earlier, resolved record's `surface`, registered after that record's resolution date.
- Recurrence: group by `surface` (the closed enum), never by a `component` substring guess.
- Fix-induced bug: a later record whose `refs`/`component` names a file the earlier resolution's diff touched.
- Fix-induced bug: the later record's `caused_by` must name the earlier one; a contradicted `caused_by: none` is itself a finding.
- Both definitions are computable from `BUGS.jsonl` + `git show` alone — no further judgement about what counts.

## The eight forensic metrics (verbatim from SPEC FR14 — each row is a validation, V33)

A pillar-1 run reporting fewer than eight is incomplete, not lenient (A14.7).
Metrics 7 and 8 carry `target 0` and report their measured value even when worse than baseline.

| # | Metric | Definition / command | Baseline | Record field |
|---|---|---|---|---|
| 1 | Per-bug diff attributability | 1st-adding commit adds 1 record, non-`specs/` | 26/92 = 28% | `resolution_granularity=="exact"`; target 100% |
| 2 | FR23 triple coverage | resolved records with the evidence triple all present | 23/92 = 25% | the restored triple; target 100% |
| 3 | Fix-shape ratio | `net-negative / (net-neutral + net-positive)` | 21/31 = 0.68 | `diff_direction` |
| 4 | Same-surface re-bug rate at 3d/14d | grouped on the `surface` enum, never free text | 55% / 73% | `surface` |
| 5 | Hand-kept-list touch count | resolving commits touching the fixed path set below | 16/83 | fixed path set, below |
| 6 | Test-layer bug share | records whose `surface == "tests"` or `component` starts with `tests/` | 21/100 | `surface` |
| 7 | Scanner-vs-prose recurrence | scanner-term symptom AND fix touches only docs/tests | 10/100, target 0 | reported honestly, not hidden |
| 8 | Sweep closures as `resolved` | terminal records with no code-touching commit | 9/92, target 0 | a sweep is `superseded`, never `resolved` |

- Metric 5's fixed path set (FR10A owns relocating it): `.gitignore`, `privacy_baseline.json`, `shipped-hashes.json`.
- Fixed path set (continued): `*_golden/*.json`, a skill roster file, a `frozenset({...})` literal.

## Three cheap measures (beyond the eight)

- Registration-to-resolution interval: diff the resolved commit's date against the record's `ts`.
- An implausibly short interval is the no-red-loop signature.
- Worked example: `certify-cannot-install-installed-provider` reported 18:41:56Z, resolved 18:41:57Z, one second.
- Core-field mutation: a hunk changing an immutable-core field (per the schema's `x-mutability`) of an existing `id` is a HIGH finding.
- Cache disagreement: a stored `resolved_commit` disagreeing with the FR8 resolver's derivation is a finding (A8.2).

## Per-record checks (beyond the eight metrics)

- A resolved record carrying no `cause`, or no `evidence_seam` (no regression seam).
- A `diff_direction: net-positive` record whose resolving commit shows no `software-architect` routing evidence (`DADAIA.md` §7).
- Bug-scoped commit-shape conformance: shapes 1 (registration) and 3 (fix) of `dd-gitflow-default` §3a, read from `git log`.
- The full five-shape sweep is `PILLAR-SPECS.md`'s — never duplicated here.

## Pillar 1 is the single writer of the derived cache (A14.6)

1. On each record reviewed, write `audited: <audit-slug>` and the four derived provenance fields in one atomic rewrite.
2. Provenance fields: `registration_commit`, `registration_granularity`, `resolved_commit`, `resolution_granularity`.
3. Use the FR2 seam only: `dadaia bugs update <bug-id> --set audited=<slug> --set registration_commit=<sha> ...`.
4. One writer, one seam, one commit per rewritten record batch — this is what AS-1(ii) buys; FR8 has no shape 3b.
5. A record whose derivation cannot be resolved carries `null`, which is correct, not a failure (A8.2).
