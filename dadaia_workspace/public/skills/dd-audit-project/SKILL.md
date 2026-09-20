---
name: dd-audit-project
description: >
  The three-pillar drift audit (the reviewer's audit lens) — bug history, spec compliance, memory
  drift — over the sha window read from audits_histo.jsonl. Use when dispatched to
  audit a context.
---

# dd-audit-project — Three Pillars Over a SHA Window

> `code-reviewer` drives this directly, dispatched by the operator or a dispatching
> agent. Suggested every 5 releases, never mandatory.

## 1. The window — computed once per audit

1. Open `specs/audits/AGENTS.md` (the area's scoped law) and follow it.
2. Window mechanics: `dd-bug-resolution`'s `LINEAGE.md` §The window, cited never restated.
3. Record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope.

## 2. The three pillars — run together, never fewer

- **Pillar 1 — bugs** ([`PILLAR-BUGS.md`](PILLAR-BUGS.md)): compute all eight
  forensic metrics on every `BUGS.jsonl` record in the window; stamp `audited` on each
  reviewed record (`dadaia bugs update <id> --set audited=<slug>`, pillar 1's only write).
- **Pillar 2 — specs** ([`PILLAR-SPECS.md`](PILLAR-SPECS.md)): commit-shape
  conformance, canon pattern compliance, `_RELEASE.json` milestone completeness over
  the window.
- **Pillar 3 — memory** ([`PILLAR-MEMORY.md`](PILLAR-MEMORY.md)): execute every
  Part-1 principle's named `Measured by:` check; match every Part-1 hunk in the
  window to an `accepted` ADR in the same commit, or flag HIGH.

Refuse to write `AUDIT.md` until all three pillar sections are present — fewer than
three is not an audit. Append one `FINDINGS.jsonl` record per claim
([`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md)).

## 3. Done when

- The window is computed once and recorded in `AUDIT.md`'s scope.
- All eight bug-forensic metrics computed with baseline + target; every Part-1
  principle's named check ran and was recorded.
- `AUDIT.md` carries all three pillar sections; every claim has its
  `FINDINGS.jsonl` record.

## 4. References

- [`PILLAR-BUGS.md`](PILLAR-BUGS.md) · [`PILLAR-SPECS.md`](PILLAR-SPECS.md) ·
  [`PILLAR-MEMORY.md`](PILLAR-MEMORY.md) — the pillar protocols.
- [`FINDINGS-FORMAT.md`](FINDINGS-FORMAT.md) — record shape, evidence rule,
  disposition vocabulary.
- Lifecycle, pillars and verbs: `specs/audits/AGENTS.md`.
- `dadaia doctor --json` / `dd-cli-library` — command reference.
