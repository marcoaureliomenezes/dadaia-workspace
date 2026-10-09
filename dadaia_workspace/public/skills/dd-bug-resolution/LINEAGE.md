# LINEAGE.md — Phase 0 in Full

Sibling of `SKILL.md` (`dd-bug-resolution`, Phase 0). The canonical statement of the
lineage window, filter and diff-trust rule. The audit's bug pillar cites this file instead
of repeating it.

## The window

- The window runs from the newest archived audit to `HEAD`.
- Read `specs/audits/_archive/audits_histo.jsonl`; an audit is not a release milestone.
- A shipped release survives under `releases/_archive/<v>/`; its `_RELEASE.json`
  `shipped` field holds the sha and PR.
- The window is `[newest archived audit sha, HEAD]`, or the whole history when the audit
  history is empty.
- Recover a historical audit record missing its sha with
  `git log -S <audit-id> -- specs/audits`.

## The filter

- Match `surface` exactly. It is the stable grouping key.
- Match `component` by engineering judgement; it is precise free text, not an enum.
- Read at most the 20 most recent matching records in the window, ordered by
  `closed_at`, newest first.

## Read persisted facts, inspect the named fix

- A resolved record persists `cause`, `solution`, `caused_by` and `fix_sha`.
- Inspect the named fix with `git show <fix_sha> --stat --patch`. A release squash or a
  ledger-only commit isolates no implementation; report that coarse trail honestly.
- Follow `caused_by` through live and archived records. It names the bug or task whose
  implementation wrote the lines this fix corrects; `none` means blame offered no
  candidate.
- Bug-window maturity belongs to the next candidate's `SPEC.md` `## Bug window review`:
  one KEEP leaves the first-level window; a REBUILD leaves after its tested replacement
  and a following candidate with no child bug.

## Declare `caused_by`

1. Inspect blame for the production lines the fix replaces and the matching records.
2. Choose the prior bug or task that wrote those lines. Use `none` only when blame offers
   no candidate.
3. Resolve once the fix commit exists (`SKILL.md` Phase 6).

4. `check` refuses a target naming no live or archived bug or known release task, and
   refuses a lineage loop.

## Cost bound

- Read at most 20 records and inspect at most 20 named fix commits per fix. A wider read
  belongs to `dd-audit-project`.
- This is a reading discipline. The audit measures its outcomes across the fleet.
