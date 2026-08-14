---
title: "git_objects: stream or chunk the cat-file --batch conversation — whole-range stdout buffer peaks at ~277 MB on the fallback shape (CWE-400)"
status: candidate
opened: 2026-08-14
description: >-
  Materializes a LOW from the APPROVED v0.9.0 ship security review. The 3c3c6d4a
  remediation correctly removed per-blob subprocess spawns and made the object
  stream a generator consumed lazily by scan_objects — but the generator is fed
  from result.stdout, and _run uses subprocess.run(capture_output=True), which
  blocks until EOF. Every under-cap blob of the range is therefore resident in ONE
  bytes buffer before the first ScannedObject is yielded. Measured upper bound in
  this repo for the `--not --remotes` fallback shape (first push of a ref, fresh
  clone without remote-tracking refs, or unresolvable remote_sha): 11,478 blobs /
  ~276.7 MB in a single buffer — versus the ~129 MB resident figure the
  remediation was fixing. Availability only, and fail-closed: a MemoryError aborts
  push-gate-check non-zero and the hook refuses. Not reachable on the ordinary
  origin/develop..develop range (71 blobs this ship). Reviewer's fix options:
  drive git cat-file --batch through subprocess.Popen with piped stdin/stdout and
  parse the length-prefixed protocol incrementally, or chunk fetch_shas into
  fixed-size batches (e.g. 500 blobs) reusing the existing code per chunk —
  chunking is the smaller change and caps the peak deterministically.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_read_blobs
    change: >-
      Bound the resident set: either a Popen-driven incremental parse of the
      length-prefixed batch protocol, or fixed-size sha chunks through the
      existing code path. Preserve the single-conversation performance win (no
      return to per-blob spawns), the 5 MB per-blob cap, and the typed-error
      contract.
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_run
    change: >-
      If the Popen route is chosen: extend or bypass _run for the streaming case
      without losing the timeout and typed GitObjectReadError conversion it
      guarantees today.
---

# git_objects streamed/chunked batch reads

## Description

See frontmatter. Source — the APPROVED pre-push security handoff
`.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`,
LOW finding "CWE-400: the whole git cat-file --batch output is materialised in one
bytes buffer" (`git_objects.py:152,156`), with the in-repo measurement
(11,478 blobs / 276.7 MB under the cap, 0 over it). Routed to the PM in
`decisions_required` (restated by the reconciliation handoff); this entry is that
routing.

Related evidence from the round-2 code review
(`2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`, MEDIUM on
V14): on the real 8,861-blob fallback range, READING costs 4.29 s while MATCHING
costs ~143 s — so chunking the read will not change fallback wall-clock
materially; the memory bound is the point of this entry, the match cost belongs to
`closure-v14-perf-figure-correction`.

## Motivation

The fallback shape is exactly the shape a first-time or recovery push takes — the
worst moment for the gate to die on memory. Deterministic peak, fail-closed
today, cheap to cap.

## Acceptance criteria

- Peak resident bytes for the batch conversation bounded by a constant
  (chunk size × cap), pinned by a test or a documented measurement over a
  multi-thousand-blob synthetic range.
- Single-conversation win preserved (no per-blob subprocess); timing on the
  ordinary range does not regress.
- Timeout and typed-error semantics unchanged (existing unit tests green).

## Ownership

`software-engineer` implements; `security-reviewer` verifies CWE-400 closed in the
covering push review.
