---
release: v0.1.29
phase: IMPLEMENTATION
---

# Active release: v0.1.29 — Harness as a governed dimension + catalog completion

Closes the gap found auditing v0.1.28: model governance governs profiles but NOT the
worker harness, so PI cannot be selected as a Layer-2 worker through the governed policy.

**Phase:** DEFINITION — product-engineer authoring SPEC/PLAN/TASKS from `GRILL.md`
(decisions D-1..D-5). Operator: fix now, complete the catalog (all 7 workflows), ship
v0.1.28 + v0.1.29 together.

Branch: `feature/v0.1.29` (stacked on `feature/v0.1.28` @ bd710c57). v0.1.28 is
CLOSED+archived on its branch; both ship together once machine load clears for the
pre-push gate (a load-sensitive 437k-file perf test currently fails only under the
concurrent aero-fighters Playwright suite, not from any v0.1.28/29 code).
