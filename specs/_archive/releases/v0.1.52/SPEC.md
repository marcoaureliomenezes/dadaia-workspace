# SPEC — v0.1.52 — Panel Plumbing

**Status:** Aprovado
**Branch:** `feature/v0.1.52` (base: `ccc47934`, v0.1.51 closure)
**Origin:** operator-approved release sequence R4 (grill 2026-07-02; operator-elected
early position; definition-time inspection 2026-07-02). Dual definition review
2026-07-02: software-architect REJECT (facade layering + foreign-DB factory scope +
composition-root unwiring) + qa-engineer REJECT (commit-archaeology verifiability +
factory-grep scope + cost-known matrix + deterministic concurrency red) — ALL
amendments folded in below. Disposes the deferred bug root-chain
`panel-telemetry-sqlite-corrupts-under-concurrent-access` (stream already terminal —
no new event; this release remediates the chain).
**Consumes:** panel-sessions-cost-dashboard-only, panel-runtime-reliability

## 1. Problem

1. **The Sessions tab serves a list nobody uses; its dashboard is client-computed.**
   `views/sessions.py:24-116` scaffolds a 4-card grid + cost-unknown banner PLUS a
   sortable/filterable table, detail drawer, and skeleton rows; `sessions.js`
   (711 lines) fetches the FULL list from `/api/sessions` (`fetchSessions`:555) and
   computes the cards client-side (`computeStats`:97) with a 10s list auto-refresh;
   `assets/css/sessions.py` (~477 CSS lines) mostly serves the list/drawer. The
   panel view reaches telemetry ONLY through the `service.telemetry.*` facade
   (`api.py:872` → `TelemetryService.list_sessions:464` → aggregator). The
   aggregate MUST move server-side before the client list dies.
2. **The telemetry SQLite corruption root-chain is live.** The pragma'd factory
   `telemetry/store/schema.py#open_connection` (WAL, :129-141) has ZERO production
   callers; the panel CLI `_dao_factory` (`cli/commands/panel.py:52`) opens a bare
   `sqlite3.connect(check_same_thread=False)` shared across every
   ThreadingHTTPServer thread; refresh write-DAOs lack finally-close;
   `_quarantine_db` (`service.py:263-286`) strands `-wal`/`-shm` siblings.
   **Connection topology (5 sites):** the store sites above + `service.py:296`
   (deliberate pre-migration integrity probe) + TWO foreign READ-ONLY readers —
   `aggregator/runtimes.py:281` and `reader/codex.py:121` open
   `~/.codex/state_5.sqlite` via `file:...?mode=ro`. The foreign readers must NEVER
   flow through a WAL-writing factory (WAL is a write; it would mutate the
   operator's Codex DB).
3. **Catalog debris.** (a) The `/api/kanban` chain is UI-unreachable since v0.1.45;
   its full surface: route (`handler.py:197`) + dispatch + 404-body line + the
   `_GET_ONLY_API_ROUTES_RE` 405 guard (`handler.py:294`) + view
   (`views/kanban.py`, ~298 lines) + the WHOLE CSS file (`assets/css/kanban.py`) +
   nine `--kanban-*` tokens (`tokens.py:121-129`) + composition-root wiring
   (`container.py:82` import, `:1238-1242` views-dict entry, `:339` kanban-only
   provider) + tests. (b) `_md_render.block_code` (:107-116) emits mermaid fences
   UNESCAPED while no renderer ships (CSP forbids the CDN import; the dead
   `window.mermaid.run()` block survives at `academy.js:146-147`). (c) The
   telemetry `panel.token` drift-check (`service.py:181-197`) references the
   deleted auth model — the token is never minted.

## 2. Goals (what done means)

1. `/api/sessions` returns a SERVER-side aggregate cost summary through a proper
   `TelemetryService.aggregate_sessions` facade; the detail endpoint and the
   then-dead facade + aggregator queries are gone; the aggregate lands before the
   client list dies (greppable commit convention — §5 AC-1).
2. The Sessions tab renders ONLY the 4-card dashboard + banner from the aggregate;
   list/toolbar/drawer/skeleton/10s-refresh code is deleted; CSP hashes untouched.
3. Every WRITABLE telemetry-store connection flows through the pragma'd factory
   (WAL + busy_timeout); store query paths use read-only URIs closed in finally;
   refresh DAOs close in finally; the integrity probe uses the factory's read-only
   mode; quarantine moves `-wal`/`-shm` with the DB; the foreign read-only readers
   are explicitly EXEMPT (enumerated allowlist).
4. The kanban chain is deleted COMPLETELY (including composition root, 405 guard,
   tokens, CSS file); mermaid fences are escaped AND the dead `mermaid.run()`
   client block is deleted; the token drift-check is removed.
5. The surviving panel passes E2E-GUARD-01/02 plus a dashboard-only spec; the
   replaced test files' behavior inventory is mapped to successors (no silent
   coverage loss).

## 3. Functional requirements

### FR1 — Server-side aggregate endpoint (lands FIRST)

- New aggregator query `aggregate_sessions(runtime) -> SessionAggregate` in
  `telemetry/aggregator/queries.py`: `{runtime, total_sessions, active_sessions,
  total_cost_usd (float | None), cost_known (bool), total_messages,
  top_agent: {name, session_count} | None, generated_at}`.
- New facade `TelemetryService.aggregate_sessions(...)` (same layering as the
  current `list_sessions:464`); `render_api_sessions` calls the facade, never the
  private aggregator. DELETE the then-dead facades `TelemetryService.list_sessions`
  (:464) and `TelemetryService.get_session` (:477) — grep-verified zero callers
  after the switch.
- **Cost-known case matrix (REQUIRED aggregate-test assertions):**
  1. codex/pi runtime ⇒ `total_cost_usd: null`, `cost_known: false` (client 'N/A');
  2. claude, empty store ⇒ `total_sessions: 0`, `total_cost_usd: null` ('—');
  3. claude, all rows cost-unknown ⇒ `total_cost_usd: null` ('—' — NOT 'N/A');
  4. claude, mixed rows ⇒ partial sum over `cost_known AND cumulative_cost_usd IS
     NOT NULL` rows only;
  5. claude, `cost=0` known row ⇒ `total_cost_usd: 0.0` ('$0.00' — 0 ≠ null);
  6. a `cost_known=1, cumulative_cost_usd=null` row contributes NOTHING to the sum
     and does not flip cost-known-ness;
  7. `cost_known=false` rows STILL count toward `total_sessions`,
     `total_messages`, `active_sessions`, and top-agent;
  8. `?runtime=` filtering scopes every figure.
  The client render mapping ('N/A' for cost-unknown runtimes vs '—' for
  claude-null vs '$X.XX') is preserved in FR2.
- DELETE `/api/sessions/<runtime>/<session_id>`: ALL handler sites (docstring
  :48-49, 404 body :121-124, route :245-248, dispatch :790-801, any route-name
  listing), `render_api_session_detail` (`api.py:921-1000`), aggregator
  `list_sessions` (:669) + `get_session` (:849). `list_sessions_by_agent` (:578)
  STAYS (serves `/api/agents/<id>/sessions`).
- **Coverage-inventory contract (v0.1.51 AC-5 analogue):** before deleting the
  three list-era test files (625+536+538 lines), enumerate the behaviors they
  assert and map each SURVIVING behavior to a named successor test (matrix cases
  above; deleted-route 404; `/api/agents/<id>/sessions` coverage confirmed intact
  elsewhere). Inventory recorded on the T-52-10 task line; the QA gate re-derives.

### FR2 — Sessions view: dashboard only

- `views/sessions.py`: keep `#sessions-dashboard`, `#sessions-banner`, and the
  `#sessions-last-updated` badge — the badge is EXTRACTED from `.sessions-toolbar`
  BEFORE the toolbar (filter input) is deleted; DELETE table, sortable headers,
  drawer, skeleton machinery.
- `sessions.js`: fetch the aggregate, render the 4 cards (Total Sessions keeps its
  "N active" sub-label from `active_sessions`; Top Agent keeps its session-count
  sub-label) + banner (`isCostUnknownRuntime` semantics preserved: 'N/A' vs '—' vs
  '$X.XX' per the FR1 matrix), re-fetch on `dadaia:runtime-change`; DELETE list
  rendering, sort/filter, drawer, the 10s list auto-refresh.
- `assets/css/sessions.py`: keep dashboard-grid/banner/stat-card blocks; DELETE
  table/drawer/toolbar blocks.
- Playwright: DELETE `test_panel_sessions_tab.spec.ts` (623 lines, list-era); ADD
  `sessions-dashboard.spec.ts` (mocked aggregate per matrix case, banner per
  runtime, no console errors). Response-guard tour unchanged (tours by section id;
  zero list-selector dependencies — verified).

### FR3 — Telemetry SQLite reliability

- `schema.open_connection` gains `busy_timeout` and `read_only: bool = False`
  (`file:...?mode=ro` URI; read-only mode skips the WAL pragma — WAL is a write).
- Routing scope = **telemetry-store connections only**: panel `_dao_factory`
  (drop `check_same_thread=False` sharing — per-use connections), aggregator
  store-query paths (read-only, finally-closed per call), refresh writer DAOs
  (finally-closed), and the pre-migration integrity probe `service.py:296`
  (→ `open_connection(read_only=True)`).
- **EXEMPT allowlist (enumerated in the contract test):** `aggregator/runtimes.py`
  and `reader/codex.py` — foreign `~/.codex` DBs, already `mode=ro`; they must
  never receive the WAL factory. The factory's own internal `sqlite3.connect`
  (`schema.py:137`) is the one allowed bare call.
- `_quarantine_db` moves `-wal`/`-shm` siblings with the DB.
- Tests (TDD): the concurrency regression is **deterministically red** on the
  shared design — a `threading.Barrier(2)`-synchronized structural assertion that
  two concurrent panel query calls receive DISTINCT `sqlite3.Connection` objects
  (fails by construction on the shared `_dao_factory` connection; green
  per-call), PLUS a bounded smoke (8 reader threads × 25 iterations against a
  live writer loop through the new path; no `database is locked`, no exceptions;
  Barrier-synchronized, zero sleeps). Quarantine sibling test. Grep-based
  factory-routing contract test in `tests/contract/` encoding the allowlist above.

### FR4 — Catalog (decisions resolved at definition from code)

- **Kanban: DELETE the COMPLETE chain** — route + dispatch + 404-body line +
  `_GET_ONLY_API_ROUTES_RE`/405 branch (`handler.py:294`) + `views/kanban.py` +
  the WHOLE `assets/css/kanban.py` file + the nine kanban tokens
  (`tokens.py:121-129`) + composition root (`container.py:82` import,
  `:1238-1242` views-dict entry, and the kanban-only
  `_build_alive_contexts_provider`/`AliveContextsProvider` at `:339` IF no other
  consumer — implementer confirms) + its tests. `session_identity.py:171,183`
  kanban-referencing enumeration API: remove if no other caller survives, else fix
  the stale doc reference.
- **Mermaid: ESCAPE** fence content in `_md_render.block_code` (class kept) AND
  delete the dead `window.mermaid.run()` block (`academy.js:146-147`).
- **Token drift-check: DELETE** (`service.py:181-197`).

## 4. Non-goals

- NO cost tracking for codex/pi; NO new tabs or visual redesign (R11); NO CSP
  hash or loopback/Host-guard changes; NO `list_workflows` pruning (R5); NO panel
  memory edit during implementation (CLOSURE-phase `panel.md` refresh); NO
  connection pool (per-call is the sized-right design — reviewed and affirmed).

## 5. Acceptance criteria

- **AC-1 (ordering, greppable):** the W1 commit (`feat(T-52-10)`) contains BOTH the
  aggregate endpoint AND the server-side list/detail deletion; the W2 commit
  (`feat(T-52-11)`) containing the client list deletion comes AFTER it in
  `git log` — at no commit does the client list code exist without a server
  aggregate. Verified by commit order + per-commit content.
- **AC-2 (dashboard-only):** rendered section has grid+banner+badge and NO
  table/filter/drawer markup; `sessions.js` has no list path and no 10s interval;
  grep proves `render_api_session_detail`, `list_sessions(`, `get_session(` gone
  from production INCLUDING `service.py` (facades deleted;
  `list_sessions_by_agent` excepted).
- **AC-3 (reliability, TDD-verifiable):** the RED commit
  (`test(T-52-12): ... RED`) precedes the fix commit and its structural
  distinct-connection assertion fails at the RED commit; after the fix: regression
  + smoke green, quarantine moves siblings, the allowlist-scoped factory contract
  passes, `check_same_thread=False` is gone.
- **AC-4 (catalog, comprehensive greps):** `grep -rn kanban dadaia_workspace/`
  returns NO functional hits (route/view/CSS/tokens/container/regex all gone);
  `/api/kanban` → standard 404; hostile mermaid fence (`<script>` payload) arrives
  escaped; `window.mermaid` absent from `academy.js`; the drift-check gone.
- **AC-5 (panel gates + inventory):** `e2e-panel` green (guards + dashboard spec;
  list spec deleted); the T-52-10 coverage inventory maps every surviving behavior
  of the three deleted test files to a named successor.
- **AC-6 (gates):** ruff format/check + mypy --strict + full pytest (unpiped, real
  exit code) green locally and in CI.
- **AC-7 (mutation-sanity, THREE sabotages):** (a) aggregate endpoint returns
  zeros → dashboard spec FAILS; (b) one store path bypasses the factory → the
  contract test FAILS; (c) the `cost_known` filter dropped from the aggregate SQL
  → the matrix test (case 4/6) FAILS. Each recorded as captured test output on the
  task line (artifact evidence, not commit archaeology) and reverted before
  commit. The hostile-fence test is its own probe (no separate sabotage).

## 6. Risks

- **Hidden list consumers** — grep-verified: only `sessions.js` consumes the list
  payload; docs update at closure.
- **Foreign-DB regression** — the FR3 allowlist exists precisely to keep the WAL
  factory away from `~/.codex`; the contract test encodes it.
- **CSP breakage** — inline scripts untouched; E2E-GUARD-02 catches violations.
- **Concurrency flake** — the red assertion is structural (distinct connections),
  not probabilistic; the smoke is Barrier-bounded with zero sleeps.
- **Playwright evidence is CI-bound** — local sandbox via `PANEL_TEST_REGISTRY` +
  `PANEL_WEB_SERVER_COMMAND` (v0.1.51 pattern); final AC-5 evidence is the PR's
  `e2e-panel` run.
