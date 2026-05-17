# Tasks: Release — agent-monitoring-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** agent-monitoring-v1
> **Phase:** TASKS
> **Owner:** product-engineer (curator) / handed off to specialists on Aprovado
> **Created:** 2026-05-17
> **SPEC:** `specs/releases/agent-monitoring-v1/SPEC.md` (Status: Aprovado)
> **PLAN:** `specs/releases/agent-monitoring-v1/PLAN.md` (Status: Aprovado)

> Marker convention (`dadaia-task-manager`): `[ ]` OPEN → `[-]` IN PROGRESS → `[x]` DONE.
> All tasks below are OPEN. Implementation may begin — reserve via `dadaia-task-manager` protocol.

---

## Phase 1 — A11y fix (gating)

- [ ] **T-AM-01** — Fix nav-tabs accessibility in `dadaia_workspace/features/panel/views/index.py`.
  - Add `role="tablist"` to the `<nav class="nav-tabs">` element.
  - Add `id="tab-{section}"` to each tab button.
  - Add `role="tabpanel"`, `tabindex="0"`, `aria-labelledby="tab-{section}"` to each `<section id="section-...">`.
  - Extend PANEL_JS keydown handler: ArrowLeft/ArrowRight cycle, Home/End jump, Enter/Space activate.
  - Snapshot tests (smoke) for the 3 existing tabs (Servers/Memories/Agents-placeholder) before and after.
  - Files: `dadaia_workspace/features/panel/views/index.py`, `dadaia_workspace/features/panel/views/_assets.py` (PANEL_JS), `tests/unit/features/panel/test_views_index.py` (new).
  - Parallel-safe: no — gates all subsequent frontend work.

## Phase 2 — Schema, migrations, telemetry service skeleton

- [ ] **T-AM-02** — Create `dadaia_workspace/features/telemetry/` top-level package skeleton.
  - Files: `features/telemetry/__init__.py`, `features/telemetry/service.py` (empty `TelemetryService` with DI constructor signature), `features/telemetry/store/__init__.py`, `features/telemetry/reader/__init__.py`, `features/telemetry/aggregator/__init__.py`.
  - Parallel-safe: yes (no other task touches these new files until T-AM-03).

- [ ] **T-AM-03** — Implement `features/telemetry/store/schema.py` with the 5 migrations from SPEC § Schema (reader_state, sessions, agents, events, workflows, workflow_agents) + indices.
  - `PRAGMA user_version` based migration runner.
  - Connection PRAGMAs: WAL, synchronous=NORMAL, foreign_keys=ON.
  - `apply_migrations(conn)` idempotent.
  - Tests: in-memory SQLite, apply twice, assert user_version stable.
  - Files: `features/telemetry/store/schema.py`, `tests/unit/features/telemetry/test_schema.py`.
  - Parallel-safe: yes after T-AM-02.

- [ ] **T-AM-04** — Implement `features/telemetry/store/dao.py` (repository pattern).
  - Methods: `upsert_session`, `upsert_agent`, `insert_event`, `upsert_workflow`, `upsert_reader_state`, `get_reader_state`, plus read-side: `list_agents`, `list_workflows`, `list_sessions_by_agent`.
  - Returns dataclasses, never `sqlite3.Row`.
  - Tests: CRUD round-trip, idempotency on duplicate `event_id`.
  - Files: `features/telemetry/store/dao.py`, `features/telemetry/store/models.py` (dataclasses), `tests/unit/features/telemetry/test_dao.py`.
  - Parallel-safe: yes after T-AM-03.

## Phase 3 — Reader Claude Code

- [ ] **T-AM-05** — Implement `features/telemetry/reader/allowlist.py` (CRITICAL T1).
  - Function `allowlist_event(raw: dict) -> dict | None` returns dict with only approved keys; rejects events missing required fields.
  - Approved keys hardcoded: `sessionId`, `timestamp`, `cwd`, `entrypoint`, `gitBranch`, `isSidechain`, `slug`, `uuid`, `type`, `agentName`, `aiTitle`, plus `message.usage.*` and `message.model` for `type=assistant`.
  - Forbidden keys (asserted by tests): `content`, `text`, `messages`, `snapshot`, `thinking`, `prompt`, `response`.
  - Tests: dict with forbidden keys → stripped; integration test asserts NO endpoint leaks these fields.
  - Files: `features/telemetry/reader/allowlist.py`, `tests/unit/features/telemetry/test_allowlist.py`.
  - Parallel-safe: yes (no deps on T-AM-03/04 in module sense).

- [ ] **T-AM-06** — Implement `features/telemetry/reader/claude.py`.
  - Incremental tail with byte-offset checkpoint in `reader_state`.
  - `_safe_parse_lines(raw)` handles truncated last line (rewinds offset).
  - Detects file rotation via inode change (devops T7).
  - Reads `event.message.usage.*` and `event.message.model` (SE empirical schema, R1 reconciliation).
  - Agent identity: `type=agent-name` events feed `sessions.agent_name`; `isSidechain` + `slug` populates sub-agent.
  - Budgets enforced from `features/telemetry/budget.py` (T-AM-08).
  - Tests: valid jsonl, truncated, malformed mid-file, empty, idempotent re-read.
  - Files: `features/telemetry/reader/claude.py`, `tests/unit/features/telemetry/test_reader_claude.py`, `tests/fixtures/telemetry/sample_session*.jsonl`.
  - Parallel-safe: yes (orthogonal to T-AM-07).

## Phase 4 — Reader Codex + workflows

- [ ] **T-AM-07** — Implement `features/telemetry/reader/codex.py`.
  - `sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5.0)`.
  - Query `threads` table with defensive column selection; degrade to empty list on `OperationalError`.
  - Maps `tokens_used` (aggregated) → `tokens_input=tokens_used, tokens_output=0` with `cost_micro_usd=NULL` (D-AM-16).
  - Tests: in-memory SQLite with partial schema, locked DB, missing file.
  - Files: `features/telemetry/reader/codex.py`, `tests/unit/features/telemetry/test_reader_codex.py`.
  - Parallel-safe: yes.

- [ ] **T-AM-08** — Implement `features/telemetry/budget.py` named constants.
  - `MAX_BYTES_PER_FILE_PER_CYCLE`, `MAX_LINE_LENGTH`, `MAX_EVENTS_PER_CYCLE`, `CACHE_TTL_SECONDS`, `PRICING_STALENESS_THRESHOLD_DAYS`, `MAX_TOKEN_COUNT_PER_EVENT`.
  - Tests: assert types and reasonable defaults.
  - Files: `features/telemetry/budget.py`, `tests/unit/features/telemetry/test_budget.py`.
  - Parallel-safe: yes.

- [ ] **T-AM-09** — Implement `features/telemetry/reader/workflows.py` (SKILL.md frontmatter parser, architect D12).
  - Walk `.claude/skills/*/SKILL.md` and `.agents/skills/*/SKILL.md`.
  - Parse YAML frontmatter (regex stdlib parser like multi-platform-parity-v1 used; no `pyyaml`).
  - Extract `name`, `description`, optional `applyTo`.
  - Best-effort substring match against known agent names for `workflow_agents`.
  - Files: `features/telemetry/reader/workflows.py`, `tests/unit/features/telemetry/test_reader_workflows.py`.
  - Parallel-safe: yes.

## Phase 5 — Pricing module

- [ ] **T-AM-10** — Implement `features/telemetry/pricing.py` (D-AM-07).
  - `ModelPricing` dataclass with `effective_from`.
  - `PRICING_TABLE` dict with claude-opus-4-7, claude-sonnet-4-6, claude-haiku-3-5 baseline rows.
  - `compute_cost(usage, model, when) -> int | None` returns micro-USD.
  - `pricing_age_days(when=date.today()) -> int | None` returns the age of the newest used row.
  - Tests (parametrized): known model in current window, historical effective_from, unknown model returns None, zero usage returns 0.
  - Files: `features/telemetry/pricing.py`, `tests/unit/features/telemetry/test_pricing.py`.
  - Parallel-safe: yes.

## Phase 6 — Aggregator

- [ ] **T-AM-11** — Implement `features/telemetry/aggregator/queries.py`.
  - SQL group-by per agent / per context / per day.
  - `cwd → spec_context` lookup at query time via injected `SpecContextService.list_all()` (architect D9).
  - Bucket `context_slug=null, context_name="unassigned"` for cwd outside any registered context.
  - Returns API-shaped dataclasses (AgentSummary, ContextBreakdown, RecentSession) — NO content fields (T1).
  - Tests: synthetic DB with fixtures; verify breakdown sums, unassigned bucket, ordering.
  - Files: `features/telemetry/aggregator/queries.py`, `features/telemetry/aggregator/models.py`, `tests/unit/features/telemetry/test_aggregator.py`.
  - Parallel-safe: yes after T-AM-04 + T-AM-10.

- [ ] **T-AM-12** — Wire `TelemetryService` in `features/telemetry/service.py`.
  - DI constructor: `(reader_factory, dao, aggregator, pricing_table, workspace_root, spec_context_service)`.
  - Public methods: `refresh()` (lazy on-request, cache 30s), `list_agents()`, `list_workflows()`, `list_sessions_by_agent(name)`.
  - Process lock via `fcntl.flock` on `~/.dadaia/state/telemetry/telemetry.lock` (architect D6).
  - Guard `os.getuid() != 0` in constructor (devops T6).
  - Tests: stub reader/dao via DI; lock behavior on concurrent refresh.
  - Files: `features/telemetry/service.py`, `tests/unit/features/telemetry/test_service.py`.
  - Parallel-safe: yes after T-AM-04 + T-AM-06 + T-AM-07 + T-AM-09 + T-AM-11.

## Phase 7 — Endpoints + auth

- [ ] **T-AM-13** — Implement Bearer token auth in `features/panel/auth.py`.
  - `ensure_token() -> str` generates via `secrets.token_urlsafe(32)`, persists to `~/.dadaia/state/panel.token` with `os.chmod(0o600)`.
  - `validate(header_value: str) -> bool` constant-time compare.
  - Tests: token file created with 0o600 perms; invalid header → False; missing header → False.
  - Files: `dadaia_workspace/features/panel/auth.py`, `tests/unit/features/panel/test_auth.py`.
  - Parallel-safe: yes.

- [ ] **T-AM-14** — Add CSP + nosniff security headers in `features/panel/handler.py`.
  - Private helper `_security_headers(content_type)`.
  - HTML: `Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'`.
  - JSON: `X-Content-Type-Options: nosniff`.
  - Tests: integration — header present in responses.
  - Files: `dadaia_workspace/features/panel/handler.py`, `tests/integration/test_panel_handler_headers.py`.
  - Parallel-safe: yes.

- [ ] **T-AM-15** — Add `/api/agents`, `/api/workflows`, `/api/agents/{id}/sessions` routes in `handler.py`.
  - Update `_RAW_ROUTES` and **synchronize `_NOT_FOUND_BODY`** (architect HIGH finding).
  - Auth check on every route via T-AM-13 middleware.
  - Wire to `PanelService.telemetry.*` methods.
  - Tests: integration with fake `TelemetryService`; verify 401 without token, 200 with token, no `content`/`text`/`messages` in any payload.
  - Files: `dadaia_workspace/features/panel/handler.py`, `dadaia_workspace/features/panel/service.py` (DI extension), `tests/integration/test_panel_telemetry_endpoints.py`.
  - Parallel-safe: yes after T-AM-12 + T-AM-13 + T-AM-14.

## Phase 8 — Frontend

- [ ] **T-AM-16** — Implement `features/panel/views/agents.py`.
  - Card grid: `repeat(auto-fill, minmax(360px, 1fr))` (frontend D-02).
  - Header (name + dominant model + agent icon placeholder for brand-identity).
  - Metrics: session_count, total_cost_usd (or "—" when `cost_known=false`), last_activity.
  - Breakdown by Spec Context Project with `%` bars (aria-label = "X% do custo total").
  - Drill-down: lazy fetch `/api/agents/{id}/sessions` on toggle (`aria-expanded`).
  - Pricing-staleness banner when `pricing_age_days > PRICING_STALENESS_THRESHOLD_DAYS`.
  - SessionId truncated to 8 chars + `...` (T9 devops).
  - All inserted values via `escHtml()`.
  - Tests: smoke render with empty list, typical list.
  - Files: `dadaia_workspace/features/panel/views/agents.py`, PANEL_CSS additions in `_assets.py`, PANEL_JS fetch extensions, `tests/unit/features/panel/test_views_agents.py`.
  - Parallel-safe: yes after T-AM-15.

- [ ] **T-AM-17** — Implement `features/panel/views/workflows.py`.
  - Card grid: `repeat(auto-fill, minmax(280px, 1fr))` (frontend D-02).
  - Header + description + source_hint.
  - Agent chips: `<button aria-label="Filtrar por agente: ...">` navigating to `#agents?filter=<name>` (frontend D-04).
  - No cost numbers (intentional, frontend D-01).
  - Tests: chip click triggers tab-switch + filter.
  - Files: `dadaia_workspace/features/panel/views/workflows.py`, PANEL_JS hash filter handler, `tests/unit/features/panel/test_views_workflows.py`.
  - Parallel-safe: yes after T-AM-15.

- [ ] **T-AM-18** — Add Workflows tab to `views/index.py` (4th nav-tab) and wire both tabs into PANEL_JS lazy fetch on tab activation (frontend D-05).
  - Update tab list to: Servers, Memories, Agents, Workflows.
  - Hash-fragment routing reads `#agents?filter=<name>` on initial load.
  - Files: `dadaia_workspace/features/panel/views/index.py`, PANEL_JS.
  - Parallel-safe: no — must come after T-AM-16 + T-AM-17 + T-AM-01.

## Phase 9 — Integration with brand-identity-v1 + hardening

- [ ] **T-AM-19** — Consume brand-identity-v1 tokens with fallback.
  - PANEL_CSS adds: `--color-cost`, `--color-warning-bg`, `--color-alert`, `--color-accent-secondary` mapped to new palette `#633d2e #ddd9ab #f7af63 #bfd8ad`. Existing `--color-accent` updated to `#9cddc8`.
  - If brand-identity-v1 is not yet on Aprovado, keep current values as fallback (release ships either way).
  - Tests: contrast assertions (WCAG AA) on text-over-token combinations from SPEC.
  - Files: `dadaia_workspace/features/panel/views/_assets.py`, `tests/unit/features/panel/test_panel_css_contrast.py`.
  - Parallel-safe: yes; coordinated with `dadaia-workspace-brand-identity-v1` tasks.

- [ ] **T-AM-20** — Hardening pass: chmod, fs permission checks, secure-delete docs.
  - Verify `~/.dadaia/state/telemetry/` is created with `0o700`, file with `0o600` (devops T2).
  - Integration test: create service, inspect mode bits.
  - Document `shred -u` recovery procedure in `dadaia_workspace/features/panel/views/agents.py` help section (devops T12).
  - Files: `dadaia_workspace/features/telemetry/service.py` (mkdir mode), `tests/integration/test_telemetry_permissions.py`.
  - Parallel-safe: yes after T-AM-12.

- [ ] **T-AM-21** — Boot in no-telemetry mode on SQLite corruption (devops T10).
  - `PRAGMA integrity_check` at startup; on failure rename to `telemetry.sqlite.corrupt.<ts>` and degrade endpoints to 503.
  - Tests: corrupted file fixture (truncated header) → service starts, endpoints return 503 with human-readable message.
  - Files: `dadaia_workspace/features/telemetry/service.py`, `tests/integration/test_telemetry_corrupt_db.py`.
  - Parallel-safe: yes after T-AM-12.

- [ ] **T-AM-22** — Acceptance pass.
  - All 13 acceptance criteria from SPEC.md § Acceptance criteria green.
  - `dadaia doctor` passes for this release (any pre-existing failures are not introduced by these tasks).
  - Performance budget validated on the real operator workspace (49.7 MB jsonl).
  - Files: ad-hoc validation log captured in `.dadaia/reports/dadaia-workspace/product-engineer/<ts>-agent-monitoring-acceptance.html`.
  - Parallel-safe: no — gates CLOSURE.

---

## Parallelization summary

After SPEC Aprovado, the following groups can be picked up in parallel:

- **Wave A (independent):** T-AM-01, T-AM-02, T-AM-08, T-AM-10, T-AM-13, T-AM-14.
- **Wave B (after schema):** T-AM-03 → T-AM-04 → (T-AM-05, T-AM-06, T-AM-07, T-AM-09).
- **Wave C (after readers + pricing):** T-AM-11 → T-AM-12.
- **Wave D (after service):** T-AM-15 → (T-AM-16, T-AM-17) → T-AM-18.
- **Wave E (closing):** T-AM-19, T-AM-20, T-AM-21 → T-AM-22.

Each wave's tasks live in distinct files; any agent reserving one of these flips it to `[-]` per `dadaia-task-manager` protocol and commits the marker change in its own `chore(tasks): start <id>` commit.
