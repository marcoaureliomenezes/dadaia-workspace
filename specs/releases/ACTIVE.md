---
release: v0.1.67
phase: IMPLEMENTATION
---

# Active release: v0.1.67 — Test-Infra Executed-Path Integrity

Picked set: 2 open bugs, one shared root cause —
`pi-executed-path-cli-tests-invoke-real-pi-binary` (MEDIUM) and
`pi-e2e-test-false-positive-loose-blocked-reason-assertion` (HIGH), both next-pick
debt carried over from v0.1.66. Root cause: `PiHeadlessAdapter.__init__` and
`CodexExecAdapter.__init__` bind `runner: Runner = subprocess.run` at
class-definition time, so `monkeypatch.setattr(".pi_runtime.subprocess.run", fake)`
never reaches an already-bound default — the real local `pi` binary runs, masked
by a truthy-only `blocked.reason` assertion in the pre-existing executed-path test.

**Prior:** v0.1.66 — Layer-2 Worker Path Remediation shipped and closed 2026-07-08
(merged `70c9760c`, PR #126). Live backlog: `panel-tab-reorg-agentic-layers`
(candidate), `dispatch-band-legacy-fallback-removal` (eligible 2026-08-01),
`platform-seam-todo-retirement`, `specs-doctor-partial-archive-invariant`.
Operator-pending: optional PyPI deploy (v0.1.61–66 unpublished).
