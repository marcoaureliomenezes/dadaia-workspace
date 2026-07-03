---
release: none
phase: none
---

# Active release: none

**v0.1.52** — *Panel Plumbing* — is **CLOSED and ARCHIVED** at
`specs/_archive/releases/v0.1.52/` (CLOSURE.md). R4 of the 2026-07-02 operator
sequence: `/api/sessions` is a server-side aggregate cost summary behind a proper
facade; the Sessions tab is the aggregated-cost dashboard only (list/drawer/detail
deleted, −4,770 lines net); every telemetry-store SQLite connection flows through
the pragma'd WAL+busy_timeout factory with per-call read-only connections (the
shared cross-thread connection — the corruption root — is gone; quarantine is
WAL-aware; an AST allowlist contract protects the foreign `~/.codex` read-only
DBs); the kanban chain is completely deleted; mermaid fences are entity-escaped.
Process discovery recorded: consumed-backlog archival moves to SHIP when a release
deletes an anchored symbol (the fail-closed BL-SCHEMA registry correctly went red).
Merged as `fd23ea5e` (PR #93, 38 checks green, `e2e-panel` pass ×2).

No release is active. Next in sequence: **R5 — Legacy purge** (v0.1.53:
`legacy-surface-retirement` + `hygiene-and-dead-code-cleanup` +
`centralize-release-semver-canon` + `telemetry-tier2-chmod-unguarded-on-windows`)
per `specs/backlog/candidates.md` §Release sequence — the final release of the
operator's R1→R5 mandate.
