# PILLAR-BUGS — bug-history forensics

Disclosed sibling of `SKILL.md`, pillar 1. Input: every `specs/bugs/BUGS.jsonl` record
whose `registration_commit` or `resolved_commit` falls inside the audit window
(`SKILL.md`'s window section). Only shas carrying `resolution_granularity == "exact"`
(**never** `commit_granularity`, which is not a field) are diff-able lineage — a
`release-squash`/`ledger-only`/`null` sha is counted, never diffed (`dd-diagnose`'s
`LINEAGE.md` "What to read — and what to distrust" table applies identically here).

## Recurrence and fix-induced bugs — operational, not adjectival (A14.3)

- **Recurrence.** A later record whose `surface` (the closed enum) matches an earlier,
  resolved record's `surface`, registered after that earlier record's resolution date
  (`resolved_commit`'s `git log -1 --format=%cI <sha>`, once derived) — group by
  `surface`, never by a `component` substring guess.
- **Fix-induced bug.** A later record whose `refs`/`component` names a file the earlier
  resolution's diff touched (`git show <resolved_commit> --name-only`). The **later**
  record's `caused_by` must then name the earlier one; a `caused_by: none` on the later
  record that the diff nonetheless contradicts is itself a finding.

Both definitions are computable from `BUGS.jsonl` + `git show` alone — no further
judgement about what counts.

## The eight forensic metrics (verbatim from SPEC FR14 — each row is a validation, V33)

A pillar-1 run reporting fewer than eight is **incomplete, not lenient** (A14.7). Metrics
7 and 8 carry `target 0` and report their measured value even when it is worse than
baseline — metric 7 is *expected* to be worse this release, and saying so is the
acceptance.

| # | Metric | Definition / command | Baseline | Record field |
|---|---|---|---|---|
| 1 | Per-bug diff attributability | share of resolutions whose first-adding commit adds exactly one resolved record and touches a non-`specs/` path | 26/92 = 28 % | `resolution_granularity == "exact"`; target 100 % on post-0.5.0 resolutions |
| 2 | FR23 triple coverage | resolved records with `evidence_loop` + `evidence_seam` + `evidence_diff` all present | 23/92 = 25 % | the restored triple; target 100 % post-0.5.0 |
| 3 | Fix-shape ratio | `net-negative / (net-neutral + net-positive)` | 21/31 = 0.68 | `diff_direction` |
| 4 | Same-surface re-bug rate at 3 d / 14 d | grouped on the `surface` enum, never free text | 55 % / 73 % | `surface` |
| 5 | Hand-kept-list touch count | resolving commits whose `git show --name-only` touches `.gitignore`, `privacy_baseline.json`, `shipped-hashes.json`, `*_golden/*.json`, a skill roster, or a `frozenset({…})` literal | 16/83 | fixed path set, below |
| 6 | Test-layer bug share | records whose `surface == "tests"` or `component` starts with `tests/` | 21/100 | `surface` |
| 7 | Scanner-vs-prose recurrence | records whose `symptom` matches `self-scan\|denylist\|privacy` **and** whose fix touches only `specs/**/*.md` or `tests/` | 10/100, **target 0** — expected worse this release (prose growth: audits, migration report, `AGENTS.md`) | reported honestly, not hidden |
| 8 | Sweep closures as `resolved` | terminal records whose evidence matches `^Need met\|re-affirmation` with no code-touching commit | 9/92, **target 0** | a sweep is `superseded`, never `resolved` (FR2) |

Metric 5's fixed path set (FR10A owns relocating it, not this skill): `.gitignore`,
`privacy_baseline.json`, `shipped-hashes.json`, `*_golden/*.json`, a skill roster file, a
`frozenset({…})` literal.

## Three cheap measures (beyond the eight)

- **Registration→resolution interval.** Once a record's `resolved_commit` is derived
  (below), diff its commit date against the record's own `ts`. An implausibly short
  interval is the no-red-loop signature — the ledger's own worked example:
  `certify-cannot-install-installed-provider` reported 18:41:56Z, resolved 18:41:57Z,
  one second. Detecting the certify class becomes arithmetic, not judgement.
- **Core-field mutation.** A hunk in `git log -p -- specs/bugs/BUGS.jsonl` that changes
  an **immutable-core** field (per `bug-record-v1.schema.json`'s `x-mutability`) of an
  existing `id` is a **HIGH** finding — the detector that makes the seam's immutability
  rule auditable, since nothing at write time prevents a raw file-tool rewrite.
- **Cache disagreement.** A stored `resolved_commit` that disagrees with the FR8
  resolver's derivation is a finding (A8.2).

## Per-record checks (beyond the eight metrics)

- A resolved record carrying no `cause`, or no `evidence_seam` (no regression seam).
- A `diff_direction: net-positive` record whose resolving commit shows no
  `software-architect` routing evidence (`DADAIA.md` §7).
- Bug-scoped commit-shape conformance — shapes 1 (registration) and 3 (fix) of
  `dd-gitflow-default` §3a, read from `git log --format --stat` over the window; the
  full five-shape sweep is `PILLAR-SPECS.md`'s (never duplicated here).

## Pillar 1 is the single writer of the derived cache (A14.6)

On each record reviewed, write `audited: <audit-slug>` **and** the four derived
provenance fields — `registration_commit`, `registration_granularity`,
`resolved_commit`, `resolution_granularity` — in **one** atomic rewrite, through the
FR2 seam:

```bash
dadaia bugs update <bug-id> \
  --set audited=<audit-slug> \
  --set registration_commit=<sha> --set registration_granularity=<exact|release-squash|ledger-only> \
  --set resolved_commit=<sha> --set resolution_granularity=<exact|release-squash|ledger-only>
```

One writer, one seam, one commit per rewritten record batch — this is what AS-1(ii)
buys, and it is why FR8 has no shape 3b. A record whose derivation cannot be resolved
carries `null`, which is correct, not a failure (A8.2).
