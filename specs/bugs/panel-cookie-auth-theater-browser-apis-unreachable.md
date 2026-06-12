---
name: panel-cookie-auth-theater-browser-apis-unreachable
status: Closed
severity: CRITICAL
session_id: sess_4f3a2384
reported: 2026-06-11
resolved_in: v0.1.13
surface: panel auth architecture (features/panel/{auth,handler}.py + views/assets/js/core.js)
---

**Symptom:** With the v0.1.11 launch-token flow, the panel UI shell loads but EVERY
`/api/*` call returns 401 in a real browser — Kanban, sessions, panel-status,
academy, workflows, agents all dead. The Agentic tab shows "Authentication
required. Re-open the panel via `dadaia panel start`" (a command that does not
exist). Live-reproduced with Playwright on a fresh profile: 3/3 boot XHRs 401,
console floods with one 401 per 5s poll.

**Root cause (architecture incoherence, three layers):**
1. The launch-token exchange (T-011-13/ADR-10) mints the `panel_session` cookie
   carrying the Bearer — but **no server code ever reads a Cookie header**. Every
   non-PUBLIC route validates only `Authorization` (handler.py `_validate_bearer`
   on `self.headers.get("Authorization")`). `SESSION_COOKIE_NAME` has zero
   consumers. The cookie gates nothing (the shell route is PUBLIC anyway).
2. The front-end (`views/assets/js/core.js`) still bootstraps its credential from
   the **removed** `?token=` query param into `localStorage['panel_token']`. With
   `?launch=` it stores nothing, and `authedFetch` sends no header. The cookie is
   `HttpOnly`, so JS cannot use it either. There is NO path by which a browser
   can authenticate to the API after v0.1.11.
3. Pre-existing: the Servers tab polls `/api/panel-status` with a **plain
   `fetch`** (not `authedFetch`) — it 401'd in every version and shows a
   misleading "if using an ad blocker…" notice.

**Why reviews missed it:** the AC-W4-02 "binding e2e" exercised server responses
to crafted requests (replay 401, cookie flags, tokenless 401) but never the
shipped JS client; ADR-10's "sensitive APIs remain Bearer-only" was accepted
without asking how the browser obtains a Bearer once it left the URL.

**Intermittence ("works one day, not the other"):** a `panel_token` persisted in
localStorage by a v0.1.10 launch still authenticates if it matches the server's
persisted token — fresh profiles/machines get 100% 401s. The stale localStorage
Bearer is also an unswept credential in browser storage.

**Repro:** fresh browser profile → open the printed `?launch=` URL → shell loads,
all tabs empty; any `/memory-view/...` or `/api/...` → 401.

**Expected:** a coherent auth model where the browser can actually call the API:
e.g. server accepts the SameSite=Strict HttpOnly session cookie for GET routes and
cookie + custom `X-…` header for state-changing/XHR routes (CSRF-safe without
exposing the Bearer to JS), Bearer header kept for CLI/tools; `core.js` drops the
localStorage token entirely and purges stale `panel_token`; error texts reference
real commands; the binding e2e must drive the real JS client (or a faithful
simulation of cookie+header behavior).

**Notes:** found during operator live review of the v0.1.11 panel; v0.1.11 shipped
the regression half, the plain-fetch and memory-view halves predate it. No
operator-local data in this record.

**Resolution (v0.1.13 window, live-review commits `9d02f7f`/`ab859c7` — solved
outside the release's folded bug table):** the operator killed panel auth entirely
for the loopback boundary — token/cookie machinery removed; the only residual guard
is a Host-header allowlist (DNS-rebinding protection, not authentication) in
`features/panel/handler.py`. Browser API calls work with zero credential; the
incoherent cookie/Bearer/localStorage triangle no longer exists. Verified present in
the working tree at v0.1.13 closure.
