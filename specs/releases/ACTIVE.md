---
release: v0.1.75
phase: IMPLEMENTATION
---

# Active release: v0.1.75 — Test-suite rearchitecture (1,000–1,200 high-value tests)

Operator mandate 2026-07-09: rearchitect ~4,450 test fns to 1,000–1,200 well-designed
tests. Executed per the 7 per-cluster classification plans
(`.dadaia/tmp/claude/20260709/test-rearch/`), cluster-by-cluster with per-cluster green
gates. Carries the grill-CRITICAL FR2: explicit QA-adjudicated re-baseline of the frozen
v0.1.50 no-steal suite (successor baseline named in CLOSURE — v0.1.79's zero-diff gate
re-keys to it). FR3 speed wiring: pre-push `--quick`, pytest-xdist unit tiers,
`tests/tmp/` gitignored. Sequenced first of the 5 planned releases
(`specs/backlog/candidates.md`).
