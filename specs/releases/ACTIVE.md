---
release: none
phase: none
---

# Active release: none

v0.1.75 shipped (PR #145, `81e60ef7`) and closed — archived to `specs/_archive/v0.1.75/`.
Suite: 4,450 → 1,327 authored test fns, full run 2:52, coverage 84.30%.

Bug ledger: **5 open** (2026-07-10 remote intake: 1 CRITICAL lease-identity self-block,
4 HIGH lifecycle) + P0 cross-harness lock audit
(`specs/audits/2026-07-10-lock-risk-audit-cross-harness.md`) awaiting disposition.

Backlog consolidated to 5 entries (PR #147) and **release-defined 2026-07-10** under
the operator-ratified **NO-LOCKS DOCTRINE**: v0.1.76 lock liberation (advisory
presence replaces the blocking lease — P0, disposes the CRITICAL bug + full audit) →
v0.1.77 central bind-resolution seam (P0) → v0.1.78 lifecycle correctness &
diagnosability (P1, disposes the 4 HIGH bugs) → v0.1.79 panel agentic-layers reorg
(P2) → v0.1.80 deprecation strips (P3, ship ≥ 2026-08-01). Full definitions in
`specs/backlog/candidates.md`.

Next release: **v0.1.76 — lock liberation (advisory presence)**.
