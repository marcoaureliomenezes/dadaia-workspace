---
release: none
phase: none
---

# Active release: none

**v0.1.66 — Layer-2 Worker Path Remediation** shipped and closed 2026-07-08:
merged `70c9760c` (PR #126, all CI green incl. post-merge main); closure on
`chore/v0.1.66-closure`. Fixed 7 dadaia-workspace product bugs blocking a remote
user's Layer-2 (pi/codex) workflows — each root-cause, reproduced RED-first on
the real executed path, proven GREEN, plus a real-binary pi/codex smoke. All 7
carry `resolved` terminal events.

**Next-pick debt (outranks plain backlog per release-governance):** 2 open bugs
discovered mid-release — `pi-e2e-test-false-positive-loose-blocked-reason-assertion`
(HIGH) and `pi-executed-path-cli-tests-invoke-real-pi-binary` (MEDIUM), both the
executed-path/false-positive-test class. Live backlog: `panel-tab-reorg-agentic-layers`
(candidate), `dispatch-band-legacy-fallback-removal` (eligible 2026-08-01),
`platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`.
Operator-pending: optional PyPI deploy (v0.1.61–66 unpublished).
