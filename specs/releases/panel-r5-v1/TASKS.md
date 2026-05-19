# TASKS — Release `panel-r5-v1`

**Status:** Aprovado
**Release ID:** panel-r5-v1
**Owner:** product-engineer
**Created:** 2026-05-19
**Phase:** TASKS

> Markers per `dadaia-task-manager` skill:
> `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE
> Invariant: **only one `[-]` at a time per TASKS.md, EXCEPT** for the explicitly
> declared parallel windows in Phases C and D — those windows have disjoint write
> sets (production code under `features/panel/views/` vs e2e specs under
> `tests/e2e/`) and may hold two `[-]` simultaneously.
>
> Phase order is strict: A → B → C → D → E. Each phase must reach all-`[x]` before
> the next opens. Phase C is additionally gated on the panel-r4-v1 trio
> **PR4-08 + PR4-09 + PR4-10** being all-`[x]` and the SQLite count probe
> (`SELECT COUNT(*) FROM sessions WHERE agent_name IS NOT NULL`) returning ≥ 50.

---

## P0 — Foundation *(product-engineer)*

- [x] **PR5-01** — Cut branch `release/panel-r5-v1` from `main`. Owner:
  product-engineer. Done criterion: `git rev-parse --abbrev-ref HEAD` returns
  `release/panel-r5-v1` and branch base = `main`. **Done** at commit `a5e4373`
  (cut from `release/panel-r4-v1` tip since r5 depends on r4 ingestion
  PR4-08+09+10; r4 is archived).
- [x] **PR5-02** — Maintain `specs/releases/ACTIVE.md` synchronized through the
  release lifecycle. Owner: product-engineer. Sequence: operator flips ACTIVE.md
  from `panel-r4-v1` to `panel-r5-v1, phase: SPEC` only AFTER panel-r4-v1 reaches
  ARCHIVED. Then `phase: PLAN` → `phase: TASKS` → `phase: IMPLEMENTATION` →
  `phase: CLOSURE` → `phase: ARCHIVED` at the end. Done criterion: ACTIVE.md
  always matches the live phase of this release. **Done** — ACTIVE.md now at
  `release: panel-r5-v1, phase: IMPLEMENTATION`.
- [x] **PR5-03** — Land `specs/releases/panel-r5-v1/SPEC.md` with `**Status:**
  Aprovado`. Owner: product-engineer. Done criterion: file present, header
  carries the Aprovado status line, 6 mandatory sections (Context, FR, NFR, Out
  of Scope, Acceptance Criteria, Dependencies & Risks) all populated.
- [x] **PR5-04** — Land `specs/releases/panel-r5-v1/PLAN.md` with `**Status:**
  Aprovado`. Owner: product-engineer. Done criterion: file present, header
  carries the Aprovado status line, all sections populated, ≤ 300 lines.
- [x] **PR5-05** — Land `specs/releases/panel-r5-v1/TASKS.md` with `**Status:**
  Aprovado`. Owner: product-engineer. Done criterion: file present, header
  carries the Aprovado status line, every task has a Done criterion line.
- [x] **PR5-06** — Emit P0 handoff report at
  `.dadaia/reports/dadaia-workspace/product-engineer/<UTC>-panel-r5-v1-foundation.html`
  with adjacent `.handoff.json` sidecar per `dadaia-handoff-emitter` skill.
  Owner: product-engineer. Done criterion: report HTML + sidecar present;
  sidecar validates against `handoff-v1` schema. **Done** —
  `2026-05-19T180000Z-panel-r5-v1-foundation.html` + sidecar at workspace-root
  `.dadaia/reports/`.

---

## Phase A — Aggregator + RuntimeAdapter *(software-engineer)*

> **Single-threaded.** Write set: `dadaia_workspace/features/telemetry/aggregator/`,
> `tests/unit/features/telemetry/`. One `[-]` at a time across Phase A.

- [x] **PR5-A1** — Extend
  `dadaia_workspace/features/telemetry/aggregator/models.py` with three frozen
  dataclasses: `SessionRow` (fields per SPEC §FR1), `SessionDetail` (extends
  `SessionRow`), `SessionListResult` (wraps `sessions: list[SessionRow]` + query
  metadata). Owner: software-engineer. Done criterion: the three dataclasses
  import cleanly from `aggregator.models`; existing tests of `models.py` remain
  green.
- [x] **PR5-A2** — Extend
  `dadaia_workspace/features/telemetry/aggregator/queries.py` with two new
  methods on `TelemetryAggregator`: `list_sessions(runtime, project=None,
  limit=None) -> SessionListResult` and `get_session(runtime, session_id) ->
  SessionDetail | None`. Mirror the patterns of the existing `recent_sessions`
  and `agent_summary` queries. Owner: software-engineer. Done criterion: both
  methods callable from an instance; `list_sessions` honors `project` and
  `limit`; `get_session` returns `None` for unknown ids.
- [x] **PR5-A3** — Create new file
  `dadaia_workspace/features/telemetry/aggregator/runtimes.py` defining the
  `RuntimeAdapter` protocol with `enrich_row`, `enrich_detail`, and
  `liveness(session_id, cwd)`. Add stub `ClaudeRuntimeAdapter` and
  `CodexRuntimeAdapter` implementations: Claude wires `pricing.compute_cost`
  for `cumulative_cost_usd` and reads `~/.claude/sessions/*.json` for liveness;
  Codex stubs return `cumulative_cost_usd = None, cost_known = False`
  (full liveness implementation lives in Phase E). Owner: software-engineer.
  Done criterion: protocol importable; both adapters instantiable; smoke-import
  passes.
- [x] **PR5-A4** — Author unit test
  `tests/unit/features/telemetry/test_aggregator_sessions.py` covering
  `list_sessions` (with and without `project` and `limit` filters; per-runtime
  discriminator) and `get_session` (hit + miss). Owner: software-engineer. Done
  criterion: `.dadaia/.venv/bin/python -m pytest
  tests/unit/features/telemetry/test_aggregator_sessions.py -v` green.
- [x] **PR5-A5** — Author unit test
  `tests/unit/features/telemetry/test_runtime_adapters.py` covering
  `ClaudeRuntimeAdapter.enrich_row` (cost computed via `pricing.compute_cost`)
  and `CodexRuntimeAdapter.enrich_row` (`cumulative_cost_usd is None`,
  `cost_known is False`). Owner: software-engineer. Done criterion:
  `.dadaia/.venv/bin/python -m pytest
  tests/unit/features/telemetry/test_runtime_adapters.py -v` green; `dadaia
  panel start` still boots without error.

---

## Phase B — `/api/sessions` endpoints *(software-engineer)*

> **Phase prerequisite:** Phase A all-`[x]`.
> **Single-threaded.** Write set: `dadaia_workspace/features/panel/views/api.py`,
> `dadaia_workspace/features/panel/handler.py`, `dadaia_workspace/container.py`,
> `tests/unit/features/panel/`, `tests/integration/`,
> `tests/fixtures/telemetry/`.

- [x] **PR5-B1** — Extend
  `dadaia_workspace/features/panel/views/api.py` with closure factories
  `render_api_sessions(service)` and `render_api_session_detail(service)`
  following the existing `render_api_agents_canonical` /
  `render_api_workflows_list` convention. Owner: software-engineer. Done
  criterion: both closures return the standard 200/401/503 envelope shape; unit
  smoke import passes.
- [x] **PR5-B2** — Register the new routes in
  `dadaia_workspace/features/panel/handler.py`: add `api_sessions` and
  `api_session_detail` to `_RAW_ROUTES`; add both to
  `_BEARER_AUTH_ROUTE_NAMES`; extend `_dispatch_telemetry` switch with the new
  cases. Wire the view callables into
  `dadaia_workspace/container.py::build_panel_views`. Owner: software-engineer.
  Done criterion: hitting `/api/sessions?runtime=claude` without a bearer token
  returns `401`; with a valid bearer returns `200` and a JSON envelope; same for
  `/api/sessions/<runtime>/<session_id>`.
- [-] **PR5-B3** — Author unit test
  `tests/unit/features/panel/test_views_api_sessions.py` covering: envelope
  shape, auth-missing → 401, telemetry-unavailable → 503, successful list
  with mocked aggregator. Owner: software-engineer. Done criterion:
  `.dadaia/.venv/bin/python -m pytest
  tests/unit/features/panel/test_views_api_sessions.py -v` green.
- [ ] **PR5-B4** — Create fixture
  `tests/fixtures/telemetry/sessions_seeded.sqlite` with a small set of seeded
  rows (≥3 Claude sessions across two projects; ≥2 Codex sessions; mix of
  active/idle/ended statuses; representative `events` rows so
  `context_size_tokens` is non-trivially computed). Author integration test
  `tests/integration/test_panel_sessions_endpoint.py` exercising both endpoints
  against the fixture. Owner: software-engineer. Done criterion:
  `.dadaia/.venv/bin/python -m pytest
  tests/integration/test_panel_sessions_endpoint.py -v` green; API smoke
  command in SPEC §5 returns a positive integer.

---

## Phase C — Frontend Sessions tab (Claude-only path live)

> **Phase prerequisite:** Phase B all-`[x]` **AND** the panel-r4-v1 trio
> **PR4-08 + PR4-09 + PR4-10** all-`[x]` **AND** the SQLite verification probe
> ```
> sqlite3 ~/.dadaia/state/telemetry/telemetry.sqlite \
>   "SELECT COUNT(*) FROM sessions WHERE agent_name IS NOT NULL"
> ```
> returns ≥ 50.
> **Parallel window declared.** Write sets are disjoint:
> - **FE impl set:** `dadaia_workspace/features/panel/views/sessions.py`,
>   `dadaia_workspace/features/panel/views/assets/css/sessions.py`,
>   `dadaia_workspace/features/panel/views/assets/js/sessions.js`,
>   `dadaia_workspace/features/panel/views/index.py`,
>   `dadaia_workspace/features/panel/views/static.py`.
> - **QA e2e set:** `tests/e2e/test_panel_sessions_tab.spec.ts`.
>
> Per CLAUDE.md §9 and the panel-r4-v1 P1/P2 parallel precedent, **one `[-]` per
> set** may be held simultaneously. QA spec authoring (PR5-C6) must START
> BEFORE FE impl (PR5-C1..C5) — the e2e is the acceptance contract.

### QA strand (qa-engineer) — START FIRST

- [ ] **PR5-C6** — Author Playwright e2e spec
  `tests/e2e/test_panel_sessions_tab.spec.ts`. Cases: (a) Sessions tab
  populates from `/api/sessions?runtime=claude`; (b) row click opens drawer
  with `SessionDetail` content; (c) sort by Cost (desc) reorders rows; (d)
  "Last updated" badge ticks at ≤11 s; (e) auto-refresh suspends when
  `document.hidden` (simulated by `page.evaluate(() => document.dispatchEvent(new
  Event('visibilitychange')))` with `document.hidden = true`). Owner:
  qa-engineer. Done criterion: spec compiles, dry-runs against a mocked backend
  (no live panel yet), and is reviewed by product-engineer for FR coverage
  before FE impl begins.

### FE strand (frontend-engineer)

- [ ] **PR5-C1** — New file `dadaia_workspace/features/panel/views/sessions.py`
  exporting `render_sessions_section() -> str` (HTML scaffold: filter input,
  sortable table with columns Session / Project / Model / AI Turns / Context /
  Cost / Last activity / Status, detail drawer container). Owner:
  frontend-engineer. Done criterion: the function returns a valid HTML
  fragment importable by `index.py`; smoke import passes.
- [ ] **PR5-C2** — New file
  `dadaia_workspace/features/panel/views/assets/css/sessions.py` exporting
  `SESSIONS_CSS`: table base styles, status-dot variants (`active`/`idle`/
  `ended`), drawer slide-in/out transitions. Owner: frontend-engineer. Done
  criterion: CSS string non-empty, valid CSS, and includes a `.sessions-table`
  selector plus `.status-dot[data-status=...]` selectors.
- [ ] **PR5-C3** — New file
  `dadaia_workspace/features/panel/views/assets/js/sessions.js`: Sessions
  module that subscribes to `dadaia:runtime-change` (no-op in Phase C — only
  Claude is wired live), appends `?runtime=` + `Runtime.get()` on `authedFetch`
  calls (fallback to `claude` if `Runtime` global not yet defined — Phase D
  ships it), renders the table, opens the drawer on row click, runs a 10 s
  auto-refresh loop that checks `document.hidden` before each tick. Owner:
  frontend-engineer. Done criterion: module loads without error; manual smoke
  in `dadaia panel` shows real sessions populated.
- [ ] **PR5-C4** — Edit `dadaia_workspace/features/panel/views/index.py`: add
  the "Sessions" nav tab and a `<section id="section-sessions">` container.
  Owner: frontend-engineer. Done criterion: nav tab present in the panel
  topbar; clicking it shows the new section.
- [ ] **PR5-C5** — Edit `dadaia_workspace/features/panel/views/static.py`:
  register `sessions.css` and `sessions.js` in `_ASSETS`. Owner:
  frontend-engineer. Done criterion: both assets served at their expected
  paths; the new module loads from a live panel start.

### Phase-C close

- [ ] **PR5-C7** — Run the Playwright e2e spec against the live FE
  implementation. Owner: qa-engineer. Done criterion: all five cases (a)–(e)
  green; manual smoke per SPEC §5 acceptance #4 passes.

---

## Phase D — Global runtime switcher + retrofit Agents + Workflows

> **Phase prerequisite:** Phase C all-`[x]`.
> **Parallel window declared.** Same disjoint pattern as Phase C:
> - **BE impl set:** `dadaia_workspace/features/panel/views/api.py`
>   (`render_api_agents_canonical`, `render_api_workflows_list` filter plumbing).
> - **FE impl set:** `dadaia_workspace/features/panel/views/assets/js/runtime.js`
>   (new), `dadaia_workspace/features/panel/views/index.py` (topbar markup),
>   `dadaia_workspace/features/panel/views/assets/css/tokens.py` (extend),
>   `dadaia_workspace/features/panel/views/assets/js/agents.js` (edit),
>   `dadaia_workspace/features/panel/views/assets/js/workflows.js` (edit),
>   `dadaia_workspace/features/panel/views/static.py` (register `runtime.js`).
> - **QA e2e set:** `tests/e2e/test_panel_sessions_tab.spec.ts` (extend).
>
> One `[-]` per set may be held simultaneously.
>
> **REBASE NOTE (cross-release with panel-r4-v1).** Four files in Phase D are
> shared with panel-r4-v1. r4 ships first; r5 Phase D rebases on top. Do not
> clobber r4 deltas — layer on top. Tasks **PR5-D9..D12** below are explicit
> rebase guards for those files. **PR5-D13** asserts the `?runtime=` default
> backward-compat parity (NFR5).

### BE strand (software-engineer)

- [ ] **PR5-D1** — Edit `dadaia_workspace/features/panel/views/api.py`:
  `render_api_agents_canonical` reads `runtime = qs.get("runtime", "claude")`
  and filters the response by `provider`. Same change to
  `render_api_workflows_list`. Default of `"claude"` preserves backward compat
  (NFR5). Owner: software-engineer. Done criterion: `curl .../api/agents` (no
  `?runtime=`) returns Claude-scoped data byte-identical to today's shape;
  `?runtime=codex` returns Codex-scoped data; same for `/api/workflows`.

### FE strand (frontend-engineer)

- [ ] **PR5-D2** — New file
  `dadaia_workspace/features/panel/views/assets/js/runtime.js`: define
  `window.Runtime` with `get()` / `set(value)`; localStorage key exactly
  `dadaia-panel-runtime`; emit `dadaia:runtime-change` `CustomEvent` on set;
  also set `document.documentElement.dataset.runtime`. Mirror the theme
  switcher pattern (`views/index.py:60`). Owner: frontend-engineer. Done
  criterion: from the panel JS console, `Runtime.set('codex')` persists across
  reload and fires the event.
- [ ] **PR5-D3** — Edit `dadaia_workspace/features/panel/views/index.py`:
  add `.runtime-switcher` topbar control beside the theme switcher (Claude /
  Codex toggle, accessible labelling). Owner: frontend-engineer. Done
  criterion: visible toggle in the topbar; clicking it calls
  `Runtime.set(...)`.
- [ ] **PR5-D4** — Extend
  `dadaia_workspace/features/panel/views/assets/css/tokens.py` with
  `--color-runtime-claude` (warm gold), `--color-runtime-codex` (sage green),
  `--color-runtime-active` (resolved by `[data-runtime="..."]` selectors).
  Define values for all three palettes (Mint / Sage / Warm); verify WCAG 2.2 AA
  against the topbar background. Owner: frontend-engineer. Done criterion:
  nine hex values defined; contrast check documented in commit body.
- [ ] **PR5-D5** — Edit
  `dadaia_workspace/features/panel/views/assets/js/agents.js`: subscribe to
  `dadaia:runtime-change`; on change, drop cache and refetch with `?runtime=`
  appended. Owner: frontend-engineer. Done criterion: toggling the switcher
  re-renders the Agents tab against the right backend filter.
- [ ] **PR5-D6** — Edit
  `dadaia_workspace/features/panel/views/assets/js/workflows.js`: same
  retrofit as `agents.js`. Owner: frontend-engineer. Done criterion: toggling
  the switcher re-renders the Workflows tab against the right backend filter.
- [ ] **PR5-D7** — Edit
  `dadaia_workspace/features/panel/views/static.py`: register `runtime.js` in
  `_ASSETS`. Owner: frontend-engineer. Done criterion: `runtime.js` served at
  its expected path; loads before `agents.js`, `workflows.js`, and
  `sessions.js`.

### QA strand (qa-engineer)

- [ ] **PR5-D8** — Extend
  `tests/e2e/test_panel_sessions_tab.spec.ts` to cover the three-tab × two-
  runtime matrix: toggling the switcher reloads Agents, Workflows, AND
  Sessions; localStorage persistence verified by `page.reload()` then
  `expect(localStorage.getItem('dadaia-panel-runtime')).toBe('codex')`. Owner:
  qa-engineer. Done criterion: extended spec green against the live FE+BE
  implementation.

### Rebase-guard strand (frontend-engineer + software-engineer)

> Cross-release with panel-r4-v1. r4 ships first (PR4-13 `tier` plumbing on
> `api.py`; PR4-18 `data-tier` wiring on `agents.js` + 9 tier tokens on
> `tokens.py`; PR4-15/PR4-19 tier assertions on `test_api_agents.py`). The
> tasks below are explicit rebase guards: r5 must layer **on top**, never
> clobber.

- [ ] **PR5-D9** — Rebase guard for
  `dadaia_workspace/features/panel/views/assets/js/agents.js`. Confirm r4
  PR4-18's `data-tier="${agent.tier}"` element wiring is still present after
  PR5-D5's `dadaia:runtime-change` subscription + `?runtime=` refetch is
  layered on. Owner: frontend-engineer. Done criterion:
  `grep -n 'data-tier' dadaia_workspace/features/panel/views/assets/js/agents.js`
  returns the r4 wiring AND
  `grep -n 'dadaia:runtime-change' dadaia_workspace/features/panel/views/assets/js/agents.js`
  returns the r5 subscription; both are in the same file.
- [ ] **PR5-D10** — Rebase guard for
  `dadaia_workspace/features/panel/views/assets/css/tokens.py`. Confirm the 9
  r4 `--color-tier-1/2/3` tokens × Mint/Sage/Warm coexist with the 9 r5
  `--color-runtime-claude` / `--color-runtime-codex` / `--color-runtime-active`
  tokens × the same 3 palettes (18 total tokens after Phase D lands). Owner:
  frontend-engineer. Done criterion:
  `grep -c 'color-tier' dadaia_workspace/features/panel/views/assets/css/tokens.py`
  returns ≥ 9 AND
  `grep -c 'color-runtime' dadaia_workspace/features/panel/views/assets/css/tokens.py`
  returns ≥ 9.
- [ ] **PR5-D11** — Rebase guard for
  `dadaia_workspace/features/panel/views/api.py`. The file goes through three
  delta layers: (a) r4 PR4-13 adds `tier: int` to each item in
  `render_api_agents_canonical`; (b) r5 Phase B adds new closure factories
  `render_api_sessions` + `render_api_session_detail`; (c) r5 Phase D
  (PR5-D1) extends `render_api_agents_canonical` to read
  `runtime = qs.get("runtime", "claude")` and filter by `provider`. Owner:
  software-engineer. Done criterion: after Phase D lands, a single agent item
  in the `/api/agents?runtime=claude` response carries BOTH the `tier` key
  (from r4) and is filtered by `provider="claude"` (from r5); response shape
  is a superset of r4's, never a replacement.
- [ ] **PR5-D12** — Rebase guard for
  `tests/unit/features/panel/test_api_agents.py`. Confirm r4 PR4-15/PR4-19
  assertions (every agent has `tier ∈ {1, 2, 3}` and `data-tier` attribute
  rendered) remain present and green AFTER the r5 runtime-filter assertions
  are appended. Owner: software-engineer. Done criterion:
  `pytest tests/unit/features/panel/test_api_agents.py -v` green; the test
  file contains BOTH the tier assertions and the new runtime-filter
  assertions; no r4 assertion was deleted or weakened.
- [ ] **PR5-D13** — Backward-compatibility parity test (NFR5). Extend
  `tests/unit/features/panel/test_api_agents.py` with an assertion that
  `/api/agents?runtime=claude` returns a response whose item shape is
  byte-identical (modulo `provider`-scoped filtering) to `/api/agents` with no
  `?runtime=` query-param. This codifies the "default to claude" guarantee in
  NFR5 and prevents a silent regression where the default branch starts
  emitting a different envelope than the explicit `runtime=claude` branch.
  Owner: software-engineer. Done criterion: pytest assertion compares the two
  response shapes key-by-key and item-by-item; passes when both branches
  produce identical envelopes for the same backing fixture.

---

## Phase E — Codex sub-tab live

> **Phase prerequisite:** Phase D all-`[x]`.
> **Parallel window declared (3-set).** Disjoint:
> - **BE impl set:** `dadaia_workspace/features/telemetry/aggregator/runtimes.py`
>   (flesh out `CodexRuntimeAdapter`) and any pricing-related touchpoints in
>   `dadaia_workspace/features/telemetry/pricing.py` if a Codex no-op branch is
>   needed.
> - **FE impl set:** `dadaia_workspace/features/panel/views/assets/js/sessions.js`
>   (banner branch).
> - **QA e2e set:** `tests/integration/test_panel_sessions_endpoint.py` (Codex
>   fixture rows) and `tests/fixtures/telemetry/sessions_seeded.sqlite` if not
>   already seeded with Codex.

### BE strand (backend-engineer)

- [ ] **PR5-E1** — Flesh out `CodexRuntimeAdapter` in
  `dadaia_workspace/features/telemetry/aggregator/runtimes.py`:
  `liveness(session_id, cwd)` reads `~/.codex/state_5.sqlite`
  `threads.updated_at` and tails `~/.codex/history.jsonl` for the most recent
  `ts` delta. Classification: `active` if delta ≤ 5 min, `idle` if ≤ 60 min,
  `ended` if `threads.archived = 1` or delta > 60 min. Wrap reads in a
  try/except returning `idle` on parse failure (graceful degradation). Owner:
  backend-engineer. Done criterion: against the operator's live
  `~/.codex/state_5.sqlite`, the adapter classifies threads correctly; failure
  modes do not crash the aggregator.
- [ ] **PR5-E2** — Audit any pricing-related touchpoints in
  `dadaia_workspace/features/telemetry/pricing.py` and confirm no Codex branch
  is mis-firing. The function `compute_cost` MUST NOT be called for Codex rows
  (the adapter sets `cumulative_cost_usd = None`). If a defensive `if runtime
  == "codex": return None` guard is warranted at the adapter boundary, add it.
  Owner: backend-engineer. Done criterion: smoke run of `list_sessions(runtime=
  'codex')` never calls `compute_cost`.

### FE strand (frontend-engineer)

- [ ] **PR5-E3** — Edit
  `dadaia_workspace/features/panel/views/assets/js/sessions.js`: when
  `Runtime.get() === "codex"`, render a top-of-table banner *"Cost not tracked
  for Codex"* and render the Cost column as `—` for every row. When runtime
  flips back to `claude`, the banner disappears and Cost cells re-populate
  with the dollar value. Owner: frontend-engineer. Done criterion: manual smoke
  in `dadaia panel`: toggle Codex → banner appears, Cost column is `—`; toggle
  Claude → banner gone, Cost column populated.

### QA strand (qa-engineer)

- [ ] **PR5-E4** — Extend
  `tests/integration/test_panel_sessions_endpoint.py` with Codex fixture rows
  sourced from `tests/fixtures/telemetry/sessions_seeded.sqlite`. Assertions:
  for every Codex row in the response, `cumulative_cost_usd is None` and
  `cost_known is False`. If the fixture lacks Codex rows from Phase B, edit
  `sessions_seeded.sqlite` to add ≥2 Codex rows. Owner: qa-engineer. Done
  criterion: extended integration test green; final e2e pass against live
  panel shows the Codex banner and the `—` Cost column across all Codex rows.

---

## P-Closure — Release closure *(product-engineer)*

- [ ] **PR5-Z1** — Author
  `specs/releases/panel-r5-v1/CLOSURE.md` per `dadaia-release-closure` skill.
  Includes: Summary, Tasks completed table with final commit SHAs,
  Validations triples (each with evidence), Drifts (if any), Memory updates
  list, Backlog returns, Archive decision = `MOVE`. Owner: product-engineer.
  Done criterion: file present with `**Status:** Aprovado`; `dadaia specs
  doctor` green.
- [ ] **PR5-Z2** — Update memory atoms during CLOSURE phase only:
  `specs/memory/product/index.html` (add Sessions tab + global runtime
  switcher to catalog if applicable); `specs/memory/product/<panel-slug>.html`
  (refresh the panel feature page with Sessions tab + multi-runtime delta);
  `specs/memory/architecture.html` (note `RuntimeAdapter` placement in the
  aggregator layer if it affects the layer description);
  `specs/memory/tech-stack.html` (no change — release does not touch
  dependencies). Owner: product-engineer. Done criterion: every listed memory
  HTML is rendered from the canonical templates at
  `dadaia_workspace/public/templates/memory-*.html.j2`; `dadaia specs doctor`
  passes the memory atomicity + broken-image checks.
- [ ] **PR5-Z3** — Move the release directory to archive:
  `git mv specs/releases/panel-r5-v1 specs/_archive/releases/panel-r5-v1`
  (executed by devops-engineer per PE-delegation rule). Update
  `specs/releases/ACTIVE.md` to the next release or `release: none`. Owner:
  product-engineer (coordinates with devops-engineer for the `git mv`). Done
  criterion: directory at archive path; ACTIVE.md updated.
