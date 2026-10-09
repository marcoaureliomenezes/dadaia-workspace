# PILLAR-BUGS — bug-history forensics

Disclosed sibling of `SKILL.md`, pillar 1. The lineage window and filter live in
`dd-bug-resolution/LINEAGE.md`. Input is every bug record whose `ts` or `closed_at`
falls inside that window.

## Resolution evidence

- A resolved record persists `cause`, `solution`, `caused_by` and `fix_sha`.
- Inspect a fix with `git show <fix_sha> --stat --patch`. Report a missing commit or a
  release-squash trail as coarse evidence instead of inventing attribution.
- Derive diff direction from the named commit's production numstat. Direction is an
  audit result, not a ledger field.
- Read the prior candidate's `SPEC.md` `## Bug window review` for the maturity verdict.
  The release summary owns delivered, carried and backlog-exit scope; pillar 1 does not
  reconstruct that scope from retired bug fields.

## Recurrence and fix-induced bugs

- Recurrence is a later record on the same exact `surface`, registered after the earlier
  record's resolution.
- A fix-induced bug is a later record whose component names a file touched by the earlier
  record's `fix_sha`, with `caused_by` naming that earlier bug.
- A contradicted `caused_by: none` is a finding.

## The nine forensic metrics

A pillar-1 run reporting fewer than nine is incomplete. Each metric reports the window's
value against the previous audit from `audits_histo.jsonl`. Metrics 7 and 8 have target 0.

| # | Metric | Definition / evidence |
|---|---|---|
| 1 | Registrations per reporter | group records by `reported_by` |
| 2 | Complete resolutions | resolved records carrying `cause`, `solution`, `caused_by` and `fix_sha` |
| 3 | Fix-shape ratio | `net-negative / (net-neutral + net-positive)` from `git show --numstat <fix_sha>` on production paths |
| 4 | Same-surface re-bug rate at 3d/14d | group on exact `surface` |
| 5 | Hand-kept-list touch count | named fix commits touching the fixed path set below |
| 6 | Test-layer bug share | `surface == "tests"` or `component` starts with `tests/` |
| 7 | Scanner-vs-prose recurrence | scanner-term symptom and a fix touching only docs/tests |
| 8 | Sweep closures as `resolved` | resolved records whose `fix_sha` touches no production code |
| 9 | REBUILD share | resolved records with `caused_by != none` whose named fix commit identifies a REBUILD |

Metric 5's fixed path set is `.gitignore`, `privacy_baseline.json`,
`shipped-hashes.json`, `*_golden/*.json`, skill-roster files and literal
`frozenset({...})` inventories.

## Additional checks

- Compare `closed_at` with `ts`; an unusually short interval is a prompt to inspect the
  actual RED/GREEN history.
- Treat a hunk changing an immutable-core field on an existing id as HIGH.
- Report any resolved record missing `cause`, `solution` or a valid `fix_sha`.
- Check bug registration and fix commit shapes against `dd-gitflow-default` §3a.

## Pillar 1 output

Pillar 1 appends findings with reproducible commands and results. Bug records remain
product facts; audit coverage is established by the audit record and git history rather
than a marker copied into every bug.
