# ADR 0016 — Stored provenance equals derived provenance

Status: proposed
Status law: only the operator flips a Status to `accepted` — an agent that writes
`accepted` has violated the law.
Date: 2026-08-27
Supersedes: — · Amends: — · Amended by: —

## Context
A bug record's `resolved_commit` cannot be written at resolve time — a commit cannot contain
its own sha — so git history is the authority and the stored field is a cache. Caches drift:
the moment a stored value disagrees with the derivation, every downstream lineage question
(what caused this bug, which fix bred which follower) is answered from a lie. The audit's
first pillar exists to catch that drift, but catching it at audit time is late; the same
equality can be asserted at implementation time against real records already on disk.

## Decision
We will store no provenance a resolver cannot re-derive: a stored `resolved_commit` equals the
value derived from git history through the single resolver seam, and git remains the sole
authority when the two disagree.

## Consequences
+ The cache is provably a cache, so lineage answers survive a rewrite of the stored field.
+ Drift is caught in the gating suite on a live sample rather than months later in an audit.
− The check walks real git history and is genuinely not free; it is marked `slow` and shares
  one cached walk across its cases.
− A record whose commit is unreachable (history rewritten) must be re-derived rather than
  hand-edited.

## Confirmation
Measured by:
`pytest -p no:cacheprovider tests/contract/test_resolved_commit_stored_equals_derived.py`
(≥ 20 live records forced through the resolver's derived branch; runs in the
`contract-coverage` job and the local preflight — only `unit-fast` excludes `slow`).
