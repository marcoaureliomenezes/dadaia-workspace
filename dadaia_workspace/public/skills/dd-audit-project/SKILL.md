---
name: dd-audit-project
description: "project-auditor's audit protocol (FR14) — bug history, spec compliance, and memory/constitution drift, run TOGETHER over the sha window since the last `audited` milestone. Suggested every 5 releases, never mandatory."
applyTo: "specs/audits/**"
---

# dd-audit-project — Three Pillars Over a SHA Window

> **Not a hook-enforced mechanism.** There is no workflow engine that runs the audit
> stage or its gates. `project-auditor` drives this protocol directly, dispatched by
> the operator or a dispatching agent. This skill is the authoritative protocol.

## The window (cited, never restated)

`dd-diagnose`'s `LINEAGE.md`, section "The window (stated once)", **is** this skill's
window (A14.2 — the same computation FR7 phase 0 uses): scan every `RELEASE.jsonl` (the
live release's, every archived release's, and `releases_histo.jsonl`) for the newest
`audited` milestone; the window is `[that sha, HEAD]`, or the whole history when no
`audited` milestone exists yet. `specs/releases/_ideas/**` is never scanned (D10/AS-7).
Run it once per audit; record the resulting `[from-sha, HEAD]` in `AUDIT.md`'s scope.

## The three pillars — always together, never one alone

An audit that emits fewer than three pillar sections is not an audit — refuse to write
`AUDIT.md` until all three are present (A14.1).

| Pillar | Disclosed sibling | Input | Done when |
|---|---|---|---|
| 1 — Bug history | `PILLAR-BUGS.md` | every `BUGS.jsonl` record whose registration or resolution sha falls in the window | all **eight** forensic metrics computed with baseline + target (A14.7); `audited` + the four provenance fields written in **one** atomic rewrite per reviewed record (A14.6) |
| 2 — Spec compliance | `PILLAR-SPECS.md` | `git log` over every release commit in the window + `dadaia specs doctor` | FR8 commit-shape conformance reported per shape; canon-v6 pattern compliance reported; `RELEASE.jsonl` milestone completeness checked |
| 3 — Memory/constitution drift | `PILLAR-MEMORY.md` | the memory trio's Part 1 `Measured by:` lines, `product/` atoms, `constitution.md` | every Part-1 principle's named check executed and recorded; every Part-1 hunk in the window matched to an `accepted` ADR in the same commit, or flagged HIGH |

## Cadence and lifecycle

An audit is **suggested every 5 releases, never mandatory** (D6) — `project-manager`
surfaces the suggestion at release close once ≥ 5 `shipped` milestones have accrued
since the last `audited`. The full lifecycle — one audit binds to exactly one
remediation release, every finding gets a disposition, the folder archives only once
fully dispositioned — is `DADAIA.md` §6 (Audits); referenced, not restated.

## Findings

Every claim, from any pillar, becomes one `FINDINGS.jsonl` record. Shape, the evidence
rule, and the disposition vocabulary: `FINDINGS-FORMAT.md` (sibling).

## dadaia CLI

`dadaia specs doctor --json`/`--recipe`; `dadaia bugs update <id> --set field=value`
(the FR2 seam — pillar 1's **only** write, never a second writer). Command syntax is
`dd-cli-library`'s; not restated here.
