---
release: none
phase: none
---

# Active release: none

The four-release queue **v0.1.61 → v0.1.62 → v0.1.63 → v0.1.64 is COMPLETE** —
all shipped and closed 2026-07-07 (Rulings 61-A/61-B order honored end-to-end):

1. **v0.1.61 — Audit Remediation & Memory Truth** — merged `3965df4c` (PR #116),
   closure `2d308c8d` (PR #117); 41/41 audit dispositions.
2. **v0.1.62 — Injection Contract & Fan-out Containment** — merged `352969da`
   (PR #118), closure `b58becc6` (PR #119); HIGH sidecar bug resolved.
3. **v0.1.63 — Plugin Platform Completion** — merged `457e4e10` (PR #120),
   closure `1061c26b` (PR #121); uninstall + 4+4 pack skill rosters.
4. **v0.1.64 — Platform Ergonomics & Tiering** — merged `d8bcdff7` (PR #122),
   closure on this branch; golden_platform consolidation, entry-harness
   auto-default + PI pin, `dispatch_band` rename; `fast-tier-persona-validation`
   REJECTED (PM-ratified, operator-overridable).

**Next-pick debt (outranks plain backlog per release-governance):** open LOW
bugs `backlog-doctor-yaml-parse-misdiagnosis` +
`e2e-panel-harness-toggle-ci-flake`; live backlog returns incl.
`dispatch-band-legacy-fallback-removal`, `platform-seam-todo-retirement`,
`specs-doctor-partial-archive-invariant`.
