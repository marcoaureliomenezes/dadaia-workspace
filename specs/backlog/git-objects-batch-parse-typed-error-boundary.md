---
title: "git_objects batch-parse loop: raw ValueError escapes the typed GitObjectReadError boundary; desync continues instead of aborting (CWE-755)"
status: picked
opened: 2026-08-14
description: >-
  The SAME defect reported independently by both ship reviewers (LOW in each),
  merged here. Inside _read_blobs — the very function whose sibling _blob_info was
  fixed at 3c3c6d4a to route through _run so failures surface typed — two parse
  paths still raise raw ValueError past the module's contract:
  `out.index(b"\n", pos)` when no newline remains, and `int(size_str)` on a
  non-numeric third header field. Both escape GitObjectReadError, contradicting
  the module docstring and the port contract (core/protocols/git_object_reader.py:
  "Any git failure raises GitObjectReadError … never a raw, unhandled exception at
  the push boundary"). Effect is fail-closed but ugly: the ValueError escapes to
  the CLI, aborts push-gate-check with a Python traceback, and the hook refuses —
  the operator gets a traceback instead of the actionable, --no-verify-naming
  refusal FR6 promises, and an unhandled traceback at a security gate is the kind
  of output people learn to bypass rather than read. Secondary (code review): the
  existing desync branch yields an undecodable object and CONTINUES, but after a
  desync `pos` points into content bytes, so every subsequent header parse is
  garbage — a stream of fabricated decodable=False objects silently counted as
  binary skips. A gate that has lost sync with git's stream should abort with the
  typed error rather than fabricate. Reachability is low (a `missing` line is
  2 fields and handled; non-zero exit caught earlier) — hence LOW, not MEDIUM.
intents:
  - subject:
      kind: code
      ref: dadaia_workspace/infrastructure/git_objects.py#_read_blobs
    change: >-
      Wrap the header-parse pair (out.index / int(size_str)) in try/except
      ValueError and raise GitObjectReadError("git cat-file --batch stream
      desynchronised at object <sha>"); on the existing desync branch, raise the
      typed error instead of yielding fabricated decodable=False objects and
      continuing.
  - subject:
      kind: code
      ref: dadaia_workspace/core/protocols/git_object_reader.py#GitObjectReadError
    change: >-
      Port contract honored by construction again: add a unit test feeding a
      truncated/garbled batch stream through the adapter and asserting the typed
      error (never a raw ValueError) reaches the caller.
---

# git_objects batch-parse typed error boundary

## Description

See frontmatter. Sources, deduplicated into this single entry (same defect, two
reports):

- Code-reviewer round-2 handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T222609Z-code-reviewer-v0.9.0-prepr-round2.handoff.json`
  — LOW "two unguarded raise paths inside the very function that added a
  defensive branch for stream desync" (`git_objects.py:160,171`; desync-continue
  at `:164-169`).
- Security-reviewer ship handoff
  `.dadaia/handoff/dadaia-workspace/2026-08-14T224700Z-security-reviewer-v0.9.0-ship.handoff.json`
  — LOW CWE-755, same lines, with the fail-closed/ugly-diagnostic effect analysis;
  routed to the PM in `decisions_required` (restated by the reconciliation
  handoff).

## Motivation

Completes the exact remediation 3c3c6d4a started: every failure at the push
boundary surfaces as the typed, actionable refusal, never a traceback. One
try/except plus one behavior change on the desync branch, plus the test the
reviewers both asked for.

## Acceptance criteria

- A truncated batch stream and a non-numeric size field each surface as
  GitObjectReadError with the desync message (unit tests through the real
  adapter); no raw ValueError escapes the module.
- Desync aborts typed instead of yielding fabricated undecodable objects; no
  fabricated skip ever reaches the skip-count note.
- FR6 refusal shape (names the failure and --no-verify) verified for this failure
  class at the decision layer.

## Ownership

`software-engineer` implements; `security-reviewer` verifies CWE-755 closed in the
covering push review. Rides the same hotfix/hardening window as
`push-ref-sha-validation-git-argv-hardening`.

## Intake adjudication (ADR #15 — report #1)

**APPROVED** — operator-delegated adjudication, 2026-08-15 (goal directive), verdicts
per PM recommendation. Adjudicated via intake report #1
(`.dadaia/reports/dadaia-workspace/project-manager/2026-08-15T132600Z-intake.html`).
The entry remains a live pickable candidate.

## Pick provenance (v0.11.0)

**picked — v0.11.0**, 2026-08-15. Delivered as **FR8** of release `v0.11.0` "scan-v2".
Provenance record: `specs/releases/v0.11.0/SPEC.md` §7. Sequenced **before**
`git-objects-streamed-batch-reads` (PLAN §3): the chunking restructures the very loop this
entry corrects, so landing it second would restructure code known to be wrong. Both halves
are delivered as written — the typed wrap of the `out.index` / `int(size_str)` pair **and**
the behaviour change on the desync branch, which now aborts typed instead of yielding
fabricated undecodable objects that the skip counters would then report as fiction. Terminal
disposition `DELIVERED — v0.11.0` lands at closure.
