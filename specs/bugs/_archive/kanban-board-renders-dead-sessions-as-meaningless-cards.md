---
name: kanban-board-renders-dead-sessions-as-meaningless-cards
status: Closed
severity: MEDIUM
session_id: null
reported: 2026-06-11
surface: features/panel/views/kanban.py + assets/js/kanban.js (GET /api/kanban)
---

**Symptom:** The Agentic-tab Kanban board is meaningless. Cards render as
`sess_xxxx / unknown / unknown · 9h ago`. The live workspace shows 3 cards in the
Backlog column and 3 in Implementation+Review for `dadaia-workspace`, none of which
correspond to a running session or the context's real lifecycle state. Operator
verdict: "I can't understand why there are 3 cards in implementation … THIS KANBAN
BOARD SUCKS AND DON'T WORK."

**Repro:**
1. `dadaia panel`, open the Agentic → Kanban tab on a workspace with stale session
   records under `.dadaia/sessions/*.json` (sessions whose pid is dead and whose
   `last_seen_at` is hours old).
2. Observe every session record rendered as a card regardless of liveness; the card
   body shows the `runtime` field twice (`"unknown"` in every record) and never the
   mode or release.

**Root cause:**
- `render_api_kanban` (views/kanban.py) emits **every** parseable session record as a
  card. It computes `is_stale` via `is_stale_session` (TTL-only, no pid probe) but
  never *filters* stale/dead sessions out — they pile up forever until the records are
  GC'd. No `OsProcessProbe` is consulted, so a record whose `last_seen_at` is within
  TTL but whose pid is long dead still renders.
- `buildCardHtml` (kanban.js) renders `card.runtime` twice and never renders `mode` or
  `release`. Session records carry `runtime: "unknown"` (the bind CLI never resolves the
  harness), so both meta lines literally read `unknown` and the detail line reads
  `unknown · <age>`.
- Swimlanes are derived from "whatever contexts have session files", not from the ALIVE
  Spec Context registry, and no card ever reflects the context's real release+phase from
  `repos/<slug>/specs/releases/ACTIVE.md`.

**Expected:** One swimlane per ALIVE Spec Context. The context's active release+phase
(from its `ACTIVE.md`) is the primary card in the matching lifecycle column. Session
cards appear only for **live** sessions (recorded pid alive OR heartbeat fresh) and show
meaningful text (mode, release if bound, relative age) — never the literal string
"unknown". Dead/stale session records are not cards.

**Notes:** No approved release TASKS.md task covered this Kanban rewrite at fix time;
fixed under a direct operator panel-review demand. Tests + view + JS updated; e2e
fragment under `tests/e2e/` is qa-engineer-owned and was not modified by the implementer.


**Resolution (2026-06-11, same-day fix):** kanban-v2 lifecycle board (views/kanban.py rewrite: ACTIVE.md release cards, pid-veto live-session filter, observers strip); verified live in browser + unit suites green.
