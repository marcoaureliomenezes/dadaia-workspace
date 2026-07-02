# TASKS — v0.1.52 — Panel Plumbing

**Status:** Aprovado

Markers: `[ ]` open · `[-]` in progress · `[x]` done. One `[-]` per owner unless write
sets are disjoint (PLAN §Write sets; service.py/handler.py shared — sequential only).

## W0 — definition

- [x] T-52-01 SPEC/PLAN/TASKS authored from the 2026-07-02 inspection; dual
  definition review REJECT×2 — architect BLOCKERs: `TelemetryService` facade +
  dead-facade deletion (W1 gains service.py; AC-2 grep extended), factory contract
  re-scoped to store-writable connections with an ENUMERATED exempt allowlist
  (foreign ro `~/.codex` readers must never see the WAL factory; integrity probe →
  ro factory mode), container.py unwiring added (ImportError-at-startup caught),
  FR4 residue enumeration (405 regex, tokens, whole CSS file, dead mermaid.run(),
  session_identity API), three-way shared-file note, `active_sessions` added to
  the aggregate, badge-extraction note; QA BLOCKERs: commit convention (greppable
  RED commits; AC-7 evidence as task-line artifact), same allowlist scope,
  8-case cost-known matrix + coverage-inventory contract, deterministic structural
  red (Barrier + distinct-connection assertion, not probabilistic), third sabotage
  (cost_known filter), comprehensive multi-site greps. ALL landed; three files
  `Aprovado`; definition commit. Owner: product-engineer (orchestrated).

## W1 — FR1 aggregate endpoint (write set: PLAN §W1)

- [ ] T-52-10 TDD: `test(T-52-10): aggregate matrix RED` commit (8-case cost-known
  matrix + deleted-route 404), then ONE `feat(T-52-10)` commit: `aggregate_sessions`
  SQL + `TelemetryService.aggregate_sessions` facade + `/api/sessions` payload
  switch + DELETE detail endpoint at ALL handler sites + DELETE dead facades
  (`TelemetryService.list_sessions`/`get_session`) + aggregator
  `list_sessions`/`get_session` (`list_sessions_by_agent` stays) + the three
  list-era test files replaced by matrix successors. Coverage inventory (deleted
  behaviors → named successors, incl. `/api/agents/<id>/sessions` intact) recorded
  on this line. Owner: software-engineer.

## W2 — FR2 dashboard-only view (write set: PLAN §W2)

- [ ] T-52-11 Extract `#sessions-last-updated` from the toolbar, THEN delete
  toolbar/table/drawer/skeleton; `sessions.js` → aggregate fetch + 4 cards
  ("N active" + top-agent sub-labels preserved; 'N/A'/'—'/'$X.XX' mapping per the
  FR1 matrix) + banner + `dadaia:runtime-change` re-fetch; CSS prune; DELETE
  `test_panel_sessions_tab.spec.ts`; ADD `sessions-dashboard.spec.ts` (mocked
  aggregate per matrix case, no console errors). AC-7 sabotage (a): aggregate →
  zeros ⇒ dashboard spec FAILS (captured output on this line; reverted). CSP
  inline scripts untouched. Owner: software-engineer.

## W3 — FR3 telemetry reliability (write set: PLAN §W3)

- [ ] T-52-12 TDD: `test(T-52-12): distinct-connection RED` commit
  (Barrier(2)-synchronized structural assertion — two concurrent panel query calls
  must use DISTINCT connections; fails by construction on the shared
  `check_same_thread=False` design), then the fix commit: `open_connection` +=
  busy_timeout + `read_only` mode (ro skips the WAL pragma); `_dao_factory` and
  store query/refresh paths per-call through the factory (finally-closed);
  integrity probe → `open_connection(read_only=True)`; `_quarantine_db` moves
  `-wal`/`-shm`; bounded smoke (8 readers × 25 iterations vs live writer,
  Barrier-started, no sleeps); allowlist-scoped factory contract test
  (`tests/contract/` — exempt: `aggregator/runtimes.py`, `reader/codex.py`,
  `schema.py:137` itself). AC-7 sabotages (b) factory bypass ⇒ contract FAILS and
  (c) `cost_known` filter dropped ⇒ matrix case 4/6 FAILS (captured outputs on
  this line; reverted). Owner: software-engineer.

## W4 — FR4 catalog (write set: PLAN §W4; sequential after W1/W3 — shared files)

- [ ] T-52-13 DELETE the complete kanban chain: handler route + dispatch + 404 line
  + `_GET_ONLY_API_ROUTES_RE`/405 branch; `views/kanban.py`; the WHOLE
  `assets/css/kanban.py`; `tokens.py:121-129` kanban tokens; `container.py`
  unwiring (import :82, views-dict entry :1238-1242, kanban-only provider :339 if
  orphaned — confirm and record); `session_identity.py` kanban-only API removed or
  doc fixed (confirm callers, record); kanban tests. `_md_render.block_code`
  escapes fence content (hostile `<script>` fence test); DELETE the dead
  `window.mermaid.run()` block (`academy.js:146-147`); DELETE the token
  drift-check (`service.py:181-197`). Panel must construct (container import
  sanity test). Owner: software-engineer.

## W5 — gates + ship (flat release: single ship gate)

- [ ] T-52-20 QA review (ship gate): every AC live — AC-1 commit order + content;
  AC-2/AC-4 comprehensive greps (incl. service.py facades and all handler.py
  kanban/detail sites); AC-3 red-commit checkout verification; AC-5 inventory
  re-derivation; AC-7 three captured-output artifacts on the task lines; suite
  UNPIPED with the real exit code. AC-5's final evidence is the PR's green
  `e2e-panel` run. Verdict lands as a review commit. Owner: qa-engineer.
- [ ] T-52-21 Security review (push gate): APPROVE handoff with
  `metrics.commit_sha` = pushed sha (attention: foreign-DB allowlist integrity,
  mermaid escape, deleted auth-era drift-check); push; CI green (incl.
  `e2e-panel`); PR; merge. Owner: security-reviewer + orchestrator.

## W6 — closure (CLOSURE phase)

- [ ] T-52-30 CLOSURE.md (Validations + Drifts — SPEC-DOC-006); consumed entries
  (`panel-sessions-cost-dashboard-only`, `panel-runtime-reliability`) removed with
  durable copies + `consumed_backlog.json`; memory `panel.md` refreshed (tab
  inventory, route table incl. deleted kanban/detail routes, flowchart, usage
  flow) + catalog + lint; archive; ACTIVE → none; candidates R4 row shipped; note
  the deferred SQLite bug chain remediated. Owner: product-engineer.
