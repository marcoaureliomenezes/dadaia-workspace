---
name: dd-audit-project
description: >
  project-auditor's audit protocol (FR14) — bug history, spec compliance, and
  memory/constitution drift, run TOGETHER over the sha window since the last
  `audited` milestone. Suggested every 5 releases, never mandatory.
tldr: "Run all 3 pillars (bugs, specs, memory) together over the sha window since last `audited`; one FINDINGS.jsonl record per claim."
applyTo: "specs/audits/**"
---

# dd-audit-project — Three Pillars Over a SHA Window

> Not hook-enforced. `project-auditor` drives this protocol directly, dispatched by the operator or a dispatching agent.

## 1. When

- `project-auditor` runs this, dispatched by the operator or a dispatching agent.
- Suggested every 5 releases (D6), never mandatory.

## 2. Steps

1. Compute the window once per audit: `dd-diagnose`'s `LINEAGE.md` "The window (stated once)" section (A14.2).
2. Read the live release's `RELEASE.json` `audited` field plus every archived release's `audited` fact in `releases_histo.jsonl`.
3. Set the window to `[newest audited sha, HEAD]`, or the whole history when no `audited` milestone exists yet.
4. Never scan `specs/releases/_ideas/**` (D10/AS-7).
5. Record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope.
6. Run pillar 1 (`PILLAR-BUGS.md`): compute all eight forensic metrics on every `BUGS.jsonl` record in the window.
7. Write `audited` plus the four provenance fields in one atomic rewrite per reviewed bug record (A14.6).
8. Run pillar 2 (`PILLAR-SPECS.md`): check FR8 commit-shape conformance and canon-v6 pattern compliance over the window.
9. Run pillar 2 (continued): check `RELEASE.json` milestone completeness.
10. Run pillar 3 (`PILLAR-MEMORY.md`): execute every Part-1 principle's named `Measured by:` check.
11. Run pillar 3 (continued): match every Part-1 hunk in the window to an `accepted` ADR in the same commit, or flag HIGH.
12. Refuse to write `AUDIT.md` until all three pillar sections are present (A14.1) — fewer than three is not an audit.
13. Append one `FINDINGS.jsonl` record per claim from any pillar — shape and evidence rule: `FINDINGS-FORMAT.md`.
14. Surface the every-5-releases suggestion at release close (`project-manager`'s job, not this skill's write).

## 3. Done when

- The window is computed once and recorded in `AUDIT.md`'s scope.
- All eight bug-forensic metrics are computed with baseline + target.
- Every Part-1 principle's named check ran and was recorded.
- `AUDIT.md` carries all three pillar sections, never fewer.

## 4. References

- `dd-diagnose` (`LINEAGE.md`) — the window computation, cited not restated.
- `PILLAR-BUGS.md`, `PILLAR-SPECS.md`, `PILLAR-MEMORY.md` — the three pillar protocols.
- `FINDINGS-FORMAT.md` — one-record-per-finding shape, evidence rule, disposition vocabulary.
- `DADAIA.md` §6 (Audits) — full lifecycle: one audit binds to one remediation release, archives once dispositioned.
- `dadaia specs doctor --json`/`--recipe`; `dadaia bugs update <id> --set field=value` (the FR2 seam, pillar 1's only write).
- `dd-cli-library` — command syntax reference.
