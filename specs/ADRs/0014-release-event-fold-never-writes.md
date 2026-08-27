# ADR 0014 — The release-event fold never writes

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
`RELEASE.jsonl` is an append-only governance record: milestone facts are appended by agents
with file tools, and the reader's job is to fold them into current state. A reader that can
also write is one refactor away from "repairing" the ledger it is reading — the failure mode
that destroys the audit value of an append-only record, because the evidence and its
interpreter become the same actor. `core/release_events.py` additionally does zero file I/O
at all, deliberately, so it never needs to join the authorized set of ADR 0011.

## Decision
We will keep the release-event fold read-only: `core/release_events.py` contains no
write-shaped call and no file I/O, and every append to `RELEASE.jsonl` happens outside it.

## Consequences
+ Folding is a pure function of the records handed to it, so it is testable without a ledger
  on disk and cannot corrupt one.
+ The set of writers to the governance record stays enumerable.
− Any convenience "read-modify-write" helper must live elsewhere and be reviewed as a writer.

## Confirmation
Measured by: `pytest -p no:cacheprovider tests/contract/test_release_events_read_only.py` (AST
walk over the module for write-shaped calls and file I/O).
