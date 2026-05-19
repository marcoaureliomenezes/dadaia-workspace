# SPEC — Release `panel-r5-v1`

**Status:** Aprovado
**Release ID:** panel-r5-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** SPEC

---

## 1. Context

The operator drives this workspace daily through **two** AI coding runtimes — Claude
Code and OpenAI Codex CLI — but `dadaia panel` exposes Claude data only, and exposes it
exclusively through the Agents, Workflows, and Servers tabs. Two observability gaps
result:

1. **No session-level view.** Token consumption and cost-per-session exist in the
   telemetry store at `~/.dadaia/state/telemetry/telemetry.sqlite` (populated by
   `dadaia_workspace/features/telemetry/reader/claude.py` from
   `~/.claude/projects/**/*.jsonl` and by `dadaia_workspace/features/telemetry/reader/codex.py`
   from `~/.codex/state_5.sqlite::threads`), but the panel has no surface that answers
   *"which session is eating my context?"* or *"how much have I spent today across both
   runtimes?"*.
2. **No runtime selector.** Even where Codex telemetry is ingested, the panel cannot
   pivot between *"show me Codex"* and *"show me Claude"*. CLAUDE.md §9 already
   declares the workspace multi-runtime; the panel must mirror that.

The architectural seam is the **aggregator output**, not a new feature package. The
`sessions`, `agents`, and `events` tables already carry a `provider IN ('claude','codex')`
discriminator; the pricing function `compute_cost(usage, model, when_date) -> micro_usd`
already lives at `dadaia_workspace/features/telemetry/pricing.py`. This release extends
`TelemetryAggregator` with session-level queries, introduces a per-runtime adapter
registry to handle Claude vs Codex differences (Claude has per-event tokens+cost; Codex
has only pre-aggregated `tokens_used` with `cost_micro_usd = NULL`), exposes the
results through two new bearer-authed endpoints, and adds a Sessions panel tab plus a
global runtime switcher.

**Hard dependency (refined 2026-05-19):** the panel-r4-v1 reader patch
(PR4-06/PR4-07 — `agent_name` extraction from `subagent_type`) has already
landed on `release/panel-r4-v1`. The remaining blocker for this release's
Phase C/D merge is the **trio PR4-08 (idempotent backfill impl) + PR4-09
(backfill executed against `~/.dadaia/state/telemetry/telemetry.sqlite`) +
PR4-10 (integration test green)**. Without that trio, `list_sessions` works
mechanically but the agent-name column on the Sessions table is sparse for
historical rows — which the operator has already classified as "not the
reality" in panel-r4-v1 §1.

---

## 2. Functional Requirements (FR)

### FR1 — `TelemetryAggregator.list_sessions` + `get_session`

Extend `TelemetryAggregator` (`dadaia_workspace/features/telemetry/aggregator/queries.py`)
with two new pure-query methods:

- `list_sessions(runtime: str, project: str | None = None, limit: int | None = None) -> SessionListResult`
  — returns a list of `SessionRow` for the requested runtime, optionally filtered by
  project slug, capped at `limit`.
- `get_session(runtime: str, session_id: str) -> SessionDetail | None` — returns the
  enriched detail for a single session, or `None` if not found.

New frozen dataclasses in
`dadaia_workspace/features/telemetry/aggregator/models.py`:

- `SessionRow` — fields: `session_id`, `runtime`, `project`, `cwd`, `model`,
  `started_at`, `last_activity_at`, `message_count`, `context_size_tokens`,
  `cumulative_cost_usd` (Optional[float]), `cost_known` (bool), `status`
  (`"active"|"idle"|"ended"`), `agent_name` (Optional[str]), `ai_title` (Optional[str]).
- `SessionDetail` — `SessionRow` plus full event timeline references.
- `SessionListResult` — wraps `sessions: list[SessionRow]` plus query metadata
  (runtime, project, limit, generated_at).

**Locked formulas (no grill):**

- `context_size_tokens = input_tokens + cache_creation_input_tokens + cache_read_input_tokens`
  of the most recent assistant event for the session (the working set the model
  received; naked `input_tokens` is misleading once cache warms).
- `message_count` is rendered as **"AI Turns"** = `COUNT(events)` for the session.
  The events table stores only assistant turns; honest naming avoids user-message
  confusion.

**Coverage:** `tests/unit/features/telemetry/test_aggregator_sessions.py` covers both
queries, including the `limit`/`project` filters and the `runtime` discriminator.

### FR2 — `RuntimeAdapter` protocol with Claude + Codex implementations

New file `dadaia_workspace/features/telemetry/aggregator/runtimes.py`:

- `RuntimeAdapter` protocol with three methods:
  - `enrich_row(row: SessionRow, raw: dict) -> SessionRow`
  - `enrich_detail(detail: SessionDetail, raw: dict) -> SessionDetail`
  - `liveness(session_id: str, cwd: str) -> Literal["active", "idle", "ended"]`
- `ClaudeRuntimeAdapter` — liveness reads `~/.claude/sessions/*.json`; enrichment
  computes `cumulative_cost_usd` via `pricing.compute_cost` and sets
  `cost_known = True`.
- `CodexRuntimeAdapter` — liveness queries `threads.updated_at` from
  `~/.codex/state_5.sqlite` and tails `~/.codex/history.jsonl` for `ts` delta;
  enrichment sets `cumulative_cost_usd = None` and `cost_known = False`.

The `TelemetryAggregator` resolves the right adapter via a `{runtime: adapter}` dict
and delegates enrichment per row before returning the dataclass.

**Coverage:** `tests/unit/features/telemetry/test_runtime_adapters.py` covers both
adapters with stub raw rows.

### FR3 — `/api/sessions` and `/api/sessions/<runtime>/<session_id>` endpoints

Two new HTTP routes registered through the existing panel handler pattern:

- `GET /api/sessions?runtime=claude|codex[&project=<slug>][&limit=<n>]`
- `GET /api/sessions/<runtime>/<session_id>`

Implementation:

- Closure factories `render_api_sessions(service)` and `render_api_session_detail(service)`
  in `dadaia_workspace/features/panel/views/api.py`, following the existing
  `render_api_agents_canonical` / `render_api_workflows_list` convention.
- Route registration in `dadaia_workspace/features/panel/features/panel/handler.py`'s
  `_RAW_ROUTES`; auth registration in `_BEARER_AUTH_ROUTE_NAMES`; switch entry in
  `_dispatch_telemetry`.
- View registration in `dadaia_workspace/container.py::build_panel_views`.
- Response envelope is the standard `200/401/503` pattern produced by the existing
  `_envelope()` helper. No new envelope shape.

`SessionRow` JSON shape:
`{session_id, runtime, project, cwd, model, started_at, last_activity_at, message_count,
context_size_tokens, cumulative_cost_usd, cost_known, status, agent_name, ai_title}`.

**Coverage:** unit test `tests/unit/features/panel/test_views_api_sessions.py` plus
integration test `tests/integration/test_panel_sessions_endpoint.py` consuming
fixture `tests/fixtures/telemetry/sessions_seeded.sqlite`.

### FR4 — Sessions panel tab (table, sortable, drawer)

New panel surface implemented as a table — not cards — because the data is
comparison-oriented and numeric.

- New view module `dadaia_workspace/features/panel/views/sessions.py` exporting
  `render_sessions_section() -> str` (HTML scaffold: filter input + sortable table +
  detail drawer).
- New CSS module `dadaia_workspace/features/panel/views/assets/css/sessions.py`
  (`SESSIONS_CSS`: table styles, status dot, drawer transitions).
- New JS module `dadaia_workspace/features/panel/views/assets/js/sessions.js`:
  - Subscribes to `dadaia:runtime-change` (see FR5).
  - On fetch: appends `?runtime=` + `Runtime.get()` to `authedFetch` calls.
  - Renders the table; row click opens the drawer populated from
    `/api/sessions/<runtime>/<session_id>`.
  - 10-second auto-refresh interval, **paused when `document.hidden` is true**.
- Nav-tab edit in `dadaia_workspace/features/panel/views/index.py`: add "Sessions" to
  the nav strip and a `<section id="section-sessions">` container.
- Asset registration in `dadaia_workspace/features/panel/views/static.py`: register
  `sessions.css` and `sessions.js` in `_ASSETS`.

The `ai_title` field is surfaced in the Session column tooltip (operator-generated
text, complementary to the `session_id[:8]` slug).

**Coverage:** Playwright e2e spec `tests/e2e/test_panel_sessions_tab.spec.ts`.

### FR5 — Global runtime switcher + retrofit of Agents and Workflows tabs

A single, global runtime selector — not per-tab — persisted to `localStorage` so the
operator's choice survives reload.

- New JS module `dadaia_workspace/features/panel/views/assets/js/runtime.js` exposing
  `window.Runtime`:
  - `Runtime.get() -> "claude" | "codex"` (default `"claude"`).
  - `Runtime.set(value)` — writes to `localStorage` and emits a
    `dadaia:runtime-change` `CustomEvent`.
  - Reads/writes the localStorage key **`dadaia-panel-runtime`**, mirroring the
    existing theme switcher pattern (`views/index.py:60`).
  - Sets `document.documentElement.dataset.runtime` for CSS targeting.
- Topbar markup in `dadaia_workspace/features/panel/views/index.py`: add
  `.runtime-switcher` control next to the theme switcher.
- New CSS tokens in `dadaia_workspace/features/panel/views/assets/css/tokens.py`:
  `--color-runtime-claude` (warm gold), `--color-runtime-codex` (sage green),
  `--color-runtime-active` (set by JS via `data-runtime`). Three tokens × three
  palettes (Mint / Sage / Warm) = nine hex values, all WCAG 2.2 AA against the
  topbar background.
- Retrofit `dadaia_workspace/features/panel/views/assets/js/agents.js` and
  `dadaia_workspace/features/panel/views/assets/js/workflows.js`:
  - Subscribe to `dadaia:runtime-change`.
  - On change: drop cache + refetch with `?runtime=` appended.
- Backend filter plumbing in `dadaia_workspace/features/panel/views/api.py`:
  - `render_api_agents_canonical` reads `runtime = qs.get("runtime", "claude")`
    and filters by `provider`.
  - `render_api_workflows_list` does the same.
  - When `?runtime=` is omitted, **default to `claude`** (backward compatibility:
    existing operator scripts that call `/api/agents` without the query-param
    continue to receive Claude-scoped data).

**Coverage:** the Playwright e2e is extended to cover all three tabs × both
runtimes plus localStorage persistence across page reload.

### FR6 — Codex sub-tab live with "Cost not tracked for Codex" banner

The Codex side of the switcher must show real threads, not a placeholder.

- `CodexRuntimeAdapter` (FR2) is fleshed out: history.jsonl tail for liveness
  delta, `threads.archived` flag → `status = "ended"`, `threads.updated_at` delta
  classified into `active`/`idle`.
- The frontend `sessions.js` renders a top-of-table banner — *"Cost not tracked for
  Codex"* — when the active runtime is `codex`. Cost cell displays `—` per row.
- Integration test `tests/integration/test_panel_sessions_endpoint.py` is extended
  with Codex fixture rows (sourced from
  `tests/fixtures/telemetry/sessions_seeded.sqlite`) asserting `cumulative_cost_usd`
  is `None` and `cost_known` is `False`.

---

## 3. Non-Functional Requirements (NFR)

### NFR1 — Telemetry refresh stays inside the existing 30 s cache TTL

`list_sessions` and `get_session` operate inside the same telemetry refresh pipeline
that already governs `/api/agents`. No new daemon, no new background process, no
competing cache. `features/telemetry/budget.CACHE_TTL_SECONDS` remains the single
source of truth for refresh cadence.

### NFR2 — No SPA framework added

Frontend remains vanilla JS + Python-generated CSS. No React, no Vue, no build step.
The Sessions tab mirrors the existing `agents.js`/`workflows.js` table-render and
auto-refresh patterns.

### NFR3 — localStorage key `dadaia-panel-runtime`

The runtime switcher key is exactly `dadaia-panel-runtime`, mirroring the theme
switcher pattern. The key is documented in CLOSURE.md for forward maintenance.

### NFR4 — 10 s sessions auto-refresh, paused when `document.hidden`

`sessions.js` runs a 10-second auto-refresh loop. The loop checks `document.hidden`
before each tick; when the tab is backgrounded, the refresh is suspended (avoids
needless telemetry hits and battery drain on the operator's laptop).

### NFR5 — Backward compatibility for `/api/agents` and `/api/workflows`

When the new `?runtime=` query-param is **omitted**, both endpoints default to
`runtime = "claude"`. Existing operator scripts and tooling that call
`/api/agents` or `/api/workflows` without the new param continue to receive the same
Claude-scoped response shape they receive today.

### NFR6 — Bearer auth and 200/401/503 envelope reused

The two new endpoints register in `_BEARER_AUTH_ROUTE_NAMES`. The handler-level
envelope (`200` success / `401` unauthorized / `503` telemetry unavailable) is reused
unchanged. No new auth path.

### NFR7 — Each phase ships on its own

Phases A → E (per PLAN.md) are individually merge-able and don't form a big-bang
release. Phase A is backend-pure and changes no API surface; Phase B exposes the
endpoints but no UI consumes them yet; Phase C ships Claude-only Sessions; Phase D
adds the switcher and retrofits the other tabs; Phase E lights up Codex.

---

## 4. Out of Scope

The following are explicitly excluded from this release and will not appear in PLAN
or TASKS:

- **Synthetic Codex cost estimation.** `cumulative_cost_usd` for Codex stays
  `None` and `cost_known = False`. A future release may add
  `compute_cost_codex(thread)` to `pricing.py` and flip `cost_known = True`; not now.
- **True user-message count.** `message_count` is `COUNT(events)` ("AI Turns"). A
  true user-message count would require re-parsing JSONL line counts, which is
  expensive and deferred unless requested.
- **Per-tab runtime independence.** The runtime selector is global. If the operator
  later wants Agents on Claude while Sessions on Codex, that is a new release.
- **A `features/sessions/` package.** The architectural seam is the aggregator
  output; no new feature package is introduced.
- **A `SessionReader` abstraction.** Reading remains in the existing
  `features/telemetry/reader/*.py` modules; only the aggregator output evolves.

---

## 5. Acceptance Criteria

The release is shippable when ALL of the following are demonstrably true:

1. **Backend unit tests green** for `test_aggregator_sessions.py`,
   `test_runtime_adapters.py`, `test_views_api_sessions.py`.
2. **Integration test green** for `test_panel_sessions_endpoint.py` against the
   seeded fixture, including Codex fixture rows showing `cumulative_cost_usd = None`
   and `cost_known = False`.
3. **API smoke** — `curl -s -H "Authorization: Bearer $(cat ~/.dadaia/state/panel.token)"
   http://127.0.0.1:4999/api/sessions?runtime=claude | jq '.sessions | length'`
   returns a positive integer.
4. **E2E green** for `tests/e2e/test_panel_sessions_tab.spec.ts` covering: Sessions
   tab populates with real Claude sessions; switching runtime to Codex re-renders
   the table with the cost banner and `—` cells; reloading the page preserves the
   runtime selection (localStorage); clicking a row opens the drawer; sorting by
   Cost (desc) re-orders the rows; the "Last updated" badge ticks at ≤11 s.
5. **Three-tab × two-runtime matrix** verified: toggling the switcher reloads the
   Agents tab, the Workflows tab, AND the Sessions tab. Each tab respects the
   `?runtime=` filter on its API path.
6. **`dadaia specs doctor`** green.
7. **`dadaia public doctor`** green.
8. **CLOSURE.md** authored with: tasks completed table, validation evidence triples,
   any drifts documented, and the explicit memory-update list (catalog entry for
   Sessions tab; runtime-switcher mention in product index; architecture.html if
   the `RuntimeAdapter` placement changes the layer description).

---

## 6. Dependencies & Risks

### Hard dependencies

- **`panel-r4-v1` PR4-08 + PR4-09 + PR4-10.** PR4-06/PR4-07 (Claude reader
  ingestion of `agent_name`) have already shipped on the r4 branch (commits
  `2918e4c` and earlier). The remaining merge blocker for r5 Phases C and D is
  the trio:
  - **PR4-08** — idempotent backfill implementation
    (`scripts/backfill_telemetry_agent_name.py`) committed.
  - **PR4-09** — backfill executed against
    `~/.dadaia/state/telemetry/telemetry.sqlite`, verified by
    `sqlite3 ~/.dadaia/state/telemetry/telemetry.sqlite "SELECT COUNT(*) FROM
    sessions WHERE agent_name IS NOT NULL"` returning ≥ 50.
  - **PR4-10** — integration test
    `tests/integration/test_telemetry_end_to_end_aggregation.py` green.

  Without this trio, `list_sessions` returns rows whose `agent_name` column is
  largely `NULL` for historical sessions, reproducing the panel-r4-v1 "not the
  reality" complaint inside the new Sessions tab.
- **`features/telemetry/pricing.py::compute_cost`** must remain stable in signature
  during this release; the `ClaudeRuntimeAdapter` calls it directly.
- **Existing telemetry refresh pipeline** (the 30 s cache window managed by
  `features/telemetry/budget.CACHE_TTL_SECONDS`) — this release does not modify it.

### Risks (operator can override at any phase)

1. **`context_size_tokens` formula** is locked to
   `input + cache_creation + cache_read`. If the operator prefers naked
   `input_tokens` after smoke testing, swap is a one-line change in
   `ClaudeRuntimeAdapter.enrich_row`.
2. **Codex cost stays `None`** by design. If the operator later wants a synthetic
   estimate, add `compute_cost_codex(thread)` to `pricing.py` and flip
   `cost_known = True` — single-PR change.
3. **Runtime toggle is global, not per-tab.** If the operator pushes for per-tab
   during smoke testing, drop the `dadaia:runtime-change` event and switch to
   per-tab localStorage keys.
4. **`message_count` = assistant events only** ("AI Turns"). True user-message
   count is deferred.
5. **Codex liveness uses `history.jsonl` tail + `threads.updated_at` delta.** A
   long-running Codex tool-call may appear "idle"; acceptable for v1.
6. **Backward compatibility** — the `?runtime=` default of `claude` is a
   compatibility guarantee. Removing the default in a later release is a breaking
   change and must go through its own release cycle.
