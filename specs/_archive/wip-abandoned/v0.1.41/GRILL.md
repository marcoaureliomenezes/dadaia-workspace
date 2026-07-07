# GRILL: v0.1.41 - Open bug root-cause sweep

**Status:** Aprovado
**Release ID:** v0.1.41
**Created:** 2026-06-29

## Questions

### Q1 - Are all open `dadaia-workspace` bug records in scope?

Yes, all true-open `dadaia-workspace` bug frontmatter records are picked. One naive text
match, `bug-report-fake-bug-write-emits-stub-and-discards-fields`, is excluded because its
frontmatter is already `status: Closed`.

### Q2 - Are any picked bugs duplicates?

Yes. The report-validation pair is one root cause. The two persisted-bind specs-doctor
records and the context-release cleanup bug are one root cause. They should close from
shared evidence rather than separate one-off fixes.

### Q3 - Is "solve all root causes" feasible in one release?

Yes for the `dadaia-workspace` open bug set. The root causes are broad but bounded:
contract drift, context resolution, SPEC-DOC-029 identity/isolation, root/repo hygiene,
architecture boundary enforcement, stale runtime config, context-dead git push behavior,
memory lint extensibility, and stale panel bug closure.

### Q4 - Does this release activate immediately?

No. `v0.1.40 alpha-1` is still the active implementation release. This release is prepared
as the next root-cause sweep and should become active after the current release is closed
or deliberately superseded.

### Q5 - What is the riskiest implementation area?

Specs resolver and SPEC-DOC-029 state wiring. The implementation must preserve explicit
`--specs-dir`, env-based bind, and persisted-bind flows.
