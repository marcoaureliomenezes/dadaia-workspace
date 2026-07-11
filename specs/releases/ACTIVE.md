---
release: v0.1.81
phase: IMPLEMENTATION
---

# Active release: v0.1.81 — Central bind-resolution seam (feature/v0.1.77)

v0.1.76 "Lock liberation" shipped (PR #149, `5dbe209c`) and closed — archived to
`specs/_archive/v0.1.76/`. The NO-LOCKS DOCTRINE is live: no path in
dadaia-workspace blocks an agent because of another session; advisory presence +
WARN-only pre-commit replace the lease. CRITICAL lock bug resolved with
executed-path evidence; P0 lock audit fully dispositioned and archived.

Bug ledger: 4 HIGH lifecycle bugs open (dispositioned by v0.1.78) + 1 LOW flake.

Next release: **v0.1.77 — central bind-resolution seam** per
`specs/backlog/candidates.md`.

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
