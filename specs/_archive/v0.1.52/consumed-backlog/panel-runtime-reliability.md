---
name: panel-runtime-reliability
status: candidate
opened: 2026-07-01
owner: project-manager (curates)
source: audit 20260701T201136Z-0bcd6c19 (B/panel, C)
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/telemetry/store/schema.py#open_connection" }
    change: "route ALL telemetry SQLite connections through the pragma'd factory (WAL + busy_timeout); close refresh DAOs in finally; read-only URIs for query paths; WAL-aware quarantine (move -wal/-shm siblings with the DB)"
  - subject: { kind: catalog, ref: "panel" }
    change: "decide /api/kanban fate (delete the orphaned chain: view + route + CSS + tests, or re-document as a supported headless API); memory/academy mermaid fences: escape-or-render decision in _md_render (currently unescaped and never rendered); remove the dead telemetry panel.token permission drift-check referencing the deleted auth module"
---

# BACKLOG — Panel runtime reliability

**Priority:** MEDIUM. Root chain of the SQLite corruption bug: the only WAL/busy-PRAGMA
factory has zero production callers; the panel shares one check_same_thread=False
connection across ThreadingHTTPServer threads; refresh leaks unclosed write DAOs;
quarantine strands -wal/-shm siblings. Bug deferred here:
`panel-telemetry-sqlite-corrupts-under-concurrent-access`. Pure dead-code items are
owned by `hygiene-and-dead-code-cleanup` (cross-ref).
