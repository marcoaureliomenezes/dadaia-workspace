---
title: "denylist-scan skip note: 5 MB fail-open mislabelled as binary (CWE-778) + split counters + end-to-end coverage of the note"
status: candidate
opened: 2026-08-14
description: >-
  Merges the SAME defect reported independently by both ship reviewers (MEDIUM in
  each) with the QA-1 coverage gap the v0.9.0 CLOSURE routed here. The 5 MB
  per-blob cap (infrastructure/git_objects.py _MAX_BLOB_BYTES) yields an oversized
  blob as decodable=False without fetching it; scan_objects counts every
  decodable=False object into one skipped_binary_count; and service._annotate_skip
  renders the whole class as "N binary blob(s) skipped by the denylist scan (not
  text-decodable)". A 6 MB PLAIN-TEXT file (log capture, SQL dump, vendored data)
  is neither binary nor undecodable — it is published unscanned while the one
  message the operator sees says a binary blob (which a text denylist could never
  have matched anyway) was skipped. An operator reading that line correctly
  concludes there was nothing to check: the disclosed fail-open (SPEC R3, sound and
  documented) is degraded exactly where it matters. CWE-778 (insufficient logging).
  No exposure today: 0 oversized blobs exist in the repo (11,478 blobs measured).
  QA-1 rides along: nothing end-to-end asserts the skip note actually reaches the
  operator through push_gate_decision -> Decision.warn -> CLI stderr on both the
  allow and refuse paths — the wiring was only manually verified in v0.9.0.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/denylist_scan.py#ScanOutcome
    change: >-
      Split the counter: carry skipped_oversized_count separately from
      skipped_binary_count so the two skip reasons are distinguishable by every
      consumer.
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#_annotate_skip
    change: >-
      Render the oversized case as what it is, naming path and size (e.g. "1
      blob over the 5 MB scan cap was NOT scanned: <path> (6.2 MB) — verify it by
      hand"); keep the binary wording for genuinely undecodable blobs. Emit on both
      the allow and refuse paths as today.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_MAX_BLOB_BYTES
    change: >-
      Distinguish oversized from undecodable at the adapter (the only place that
      knows the size), and evaluate the round-2 reviewer suggestion of scanning the
      FIRST 5 MB of an oversized blob instead of none — partial coverage strictly
      dominates zero coverage for a substring/regex denylist. Preserves the R3
      never-fetch performance decision for the remainder.
  - subject:
      kind: code
      ref: dadaia_workspace/features/chokepoints/service.py#_run_denylist_scan
    change: >-
      QA-1 closure: unit tests asserting the decision's warn channel carries the
      skip note (both counters) on an allow case and a refuse case, so the
      operator-facing channel is pinned by a test rather than by a manual check.
---

# denylist-scan skip note: oversized fail-open mislabelled as binary

## Description

See frontmatter. Sources, deduplicated into this single entry (the same defect
appears in three reports):

- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — MEDIUM, CWE-778, with the concrete exposure narrative
  (`service.py:328-337`, `git_objects.py:141-146`) and the fix shape (split
  counters + name the path and size). Explicitly routed to the PM in
  `decisions_required`, restated by the reconciliation handoff
  `2026-08-14T231057Z-security-reviewer-v0.9.0-main-reconciliation.handoff.json`.
- Code-reviewer round-2 handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`
  — MEDIUM "5 MB cap is a fail-open that the operator-facing note mislabels",
  same fix plus the scan-first-5MB suggestion; flagged hotfix-eligible.
- `specs/_archive/releases/v0.9.0/CLOSURE.md` §"Backlog returns" — QA-1 (LOW):
  no end-to-end coverage of the skip-count note; suggested fix is the
  `decision.warn` unit-test pair, absorbed into this entry because the counter
  split rewrites the exact note QA-1 wants covered — fixing one without the other
  would immediately re-open the gap.

## Motivation

This is the only channel through which a text leak can pass the v0.9.0 gate while
telling the operator it was handled. The mislabel costs one sentence to fix; the
counter split is a one-liner class change; the tests close a known coverage gap on
a security control's operator-facing evidence. Small, hotfix-eligible
(both reviewers), and the most operator-visible residual of the release.

## Acceptance criteria

- `ScanOutcome` carries `skipped_oversized_count` distinct from
  `skipped_binary_count`; an oversized text blob is reported with path + size and
  the words "NOT scanned"; a genuinely binary blob keeps the current wording.
- Unit tests assert `decision.warn` carries the note on an allow case and a refuse
  case (QA-1 closed).
- Decision recorded (yes/no + reason) on scanning the first 5 MB of oversized
  blobs.
- Existing R3 property preserved: an oversized blob's full content is never
  fetched.

## Ownership

`software-engineer` implements; `qa-engineer` confirms QA-1 closed;
`security-reviewer` verifies the CWE-778 finding closed in the covering push
review.
