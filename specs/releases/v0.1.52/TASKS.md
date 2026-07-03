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

- [x] T-52-10 DONE. RED `72caa6cc` (32 failed for the right reasons —
  `aggregate_sessions` missing / envelope mismatch / 503) → feat `21cb8158`.
  Landed: `aggregate_sessions` SQL + facade (dead facades deleted; grep-proof: the
  only surviving hit is a kept dataclass docstring; `list_sessions_by_agent`
  intact at 4 sites); `/api/sessions` aggregate envelope; detail endpoint deleted
  at ALL handler sites + `container.py` `api_session_detail` unwiring (caught
  beyond the SPEC enumeration); 2 collateral tests updated
  (`test_handler_route_classification`, `test_no_auth_contract`). Scope run: 38
  passed (3 reworked files) + **915 passed, exit 0** (panel+telemetry+contract) +
  ruff/mypy clean. COVERAGE INVENTORY recorded in the W1 handoff
  (`2026-07-02T234313Z-software-engineer-T-52-10.handoff.json`): every surviving
  behavior mapped to a named successor (matrix cases 1-8, auth/503/Host-guard,
  deleted-route 404); list/detail-only behaviors (pagination, ordering, per-row
  fields, event_timestamps) intentionally dead; `/api/agents/<id>/sessions`
  coverage confirmed intact (10 named tests). Design note for QA: codex/pi cost
  forced null/false via `_COST_UNKNOWN_RUNTIMES` even against stray stored data.
  Owner: software-engineer.

## W2 — FR2 dashboard-only view (write set: PLAN §W2)

- [x] T-52-11 DONE — `3d66016c` (7 files, +472/−1736; after `feat(T-52-10)` ⇒
  AC-1 order holds). sessions.js 710→211 (−499), scaffold 116→65, CSS 509→94
  (−415); badge extracted; runtime switcher + `#section-sessions` preserved
  (response-guard assumptions intact); `#sessions-meta` dropped (no updater, no
  test references). New `sessions-dashboard.spec.ts` E2E-SES-DASH-01..04 green
  against a local sandbox (mocked aggregate; console-error-free); list spec
  deleted. AC-7 sabotage (a-variant, endpoint mocked so the JS mapping is the
  gated surface) RECORDED: one line `var costVal = true ? 'N/A'` ⇒ DASH-01/02
  FAIL exactly on the cost mapping (`Expected "$1.73" Received "N/A"`; exit 1);
  reverted; 4 passed exit 0. Unit scope 583 passed exit 0; ruff/mypy clean.
  Collateral fix: `test_views_index.py:161` repointed from the deleted
  `sessions-tbody` to `sessions-dashboard`. Owner: software-engineer.

## W3 — FR3 telemetry reliability (write set: PLAN §W3)

- [x] T-52-12 TDD: `test(T-52-12): distinct-connection RED` commit
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
  - DONE — RED `0794dae3` (structural TypeError: no `connection_factory`;
    contract flags panel.py:52 + service.py:295; quarantine red) → fix
    `93e8b75e`. Shape: factory CALLABLE on `TelemetryAggregator`, per-method
    open/finally-close (`_open_conn`/`_impl` pattern); DAO untouched (aggregator
    is the sole connection consumer); `check_same_thread=False` GONE; integrity
    probe via `open_connection(read_only=True)` (ro skips WAL); quarantine moves
    `-wal`/`-shm`. Scope: **935 passed exit 0**; ruff/mypy clean. AC-7(b)
    captured: bare connect restored ⇒ contract FAILS (panel.py:[67], exit 1);
    AC-7(c): cost_known filter dropped ⇒ 6 matrix tests FAIL (case4/6/3/7 +
    top_agent, exit 1); both reverted, re-run green. Foreign readers CONFIRMED
    untouched (`runtimes.py`, `codex.py`, `store/dao.py` absent from the diff).
    Collateral: `test_service.py::test_cost_backfill` → file-backed (refresh now
    correctly closes its connection). Marked [x].

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
