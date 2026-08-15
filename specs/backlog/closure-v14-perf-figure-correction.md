---
title: "v0.9.0 CLOSURE V14 fallback-range figure is synthetic and non-comparable: real-content matching costs ~1.3 s/MB (~147 s over 8.8k blobs) — record the real number as product truth"
status: candidate
opened: 2026-08-14
description: >-
  Materializes the round-2 code-review MEDIUM (axis 3, evidence fidelity;
  non-blocking) with the reviewer's own routing: CLOSURE.md is FROZEN under
  specs/_archive/, so the close is NOT reopened a third time — the correction is
  carried here and the real number recorded when picked. V14 reports the
  fallback-shape benchmark at 2.978 s total (~16x faster than round 1's ~48 s);
  measured against the REAL 8,861-blob / 133 MB range at the reviewed tip the scan
  takes ~147 s (read 4.29 s + match 142.9 s): the synthetic corpus evidently
  carried ~2 MB of content vs 133 MB real, so "the same benchmark" compared two
  different workloads and the 16x ratio is an artifact of the substitution. What
  IS real and reproduced: the read-path improvement (~3.7x, per-blob spawns
  eliminated). What dominates a fallback range is raw regex throughput over
  content volume (~1.3 s/MB, per-pattern cost flat, v4 carve-outs marginally
  FASTER than v2 — the reviewer tested and rejected the carve-out-slowdown
  hypothesis), which batching could never address and the 5 MB cap does not bound
  (this repo has zero over-cap blobs). The reviewer also recorded his own round-1
  "31.6 s match" figure as equally unreproducible. The truthful statement to
  record: the fallback shape costs MINUTES on a content-heavy repository; the
  conclusion V14 supports (A7.3 budget missed, mitigation routed) stays correct.
intents:
  - subject:
      kind: doc
      ref: memory/product/sdd/sdd-gate-v3.md#Push-Range Denylist Scan
    change: >-
      Record the real-content performance posture as product truth in the
      push-range scan section: ordinary-range timing (seconds), fallback-shape
      timing (~1.3 s/MB, minutes on content-heavy repos), read vs match split, and
      that the archived V14 synthetic figure is superseded by this measurement —
      the FROZEN CLOSURE is corrected forward, never edited.
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/denylist_scan.py#_first_match
    change: >-
      Optional at pick time: if the ~1.3 s/MB match throughput is worth improving
      (single combined regex pass, term pre-filtering, or early-exit ordering),
      measure on real content before and after; otherwise record the decision not
      to and close with the memory correction alone.
---

# CLOSURE V14 perf-figure correction (fallback-range real-content measurement)

## Description

See frontmatter. Source — code-reviewer round-2 handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`,
MEDIUM finding "CLOSURE V14's ~16x faster / 2.978 s fallback-range figure is not
reproducible", metrics `fullhistory_blobs: 8861`,
`fullhistory_read_seconds_after: 4.29`, `fullhistory_match_seconds_after: 142.9`,
`fullhistory_peak_rss_mb: 281`; `decisions_required` item 1 resolved by this
entry per the reviewer's own recommendation (backlog return, not a third reopen —
the same disposition lane as the A7.3 miss V14 already routed).

Cross-references: the A7.3 budget-miss mitigation is the idea
`bugs-jsonl-whole-blob-per-append` (the data-side cost driver on ordinary
ranges); the memory-peak half of the fallback shape is
`git-objects-streamed-batch-reads` (CWE-400). This entry owns only the record
correction and the match-throughput question. The amnesty entry's memory note
lands in the same atom section when both are delivered.

## Motivation

Evidence fidelity is the currency of this workspace's closes; an archived
validation row now carries a figure two independent measurements contradict. The
FROZEN rule forbids editing it — the sanctioned shape is a forward correction in
memory, exactly what the reviewer prescribed.

## Acceptance criteria

- A real-content fallback-range measurement (read + match split, s/MB) recorded
  in the sdd-gate-v3 atom, explicitly superseding the archived V14 synthetic
  figure and citing this entry.
- Decision recorded on match-throughput optimization (adopt with before/after
  real-content numbers, or reject with reason).
- `specs/_archive/**` untouched.

## Ownership

`software-engineer` measures (and optionally optimizes); `product-engineer` lands
the memory correction in a DEFINITION/CLOSURE phase window.

## Intake adjudication (ADR #15 — report #1)

**APPROVED** — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation. Adjudicated via intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`).
The entry remains a live pickable candidate.
