# PLAN — v0.1.52 — Panel Plumbing

**Status:** Aprovado

## Wave map

- **W0 — definition**: SPEC/PLAN/TASKS from the 2026-07-02 inspection; dual
  definition review (architect REJECT: facade layering, foreign-DB factory scope,
  container unwiring, deletion-residue enumeration; QA REJECT: commit-convention
  verifiability, allowlist scope, cost-known matrix, deterministic red) — ALL
  folded; `Aprovado`; definition commit.
- **W1 — FR1 aggregate endpoint (FIRST)**: TDD — matrix tests RED
  (`test(T-52-10): ... RED`), then `aggregate_sessions` SQL + `TelemetryService`
  facade + `/api/sessions` payload switch + server-side list/detail deletion (all
  handler sites) + dead-facade prune, in ONE `feat(T-52-10)` commit; coverage
  inventory on the task line.
- **W2 — FR2 dashboard-only view**: badge extraction; scaffold/JS/CSS prune;
  Playwright list spec → dashboard spec. Client list deletion lands here — AFTER
  W1 by commit order (AC-1).
- **W3 — FR3 telemetry reliability**: TDD — structural distinct-connection
  regression RED against the shared design, then factory routing (busy_timeout +
  read-only mode + finally-close + integrity probe via ro mode + WAL-aware
  quarantine) + allowlist-scoped contract test + bounded concurrency smoke.
- **W4 — FR4 catalog**: complete kanban chain delete (incl. `container.py`
  unwiring, 405 regex, tokens, whole CSS file, provider-if-orphaned); mermaid
  escape + dead `mermaid.run()` delete; drift-check delete.
- **W5 — gates + ship (flat release: single ship gate)**: full local gates; QA
  review commit; security push-gate APPROVE keyed to the pushed sha; push; CI
  green (incl. `e2e-panel`); PR; merge.
- **W6 — closure** (CLOSURE phase): CLOSURE.md (Validations + Drifts); consumed
  entries ×2 with durable copies + ledger; memory `panel.md` refreshed (tab
  inventory, route table, flowchart, usage flow); catalog + lint; archive;
  ACTIVE → none; candidates R4 row shipped.

## Commit convention (QA BLOCKER-1 resolution)

Multiple commits per wave, greppable: every TDD red lands as its own
`test(T-52-NN): <what> RED` commit immediately before its `feat|fix(T-52-NN)`
commit. AC-7 sabotage evidence is a task-line ARTIFACT (captured test output),
never a commit. AC-1's check is commit ORDER + content: `feat(T-52-10)` (server
aggregate + server list deletion) precedes `feat(T-52-11)` (client list deletion).

## Write sets (sequential waves; shared files noted)

| Wave | Files |
|---|---|
| W1 | `features/telemetry/aggregator/queries.py`, `features/telemetry/service.py` (facade add + dead-facade delete), `features/panel/views/api.py`, `features/panel/handler.py` (sessions routes/404/docstring), the three list-era test files (replace): `tests/unit/features/panel/test_views_api_sessions.py`, `tests/integration/test_panel_sessions_endpoint.py`, `tests/unit/features/telemetry/test_aggregator_sessions.py` |
| W2 | `features/panel/views/sessions.py`, `views/assets/js/sessions.js`, `views/assets/css/sessions.py`, `tests/unit/features/panel/test_sessions_cost_banner.py` (update to the matrix), `tests/e2e/panel/test_panel_sessions_tab.spec.ts` (delete), new `tests/e2e/panel/sessions-dashboard.spec.ts` |
| W3 | `features/telemetry/store/schema.py`, `features/telemetry/service.py` (quarantine/refresh/integrity-probe), `cli/commands/panel.py`, new contract + concurrency tests, existing telemetry store/service tests |
| W4 | `features/panel/handler.py` (kanban route/404/405-regex), `features/panel/views/kanban.py` (delete), `views/assets/css/kanban.py` (delete), `views/assets/css/tokens.py` (kanban tokens), `views/_md_render.py`, `views/assets/js/academy.js` (dead mermaid block), `features/telemetry/service.py` (drift-check :181-197), `dadaia_workspace/container.py` (unwire import/entry/provider), `features/spec_context/session_identity.py` (kanban-only API or doc fix), kanban tests (delete) |
| W6 | `specs/releases/v0.1.52/**`, `specs/_archive/**`, `specs/memory/product/panel/panel.md` (closure-phase), `specs/backlog/` (removals + candidates row) |

**Shared-file discipline:** `features/telemetry/service.py` is touched by W1
(facades, ~447-483), W3 (quarantine/refresh/integrity, 263-320), and W4
(drift-check, 181-197) — SEQUENTIAL waves, disjoint line ranges, ONE owner, no
parallel `[-]`. `features/panel/handler.py` is touched by W1 (sessions sites) and
W4 (kanban sites) — same discipline.

## Test strategy

- W1: the FR1 cost-known matrix (8 cases) as unit SQL + view-envelope + integration
  endpoint tests against seeded tmp stores; deleted-route 404; coverage inventory
  (behaviors of the 1,699 deleted lines → named successors) on the task line.
- W2: scaffold snapshot (no table/drawer markup); dashboard Playwright spec with
  route-intercepted aggregates per matrix case; AC-7 sabotage (a).
- W3: structural distinct-connection RED test (Barrier(2), fails by construction on
  the shared connection); bounded smoke (8×25, Barrier-started, no sleeps);
  quarantine sibling test; allowlist contract test in `tests/contract/`; AC-7
  sabotages (b) and (c).
- W4: hostile mermaid fence; kanban comprehensive-grep assertions; container import
  sanity (panel constructs).
- Full-suite + lint + mypy locally before push (pre-push gate re-runs them).

## Rollback

Single feature branch `feature/v0.1.52`; commits per the convention above; revert =
drop the branch before merge. External consumers of the old list payload: none in
code (grep-verified); docs re-baselined at closure.
