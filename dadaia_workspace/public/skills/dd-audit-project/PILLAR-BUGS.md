# PILLAR-BUGS — bug-history forensics

Disclosed sibling of `SKILL.md`, pillar 1. Input: every `BUGS.jsonl` record whose `ts` or `closed_at` falls inside the window.
Window definition: `SKILL.md` §1.

- A record carries no commit sha: attribute a fix by `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py fix <bug-id> --specs <specs-dir>`.
- `bugs.py fix` diffs every linked commit, a shape-4 task commit included, and prints each fix's rework by class and its settled surface; a release-squash or ledger-only commit is no fix and stays unlinked.

## Recurrence and fix-induced bugs — operational, not adjectival

- Recurrence: a later record whose `surface` matches an earlier, resolved record's `surface`, registered after that record's resolution date.
- Recurrence: group by `surface` (the closed enum), never by a `component` substring guess.
- Fix-induced bug: a later record whose `component` names a file the earlier resolution's diff touched.
- Fix-induced bug: the later record's `caused_by` must name the earlier one; a contradicted `caused_by: none` is itself a finding.
- Both definitions are computable from `BUGS.jsonl` + `git show` alone — no further judgement about what counts.

## The nine forensic metrics — each row is a validation

A pillar-1 run reporting fewer than nine is incomplete, not lenient.
Each metric reports the window's measured value against the previous audit's, read from `audits_histo.jsonl`.
Metrics 7 and 8 carry `target 0` and report their measured value even when it worsened.

| # | Metric | Definition / command | Record field |
|---|---|---|---|
| 1 | Registrations per reporter | the window's records grouped by `reported_by` | `reported_by`; a reporter registering many is the ask-first rule breaking |
| 2 | Red-loop coverage | resolved records carrying `evidence_loop` | `evidence_loop`; target 100% |
| 3 | Fix-shape ratio | `net-negative / (net-neutral + net-positive)` (`bugs.py stats`' `direction:` rows) | every linked fix commit's production numstat (`bugs.py fix`) |
| 4 | Same-surface re-bug rate at 3d/14d | grouped on the `surface` enum, never free text | `surface` |
| 5 | Hand-kept-list touch count | resolving commits touching the fixed path set below | fixed path set, below |
| 6 | Test-layer bug share | records whose `surface == "tests"` or `component` starts with `tests/` | `surface` |
| 7 | Scanner-vs-prose recurrence | scanner-term symptom AND fix touches only docs/tests | target 0, reported honestly |
| 8 | Sweep closures as `resolved` | terminal records with no code-touching commit | target 0; a sweep is `superseded`, never `resolved` |
| 9 | REBUILD share of linked fixes | resolved records with `caused_by` ≠ `none` whose fix carries a REBUILD: a `refactor(…): … REBUILD` subject or `REBUILD` in a `fix(bugs):` subject (121ae02b2 counts); `rebuild: none — <reason>` is valid only beside `caused_by: none` | `caused_by`; target 100 %, gates nothing (0210) |

- Metric 5's fixed path set: `.gitignore`, `privacy_baseline.json`, `shipped-hashes.json`.
- Fixed path set (continued): `*_golden/*.json`, a skill roster file, a `frozenset({...})` literal.

## Two cheap measures (beyond the nine)

- Registration-to-resolution interval: diff `closed_at` against the record's `ts`; a seconds-long interval is the no-red-loop signature.
- Core-field mutation: a hunk changing an immutable-core field (per the schema's `x-mutability`) of an existing `id` is a HIGH finding.

## Per-record checks (beyond the nine metrics)

- A resolved record carrying no `cause`.
- A `net-positive` record (`bugs.py fix`) whose resolving commit shows no architecture-lens routing evidence (`dd-code-review`).
- Bug-scoped commit-shape conformance: shapes 1 (registration) and 3 (fix) of `dd-gitflow-default` §3a, read from `git log`.
- The full five-shape sweep is `PILLAR-SPECS.md`'s — never duplicated here.

## Pillar 1's one write

- On each record reviewed, stamp `audited: <audit-slug>` through `python3 .agents/skills/dd-bug-resolution/scripts/bugs.py update <bug-id> --set audited=<slug>`.
- One writer, one seam, one commit per rewritten record batch.
