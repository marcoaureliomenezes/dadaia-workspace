# CLOSURE — v0.1.52 — Panel Plumbing

**Status:** Aprovado
**Branch:** `feature/v0.1.52` · **Base:** `ccc47934` (v0.1.51 closure) · **Merged:** `fd23ea5e` (PR #93, 38 checks: 35 pass / 3 skipping, squash)
**Origin:** operator-approved release sequence R4 (grill 2026-07-02; operator-elected
early position) consuming 2 backlog entries and remediating the root-chain of the
deferred bug `panel-telemetry-sqlite-corrupts-under-concurrent-access` (its stream
already carries the terminal `deferred` event — no new bug event; chain remediated).

## Summary

The panel's plumbing is sound: `/api/sessions` serves a SERVER-side aggregate cost
summary through a proper facade (the client list, its detail endpoint, and the dead
query surface are gone — net −4,770 lines against +2,268), the Sessions tab is the
operator-decided aggregated-cost dashboard only, every telemetry-store SQLite
connection flows through the pragma'd WAL+busy_timeout factory with per-call
read-only connections (the shared cross-thread `check_same_thread=False` connection
— the corruption root — is eliminated, quarantine is WAL-aware, and an AST-based
allowlist contract keeps the WAL-writing factory away from the operator's foreign
`~/.codex` read-only DBs), the kanban chain is completely deleted (`grep -i kanban`
over production returns nothing), mermaid fences are entity-escaped, and the dead
auth-era drift-check is removed.

## Shipped (conventional commits on `feature/v0.1.52`, squash-merged)

- `cef21bd3` docs(T-52-01) — definition (dual REJECT→amend→Aprovado).
- `72caa6cc` test(T-52-10) RED → `21cb8158` feat(T-52-10) — aggregate endpoint +
  server-side list/detail deletion (facade layering; container unwiring).
- `3d66016c` feat(T-52-11) — dashboard-only view (sessions.js 710→211, CSS 509→94).
- `0794dae3` test(T-52-12) RED → `93e8b75e` fix(T-52-12) — connection factory
  (structural distinct-connection assertion; allowlist contract; WAL-aware
  quarantine).
- `313661bd` feat(T-52-13) — kanban chain deletion + mermaid escape + drift-check
  removal (+ two adjudicated dead APIs: `iter_session_records`,
  `is_stale_session`).
- `e47e6eb3` (W4 record + e2e kanban-tuple fix) · `a76d0735` review(T-52-20) QA
  APPROVE · `50de94fb` chore(T-52-21) — consumed-backlog archival at ship (the
  dead-anchor BL-SCHEMA fix).

## Evidence triples (AC → command → observed)

- **AC-1** → per-commit content — `21cb8158` carries aggregate + server deletion
  together; `3d66016c` (client deletion) follows → ordering constraint held.
- **AC-2** → greps → `render_api_session_detail`/`list_sessions(`/`get_session(`
  zero in production (facades included); `list_sessions_by_agent` intact.
- **AC-3** → detached worktree at `0794dae3` → structural test FAILS red; on HEAD:
  16 reliability tests green; `check_same_thread` gone; allowlist contract passes.
- **AC-4** → `grep -rn -i kanban dadaia_workspace/` → zero; hostile mermaid fences
  escaped; `window.mermaid` gone; drift-check gone.
- **AC-5** → coverage inventory in the T-52-10 handoff (every surviving behavior
  named); PR #93 `E2E panel (Playwright)` → **pass** (the stated merge condition).
- **AC-6** → full suite → **4,360 passed / 17 skipped, exit 0** (twice: orchestrator
  + QA gate, PIPESTATUS-captured); ruff/mypy clean; PR #93 38 checks green.
- **AC-7** → three sabotage artifacts on the task lines (JS cost mapping, factory
  bypass, cost_known filter) — each captured failing, reverted, re-run green.

## Review ladder

- Definition: software-architect REJECT→APPROVE (BLOCKERs: `TelemetryService`
  facade layering + dead-facade deletion; factory contract scoped with an
  enumerated foreign-ro allowlist; `container.py` unwiring — an ImportError-at-
  startup caught at definition) + qa-engineer REJECT→APPROVE (BLOCKERs: greppable
  commit convention; allowlist scope; 8-case cost-known matrix + coverage
  inventory; deterministic structural red).
- Ship gate: qa-engineer **APPROVE** on `e47e6eb3`, including the SPECIAL
  ADJUDICATION of the frozen-suite file deletion: `is_stale_session` was
  kanban-only (verified pre-W4), its test covered only the session-TTL predicate
  (never the pid-veto/no-steal invariant), and the other 8 frozen files are
  diff-clean vs main — v0.1.50's no-steal freeze preserved.
- Push gate: security-reviewer **APPROVED** for `a76d0735`, EXTENDED to `50de94fb`
  after the specs-only delta re-review (0 findings above INFO; foreign-DB
  allowlist verified at the wiring level; CSP hashes byte-identical; the aggregate
  payload drops per-session `cwd`/`ai_title`/`session_id` — net PII reduction).

## Validations

| Check | Result | Evidence |
|---|---|---|
| pytest (full suite, PIPESTATUS) | 4,360 passed / 17 skipped, exit 0 | orchestrator + QA gate |
| ruff format --check + ruff check | clean (753 files) | ship gate |
| mypy --strict | clean (297 files) | ship gate |
| Frozen no-steal suite (8 surviving files) | diff-clean vs main | QA adjudication |
| e2e-panel CI job (dashboard spec + guards) | pass ×2 runs | PR #93 |
| backlog doctor (CI-exact) | clean after the at-ship archival | fix commit `50de94fb` + green re-run |
| lint-memory-atoms | All atoms passed lint | closure run |
| memory catalog | regenerated | closure run |
| specs doctor | 0 errors | closure run (below) |
| CI (PR #93) | 38 checks: 35 pass / 3 skipping | merge gate |

## Drifts

- **Process discovery (recorded for the ritual):** a release that DELETES an
  anchored symbol invalidates its consuming backlog entry's ref before closure —
  the fail-closed BL-SCHEMA registry correctly went red in CI. Resolution adopted:
  consumed-backlog archival moves forward from closure to SHIP for entries whose
  anchors die with the release (durable copies + ledger landed in `50de94fb`).
  Not a tool bug (the gate worked as contracted); no bug event.
- Security INFO-1: quarantine sibling-move micro-window (lock-guarded,
  self-healing) — no action. INFO-2: the aggregator's legacy shared-`dao` mode
  (unused in production, mutually excluded with the factory) — cleanup candidate
  for R5 hygiene.
- The deferred SQLite bug's stream stays terminal (`deferred`); its root chain is
  remediated here — recorded in this CLOSURE, no new event (one-terminal-event law).

## Backlog returns

None. Both consumed entries shipped in full; the security INFO-2 (legacy shared-dao
mode) is left to R5's `hygiene-and-dead-code-cleanup` scope, which already owns
dead-code sweeps.

## Memory updates (this closure)

- `panel.md`: Sessions tab re-documented as the aggregated-cost dashboard (aggregate
  envelope, cost render mapping, no list/drawer/detail); kanban chain recorded
  DELETED (route table, views list, state-read lines updated); telemetry store
  access documented as per-call read-only factory connections; mermaid fences
  entity-escaped note. `release_origin: v0.1.52`.
