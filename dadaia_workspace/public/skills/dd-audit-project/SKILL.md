---
name: dd-audit-project
description: >
  project-auditor's audit protocols: the three-pillar drift audit (bug history, spec
  compliance, memory drift) over the sha window since the last audited milestone, and
  the pre-implementation spec-set review. Use when dispatched to audit, or to review
  a spec set before implementation.
---

# dd-audit-project — Three Pillars Over a SHA Window

> `project-auditor` drives this directly, dispatched by the operator or a dispatching
> agent. Suggested every 5 releases, never mandatory.

## 1. The window — computed once per audit

1. Read the live release's `_RELEASE.json` `audited` field plus every archived
   release's `audited` fact in `releases_histo.jsonl`.
2. Set the window to `[newest audited sha, HEAD]` — the whole history when no
   `audited` milestone exists yet. Never scan `specs/releases/_ideas/**`.
3. Record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope. Window mechanics:
   `dd-bug-resolution`'s `LINEAGE.md`, cited not restated.

## 2. The three pillars — run together, never fewer

- **Pillar 1 — bugs** ([`PILLAR-BUGS.md`](PILLAR-BUGS.md)): compute all eight
  forensic metrics on every `BUGS.jsonl` record in the window; write `audited` plus
  the four provenance fields in one atomic rewrite per reviewed record
  (`dadaia bugs update <id> --set field=value`, pillar 1's only write).
- **Pillar 2 — specs** ([`PILLAR-SPECS.md`](PILLAR-SPECS.md)): commit-shape
  conformance, canon pattern compliance, `_RELEASE.json` milestone completeness over
  the window.
- **Pillar 3 — memory** ([`PILLAR-MEMORY.md`](PILLAR-MEMORY.md)): execute every
  Part-1 principle's named `Measured by:` check; match every Part-1 hunk in the
  window to an `accepted` ADR in the same commit, or flag HIGH.

Refuse to write `AUDIT.md` until all three pillar sections are present — fewer than
three is not an audit. Append one `FINDINGS.jsonl` record per claim
([`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md)).

## 3. Spec-set review (the second protocol)

A pre-implementation/refinement spec review runs
[`SPEC-REVIEW.md`](SPEC-REVIEW.md) — the same auditor, a different input (a spec set
instead of a sha window).

## 4. Done when

- The window is computed once and recorded in `AUDIT.md`'s scope.
- All eight bug-forensic metrics computed with baseline + target; every Part-1
  principle's named check ran and was recorded.
- `AUDIT.md` carries all three pillar sections; every claim has its
  `FINDINGS.jsonl` record.

## 5. References

- [`PILLAR-BUGS.md`](PILLAR-BUGS.md) · [`PILLAR-SPECS.md`](PILLAR-SPECS.md) ·
  [`PILLAR-MEMORY.md`](PILLAR-MEMORY.md) — the pillar protocols.
- [`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md) — record shape, evidence rule,
  disposition vocabulary.
- [`SPEC-REVIEW.md`](SPEC-REVIEW.md) — the spec-set review dimension.
- `DADAIA.md` §6.8 — lifecycle: one audit binds to one remediation release,
  archives once dispositioned.
- `dadaia specs doctor --json` / `dd-cli-library` — command reference.
