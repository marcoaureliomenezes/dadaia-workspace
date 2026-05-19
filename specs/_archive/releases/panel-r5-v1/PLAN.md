# PLAN — Release `panel-r5-v1`

**Status:** Aprovado
**Release ID:** panel-r5-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** PLAN

---

## Strategy

Five phases, A through E, each individually merge-able. The release moves outward in
concentric rings from pure backend logic to the full multi-runtime UI:

A → aggregator + adapter (no API surface) → B → endpoints → C → Claude Sessions UI →
D → global switcher + retrofit Agents/Workflows → E → Codex live.

No phase introduces a "big bang". Phases A and B are backend-pure and reversible.
Phase C is the first user-visible delta. Phases D and E layer the multi-runtime
behaviour on top.

---

## Phase A — Aggregator + RuntimeAdapter

**Layers affected:** `dadaia_workspace/features/telemetry/aggregator/` (extend),
`tests/unit/features/telemetry/` (new tests).

**Files**

| File | Action |
|---|---|
| `dadaia_workspace/features/telemetry/aggregator/models.py` | Extend — add `SessionRow`, `SessionDetail`, `SessionListResult` frozen dataclasses |
| `dadaia_workspace/features/telemetry/aggregator/queries.py` | Extend — add `list_sessions(runtime, project, limit)` and `get_session(runtime, session_id)` methods to `TelemetryAggregator` |
| `dadaia_workspace/features/telemetry/aggregator/runtimes.py` | New — `RuntimeAdapter` protocol + `ClaudeRuntimeAdapter`, `CodexRuntimeAdapter` |
| `tests/unit/features/telemetry/test_aggregator_sessions.py` | New — covers `list_sessions` (with `project`/`limit` filters) and `get_session` |
| `tests/unit/features/telemetry/test_runtime_adapters.py` | New — covers both adapters with stub raw rows |

**Done when:** unit tests green; `dadaia panel start` still boots cleanly; the existing
`/api/agents` and `/api/workflows` endpoints behave identically (no observable change).

---

## Phase B — `/api/sessions` endpoints

**Phase prerequisite:** Phase A merged.

**Layers affected:** `dadaia_workspace/features/panel/views/api.py` (extend),
`dadaia_workspace/features/panel/handler.py` (extend), `dadaia_workspace/container.py`
(extend), `tests/unit/features/panel/` (new), `tests/integration/` (new),
`tests/fixtures/telemetry/` (new fixture).

**Files**

| File | Action |
|---|---|
| `dadaia_workspace/features/panel/views/api.py` | Extend — add `render_api_sessions(service)` and `render_api_session_detail(service)` closure factories |
| `dadaia_workspace/features/panel/handler.py` | Extend — register `api_sessions` and `api_session_detail` in `_RAW_ROUTES`; add to `_BEARER_AUTH_ROUTE_NAMES`; extend `_dispatch_telemetry` switch |
| `dadaia_workspace/container.py` | Extend — wire the two new view callables into `build_panel_views` return dict |
| `tests/unit/features/panel/test_views_api_sessions.py` | New — covers envelope shape, auth missing → 401, telemetry unavailable → 503 |
| `tests/integration/test_panel_sessions_endpoint.py` | New — uses fixture `tests/fixtures/telemetry/sessions_seeded.sqlite` |
| `tests/fixtures/telemetry/sessions_seeded.sqlite` | New — small seeded SQLite with both Claude and Codex rows |

**Done when:** `curl -H "Authorization: Bearer …" http://127.0.0.1:4999/api/sessions?runtime=claude`
returns the expected envelope (`200` + sessions array) and unit + integration tests
are green.

---

## Phase C — Frontend Sessions tab (Claude-only path live)

**Phase prerequisite:** Phase B merged.

**PREREQUISITE FOR PHASE C MERGE:**

- **PR4-08** (backfill impl) DONE — script
  `scripts/backfill_telemetry_agent_name.py` landed on `release/panel-r4-v1`.
- **PR4-09** (backfill executed) DONE — verified by:
  ```
  sqlite3 ~/.dadaia/state/telemetry/telemetry.sqlite \
    "SELECT COUNT(*) FROM sessions WHERE agent_name IS NOT NULL"
  ```
  returns ≥ 50.
- **PR4-10** (integration test) DONE —
  `tests/integration/test_telemetry_end_to_end_aggregation.py` pytest green.

**Layers affected:** `dadaia_workspace/features/panel/views/` (new view, new CSS,
new JS), `tests/e2e/` (new spec).

**Files**

| File | Action |
|---|---|
| `dadaia_workspace/features/panel/views/sessions.py` | New — `render_sessions_section() -> str` (HTML scaffold: filter + sortable table + drawer) |
| `dadaia_workspace/features/panel/views/assets/css/sessions.py` | New — `SESSIONS_CSS`: table styles, status dot, drawer transitions |
| `dadaia_workspace/features/panel/views/assets/js/sessions.js` | New — Sessions module: subscribe to `dadaia:runtime-change`, append `?runtime=` on `authedFetch`, render table, drawer detail, 10 s auto-refresh paused on `document.hidden` |
| `dadaia_workspace/features/panel/views/index.py` | Edit — nav-tab "Sessions" + `<section id="section-sessions">` |
| `dadaia_workspace/features/panel/views/static.py` | Edit — register `sessions.css` and `sessions.js` in `_ASSETS` |
| `tests/e2e/test_panel_sessions_tab.spec.ts` | New — Playwright e2e for Sessions tab populating, drawer opening, sorting, refresh badge |

**Done when:** e2e spec green; `dadaia panel` manual smoke shows real sessions from
the operator's `~/.claude/projects/` populated in the table; drawer opens on row
click; sort by Cost re-orders rows; "Last updated" badge ticks at ≤11 s.

---

## Phase D — Global runtime switcher + retrofit Agents + Workflows

**Phase prerequisite:** Phase C merged.

**Layers affected:** `dadaia_workspace/features/panel/views/assets/js/` (new runtime
module, edit agents + workflows), `dadaia_workspace/features/panel/views/index.py`
(topbar markup), `dadaia_workspace/features/panel/views/assets/css/tokens.py` (new
tokens), `dadaia_workspace/features/panel/views/api.py` (backend filter), `tests/e2e/`
(extend spec).

### REBASE NOTES — Phase D shared files with panel-r4-v1

Phase D edits four files that panel-r4-v1 has been actively modifying. r4 ships
first (it has the active release lock); r5 Phase D rebases on top. **Do not
clobber r4's deltas — layer on top.**

| File | r4 delta (already on `release/panel-r4-v1`) | r5 Phase D delta (additive) |
|---|---|---|
| `dadaia_workspace/features/panel/views/assets/js/agents.js` | PR4-18 wires `data-tier="${agent.tier}"` on each card element. | Subscribe to `dadaia:runtime-change`; drop cache + refetch with `?runtime=` appended. **Keep r4's `data-tier` line; add the runtime subscription on top.** |
| `dadaia_workspace/features/panel/views/assets/css/tokens.py` | PR4-18 adds 9 CSS custom properties `--color-tier-1/2/3` × Mint/Sage/Warm palettes. | Add 9 new tokens `--color-runtime-claude` / `--color-runtime-codex` / `--color-runtime-active` × the same 3 palettes. **Both blocks must coexist; do not replace either set.** |
| `dadaia_workspace/features/panel/views/api.py` | PR4-13 extends `render_api_agents_canonical` to include `tier: int` per agent. r5 Phase B will also have added closures `render_api_sessions` + `render_api_session_detail` to the same file. | Extend `render_api_agents_canonical` **again** to read `runtime = qs.get("runtime", "claude")` and filter by `provider`. **Order of merges:** r4 PR4-13 ships first (tier plumbing); r5 Phase B is additive (new closures); r5 Phase D layers `?runtime=` filtering on top of r4's `tier` output. |
| `tests/unit/features/panel/test_api_agents.py` | PR4-15/PR4-19 extend this test for `tier ∈ {1,2,3}` per agent. | Add `?runtime=` filter assertion (Codex-scoped response excludes Claude-only agents; default-no-param returns Claude-scoped data byte-identical to r4 shape). **Keep all r4 tier assertions intact; append the runtime assertions in a new test method.** |

**Files**

| File | Action |
|---|---|
| `dadaia_workspace/features/panel/views/assets/js/runtime.js` | New — `window.Runtime` global; `localStorage.dadaia-panel-runtime`; `document.documentElement.dataset.runtime`; emits `dadaia:runtime-change` `CustomEvent` |
| `dadaia_workspace/features/panel/views/index.py` | Edit — `.runtime-switcher` topbar markup beside the theme switcher |
| `dadaia_workspace/features/panel/views/assets/css/tokens.py` | Extend — `--color-runtime-claude` (warm gold), `--color-runtime-codex` (sage green), `--color-runtime-active` (set by JS); three palettes × three tokens = nine hex values |
| `dadaia_workspace/features/panel/views/assets/js/agents.js` | Edit — subscribe to `dadaia:runtime-change`, drop cache + refetch with `?runtime=` |
| `dadaia_workspace/features/panel/views/assets/js/workflows.js` | Edit — same retrofit as `agents.js` |
| `dadaia_workspace/features/panel/views/api.py` | Edit — `render_api_agents_canonical` and `render_api_workflows_list` read `runtime = qs.get("runtime", "claude")` and filter by `provider` |
| `dadaia_workspace/features/panel/views/static.py` | Edit — register `runtime.js` in `_ASSETS` |
| `tests/e2e/test_panel_sessions_tab.spec.ts` | Extend — three tabs × two runtimes matrix; localStorage persistence across reload |

**Done when:** flipping the topbar switcher reloads Agents, Workflows, and Sessions
tabs; the choice survives a full page reload (localStorage); the three-tab matrix
e2e is green; backward compat verified — `curl .../api/agents` (no `?runtime=`)
returns Claude-scoped data identical to today's shape.

---

## Phase E — Codex sub-tab live

**Phase prerequisite:** Phase D merged.

**Layers affected:** `dadaia_workspace/features/telemetry/aggregator/runtimes.py`
(flesh out `CodexRuntimeAdapter`), `dadaia_workspace/features/panel/views/assets/js/sessions.js`
(banner branch), `tests/integration/test_panel_sessions_endpoint.py` (extend with
Codex fixture rows).

**Files**

| File | Action |
|---|---|
| `dadaia_workspace/features/telemetry/aggregator/runtimes.py` | Edit — flesh out `CodexRuntimeAdapter.liveness` (history.jsonl tail + `threads.archived` flag + `threads.updated_at` delta) and `enrich_row` (`cumulative_cost_usd = None`, `cost_known = False`) |
| `dadaia_workspace/features/panel/views/assets/js/sessions.js` | Edit — when active runtime is `codex`, render banner "Cost not tracked for Codex" + render Cost cells as `—` per row |
| `tests/integration/test_panel_sessions_endpoint.py` | Extend — Codex fixture rows from `sessions_seeded.sqlite` asserting `cumulative_cost_usd is None` and `cost_known is False` |
| `tests/fixtures/telemetry/sessions_seeded.sqlite` | Edit — add Codex rows if not seeded in Phase B |

**Done when:** integration test green with Codex assertions; `dadaia panel` manual
smoke against operator's live `~/.codex/state_5.sqlite` shows real threads, the
banner present, Cost cells `—`, status dots reflecting `threads.archived` /
`updated_at` delta correctly.

---

## Validation plan

Five validation surfaces, in order:

1. **Backend unit tests**
   ```
   .dadaia/.venv/bin/python -m pytest \
     tests/unit/features/telemetry/test_aggregator_sessions.py \
     tests/unit/features/telemetry/test_runtime_adapters.py \
     tests/unit/features/panel/test_views_api_sessions.py -v
   ```
2. **Integration**
   ```
   .dadaia/.venv/bin/python -m pytest tests/integration/test_panel_sessions_endpoint.py -v
   ```
3. **API smoke** (after Phase B and after Phase E)
   ```
   curl -s -H "Authorization: Bearer $(cat ~/.dadaia/state/panel.token)" \
     http://127.0.0.1:4999/api/sessions?runtime=claude | jq '.sessions | length'
   ```
4. **E2E** (after Phase C, extended in Phase D)
   ```
   .dadaia/.venv/bin/python -m pytest tests/e2e/test_panel_sessions_tab.spec.ts
   ```
5. **SDD gates**
   ```
   dadaia specs doctor   # green
   dadaia public doctor  # green
   ```

---

## Technical risks

- **`compute_cost` API drift.** If `pricing.compute_cost(usage, model, when_date) ->
  micro_usd` signature changes during this release window,
  `ClaudeRuntimeAdapter.enrich_row` breaks. Mitigation: pin tests on the public API
  in Phase A; signal a re-plan if it changes.
- **Backfill non-completion (panel-r4-v1 FR1).** Phase C is blocked until the 50
  NULL `sessions.agent_name` rows are populated. Mitigation: verification step is a
  hard precondition of Phase C in the table above.
- **Codex `history.jsonl` schema drift.** If OpenAI changes the `ts` field or
  rotates the file, `CodexRuntimeAdapter.liveness` becomes brittle. Mitigation:
  Phase E adapter wraps the read in a try/except and falls back to `idle` on
  parse failure — operator-visible but non-crashing.
- **localStorage key clash.** `dadaia-panel-runtime` is a new key; verify no
  existing key with the same name in the panel before Phase D land.

---

## Parallelism notes

Phases are sequential (each is a prerequisite of the next), but within Phase C and
Phase D, FE-impl work and qa-engineer e2e spec authoring have **disjoint write
sets** (production code under `features/panel/views/` vs spec under `tests/e2e/`).
Per CLAUDE.md §9 and the panel-r4-v1 P1/P2 parallel-window precedent, these may
hold two `[-]` markers simultaneously when TASKS.md explicitly declares the
parallel window. See TASKS.md for the explicit per-task declarations.

Phases A, B, and E are single-threaded — backend changes inside a single test
fixture and adapter set; the marginal cost of parallelism is not worth the
coordination overhead.

---

## Out-of-scope (re-asserted from SPEC §4)

- Synthetic Codex cost estimation
- True user-message count metric
- Per-tab runtime independence
- A new `features/sessions/` package
- A new `SessionReader` abstraction
