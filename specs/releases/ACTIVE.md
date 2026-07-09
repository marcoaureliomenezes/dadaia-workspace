---
release: v0.1.68
phase: IMPLEMENTATION
---

# Active release: v0.1.68 — Lifecycle Evidence/Handoff Engine Correctness

**Phase:** IMPLEMENTATION (SPEC/PLAN/TASKS Aprovado; architect REVISE F1-F4 folded).

First of three remediation releases dispositioning the 9 live lifecycle/CLI bugs
reported against `dd-chain-capture v0.2.0` on a machine running current `main`
(HEAD `54e9be0e`). Release A fixes the lifecycle **engine**: run-scoped evidence
selection, terminal-payload consumption contract, and TASKS.md-derived implement
write-scope — plus the marquee full-pipeline E2E that drives a real release
through `dadaia lifecycle pipeline` end-to-end (the test that was missing).

**Picked bugs (3):**
- `lifecycle-pipeline-selects-stale-unrelated-handoff` (HIGH)
- `implement-review-completed-run-leaves-unconsumed-required-payload` (HIGH)
- `pipeline-does-not-derive-write-scope-from-tasks` (HIGH)

**Releases B (v0.1.69, context/CLI surface) and C (v0.1.70, contract/hygiene
drift)** follow, each a full cycle.
