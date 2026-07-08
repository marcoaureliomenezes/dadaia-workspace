---
release: none
phase: none
---

# Active release: none

**v0.1.67 — Test-Infra Executed-Path Integrity** shipped and closed 2026-07-08:
merged `08703384` (PR #128, all CI green incl. post-merge main); closure on
`chore/v0.1.67-closure`. Fixed the 2 test-integrity bugs found during v0.1.66 —
adapters bound `subprocess.run` as a class-definition-time default, so
executed-path tests silently invoked the real pi/codex binary; a loose assertion
let the real-binary error pass as success. FR1 moved both adapters to call-time
runner resolution; FR2 rewrote the false-positive tests with call-recorder
assertions; FR3 added a suite-wide real-binary guard (4-flag opt-in union).
Both bugs `resolved`; ledger 0 open.

**Next-pick backlog (per release-governance):** `panel-tab-reorg-agentic-layers`
(candidate), `dispatch-band-legacy-fallback-removal` (eligible 2026-08-01),
`platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`.
Audit follow-ups (2026-07-08 scaffolding audit, not yet backlogged): product-engineer
missing `dadaia-release-definition` skill; L2 ambient AGENTS.md inheritance; root
residue (`bug-space-war/`, `.playwright-mcp/`). Operator-pending: optional PyPI
deploy (v0.1.61–67 unpublished).
