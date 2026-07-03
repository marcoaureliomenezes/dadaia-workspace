---
name: panel-sessions-cost-dashboard-only
status: candidate
opened: 2026-07-02
owner: project-manager (curates)
source: operator decision 2026-07-02 — users never use the session list; keep only aggregated cost
intents:
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/sessions.py#render_sessions_section" }
    change: "replace the Sessions tab with an aggregated-cost-dashboard-only section: keep the 4-card stat grid (total sessions, total cost, AI turns, top agent) and the codex/pi cost-unknown banner semantics; delete the session-list table, filter/sort toolbar, detail drawer, skeleton rows, and the 10s list auto-refresh (sessions.js is 711 lines and sessions CSS 510 lines, mostly serving the list)"
  - subject: { kind: code, ref: "dadaia_workspace/features/panel/views/api.py#render_api_session_detail" }
    change: "delete the /api/sessions/<runtime>/<session_id> detail endpoint and replace /api/sessions with a server-side aggregate cost-summary endpoint (the dashboard is currently computed CLIENT-side from the full session list, so the aggregate must move server-side before the list dies); prune the then-dead TelemetryAggregator query surface, the handler route-table entries and 404 route listing, and the ~1,550 lines of session-list tests including the stale Playwright fixture that predates the v0.1.45 runtime switcher"
---

# BACKLOG — Panel Sessions: aggregated cost dashboard only

**Priority:** HIGH (operator-elected 2026-07-02). Scope discipline: preserve the
strict-CSP posture (the two inline-script sha256 hashes in panel/handler.py are
unaffected unless the inline scripts change) and the loopback/Host-guard model; land
with the global 4xx/5xx-and-console-error Playwright gate over the surviving tabs.
Update `specs/memory/product/panel/panel.md` at the disposing release (tab inventory,
route table, flowchart, usage flow).

Cross-refs: `panel-ux-overhaul` is re-baselined — its former "Sessions tab untouched"
constraint is void and its row-wrapping intent no longer includes the sessions view;
`panel-runtime-reliability` (SQLite WAL factory) is unaffected but should land against
the post-removal route surface.
