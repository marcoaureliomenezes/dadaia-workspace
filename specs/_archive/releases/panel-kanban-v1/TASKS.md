# TASKS — panel-kanban-v1

**Status:** Aprovado
**Release ID:** panel-kanban-v1
**Owner:** product-engineer
**Opened:** 2026-05-30

> **Activation gate (hard — no exceptions):**
> Implementation must NOT begin until ALL conditions are true:
> 1. `spec-context-session-locks-v1` (R2) ACTIVE.md phase = `ARCHIVED`
>    — session files at `.dadaia/sessions/*.json` only exist after R2 ships.
> 2. `panel-ux-fix-v1` task T-PUX-06 (loopback auth bypass) is merged.
>    — `/api/kanban` auth on loopback binds depends on it.
> 3. SPEC.md + PLAN.md both have `**Status:** Aprovado`.
>
> SPEC/PLAN/TASKS authoring is unblocked now. No code may be merged before all three
> activation conditions are satisfied.

---

## K-1 — `/api/kanban` backend endpoint + view

**Owner:** software-engineer-python
**Depends on:** activation gate satisfied (all three conditions above)
**SPEC cluster:** §3 K-1; §4 architecture deltas; §8 AC-1
**Target files:**
- `dadaia_workspace/features/panel/views/kanban.py` (new)
- `dadaia_workspace/features/panel/handler.py`

**Preconditions:**
- R2 (`spec-context-session-locks-v1`) ARCHIVED — `.dadaia/sessions/` directory and
  session file schema (`mode`, `last_seen_at`, `ttl_seconds`, `context`, `release`,
  `runtime`, `pid`, `session_id`) are defined by R2.
- `panel-ux-fix-v1` T-PUX-06 merged — loopback bypass active for all `/api/*` routes.

**Work steps:**
1. Create `kanban.py` view:
   - Glob `.dadaia/sessions/*.json`; if directory absent return 200 with empty swimlanes.
   - Parse each file; silently skip malformed JSON or files missing required fields.
   - Compute `is_stale`: `(now - last_seen_at) > ttl_seconds`.
   - Map mode to column per SPEC §3 K-1 table: READ→research, SPEC→spec,
     BOUND_IMPLEMENTATION→implementation, BOUND_REVIEW→review, unknown→research.
   - Group `SessionCard` objects by context; assemble `swimlanes` list.
   - Return JSON response with `generated_at` ISO-8601 and `swimlanes`.
2. Update `handler.py`:
   - Add `(r"^/api/kanban$", "api_kanban")` to `_RAW_ROUTES`.
   - Add `"api_kanban"` to `_BEARER_AUTH_ROUTE_NAMES` and `_BEARER_ONLY_ROUTES`.
   - Add route for Kanban HTML tab shell (served by `kanban.py`).
   - POST to `/api/kanban` → 405.
3. Write unit and integration tests covering AC-1.1 through AC-1.14.

**Done criterion:**
All of the following AC-IDs pass in `poetry run pytest`:
- AC-1.1 All four column keys present, each a list.
- AC-1.2 READ mode → research column.
- AC-1.3 SPEC mode → spec column.
- AC-1.4 BOUND_IMPLEMENTATION → implementation column.
- AC-1.5 BOUND_REVIEW → review column.
- AC-1.6 Missing sessions dir → 200, empty swimlanes.
- AC-1.7 Empty sessions dir → 200, empty swimlanes.
- AC-1.8 `last_seen_at` 10 min ago, `ttl_seconds=180` → `is_stale: true`.
- AC-1.9 30 s ago, `ttl_seconds=300` → `is_stale: false`.
- AC-1.10 Unknown mode → no 500; card in research or excluded.
- AC-1.11 POST `/api/kanban` → 405.
- AC-1.12 Corrupt JSON file silently skipped; valid session appears.
- AC-1.13 `loopback_bypass=False`, no token → 401.
- AC-1.14 `loopback_bypass=True` → 200 without Authorization header.

[x] K-1

---

## K-2 — Kanban frontend (tab, JS, CSS)

**Owner:** frontend-engineer
**Depends on:** K-1 API contract stable (SPEC §3 K-1 response schema is the contract;
K-1 does NOT need to be merged for frontend dev to begin — mock against the SPEC schema)
**SPEC cluster:** §3 K-2; §4 architecture deltas; §8 AC-2
**Target files:**
- `dadaia_workspace/features/panel/views/assets/js/kanban.js` (new)
- `dadaia_workspace/features/panel/views/assets/css/kanban.css` (new)
- `dadaia_workspace/features/panel/views/index.py`
- `dadaia_workspace/features/panel/views/tokens.py` (add new design tokens)

**Preconditions:**
- Activation gate satisfied (K-2 must not be merged before R2 ARCHIVED).
- K-1 SPEC §3 K-1 response schema treated as contract for mocking. K-1 merged before
  Playwright E2E suite runs (PW-KAN-01..05 require real backend).

**Work steps:**
1. Add design tokens to `tokens.py` per SPEC §3 K-2 token list:
   `--color-kanban-separator`, `--color-kanban-lane-header-bg`,
   `--color-kanban-locked-overlay`, `--opacity-kanban-locked`,
   `--kanban-col-min-w`, `--kanban-card-min-h`, `--kanban-card-gap`,
   `--kanban-lane-gap`.
2. Create `kanban.css`:
   - Swimlane × 4-column grid; `--kanban-col-min-w: 200px`; horizontal scroll below 800px.
   - Card anatomy: font-mono session ID + status dot, model line (muted), runtime + age
     (muted). Card `min-height: var(--kanban-card-min-h)`.
   - Locked column: `kanban-column--locked` class; `data-locked="true"`;
     `opacity: var(--opacity-kanban-locked, 0.40)` on locked column.
   - Empty column placeholder: dashed border, `data-testid="kanban-empty-placeholder"`,
     `aria-hidden="true"`.
   - Card appear animation: `opacity 0 → 1`, `--duration-normal: 220ms`,
     `--easing-decelerate`; suppressed under `@media (prefers-reduced-motion: reduce)`.
   - Column header badges: Definition `≤2`, Implementation `×1`, Review `×1`.
3. Create `kanban.js`:
   - Fetch `/api/kanban`; render swimlanes with lanes `<section aria-labelledby>` and
     columns `<div role="group" aria-labelledby>`.
   - Render each card: `role="article"`, `tabindex="0"`,
     `aria-label="Session [id], [model], [runtime], [age], [status]"`.
   - XOR lock visual: when a lane has a card in `review`, dim `implementation` column
     (set `data-locked="true"`, add `kanban-column--locked`); vice versa.
   - Lock icon (U+1F512 or inline SVG) on locked column header.
   - ARIA supplement on locked header: `"[Phase] column, locked — context is in [other phase]"`.
   - Empty lane: visible text "No active sessions" (announced by screen reader).
   - Empty board: centred "No Spec Context Projects available".
   - Poll for updates (interval per existing panel pattern).
4. Update `index.py`: add `#tab-kanban` nav entry and tab panel section.
5. Write Playwright tests PW-KAN-01 through PW-KAN-05 using deterministic
   `waitForSelector` (no `time.sleep` / `waitForTimeout`).
   Evidence folder: `.dadaia/tmp/qa-engineer/panel-kanban-v1/`.

**Done criterion:**
All of the following AC-IDs pass:
- AC-2.1 (PW-KAN-01) 2 BOUND_IMPLEMENTATION sessions from distinct contexts → 4 columns
  visible; implementation column has 2 cards from 2 distinct `data-context` values.
- AC-2.2 (PW-KAN-02) 4 sessions, one per mode → each column has exactly 1 card; session
  IDs match fixture.
- AC-2.3 (PW-KAN-03) Context has BOUND_IMPLEMENTATION → review column has
  `data-locked="true"` + CSS class `kanban-column--locked`.
- AC-2.4 (PW-KAN-04) No session files → 4 columns visible; each has
  `data-testid="kanban-empty-placeholder"`.
- AC-2.5 (PW-KAN-05) One stale session → card has `data-stale="true"`.
Tokens added to `tokens.py`; WCAG AA ratios match SPEC §3 K-2 audit table.

[x] K-2

---

## K-3 — Handoff-v1.1 schema: `verdict` field

**Owner:** software-engineer-python
**Depends on:** activation gate satisfied (disjoint from K-1 and K-2; may run in parallel)
**SPEC cluster:** §3 K-3; §8 AC-4
**Target files:**
- `dadaia_workspace/public/schemas/handoff-v1.schema.json`
  (confirmed path — lib-originated; must also propagate via `dadaia public stage` +
  `dadaia public install --target all` after edit)

**Preconditions:**
- Activation gate satisfied.
- Note: schema lives ONLY in `dadaia_workspace/public/schemas/handoff-v1.schema.json`
  (not in a separate `data/schemas/` path — confirmed by workspace glob). After editing
  the source, flag devops-engineer to run:
  `dadaia public stage && dadaia public install --target all`.

**Work steps:**
1. Add optional top-level field `verdict` to `handoff-v1.schema.json`:
   - Type: string, enum `["APPROVED", "REJECTED"]`, nullable/absent is valid.
   - Add optional `verdict_reason`: type string, no enum constraint.
   - Ensure the field is optional (no `required` entry) so existing sidecars remain valid.
2. Write or update schema tests covering AC-4.1 through AC-4.3:
   - Schema accepts sidecar with `verdict: "APPROVED"`.
   - Schema accepts sidecar with `verdict: "REJECTED"`.
   - Schema accepts sidecar without `verdict` (field absent — backward compat).
   - `dadaia reports validate <path>` exits 0 on a sidecar with `verdict: "APPROVED"`.
3. Flag devops-engineer to propagate: `dadaia public stage && dadaia public install --target all`.

**Done criterion:**
- AC-4.1 Schema accepts `verdict: "APPROVED"` or `"REJECTED"` top-level optional field.
- AC-4.2 Existing sidecars without `verdict` continue to validate.
- AC-4.3 `dadaia reports validate <path>` exits 0 on handoff-v1.1 sidecar with
  `verdict: "APPROVED"`.
- `dadaia public doctor` exits 0 after propagation (devops-engineer confirms).

[x] K-3

---

## K-QA-RACE — Impl-XOR-Review lock-conflict and race tests

**Owner:** software-engineer-python
**Depends on:** K-1 (session mode mapping logic must be in place); R2 ARCHIVED (lock layer
exists); activation gate satisfied
**SPEC cluster:** §8 AC-3.1..3.8
**Target files:**
- `tests/` (new test file, e.g. `test_kanban_lock_conflict.py`)

**Preconditions:**
- R2 ARCHIVED — `ReviewBlockedByImplementationError`, `ImplementationBlockedByReviewError`,
  `LockHeldError`, `JsonContextStore` lock layer all from R2.
- No `time.sleep` in any concurrency test (CI grep gate enforced).

**Work steps:**
1. Write deterministic lock-conflict unit tests (AC-3.1..3.6) using real
   `JsonContextStore` on `tmp_path` (never `FakeContextStore`):
   - AC-3.1 HELD impl lock blocks review bind → `ReviewBlockedByImplementationError`.
   - AC-3.2 HELD review session blocks impl bind → `ImplementationBlockedByReviewError`.
   - AC-3.3 Impl + review on DIFFERENT releases coexist (no conflict).
   - AC-3.4 After `release_lock()`, review bind succeeds.
   - AC-3.5 Stale impl lock still blocks review until reclaim.
   - AC-3.6 Two BOUND_IMPLEMENTATION binds on same release → `LockHeldError` on second.
2. Write barrier-based race tests (AC-3.7..3.8):
   - AC-3.7 `threading.Barrier(2)`: impl vs review race → exactly 1 success, 1 failure;
     lock file has winner as owner.
   - AC-3.8 `threading.Barrier(2)`: two impl binds race → exactly 1 success, `LockHeldError`
     for second.
   - All threads joined with `timeout=5`; test fails if any thread alive after join.
3. Verify CI grep gate passes: `grep -rn "time\.sleep" tests/ | grep -v "# allowed-sleep"`
   must exit non-zero (no unapproved sleeps).

**Done criterion:**
- AC-3.1 through AC-3.8 all pass in `poetry run pytest`.
- All threads in race tests joined with `timeout=5`.
- No `time.sleep` without `# allowed-sleep` comment.
- Tests run with `pytest --randomly-seed=last` (order-independent).

[x] K-QA-RACE

---

## K-QA-PW — Playwright board scenarios (qa-engineer)

**Owner:** qa-engineer
**Depends on:** K-1 merged; K-2 merged; activation gate satisfied
**SPEC cluster:** §8 AC-2.1..2.5
**Target files:**
- `.dadaia/tmp/qa-engineer/panel-kanban-v1/` (screenshots, evidence)

**Preconditions:**
- K-1 and K-2 both merged (real backend + frontend available).
- Panel server running (local or CI).

**Work steps:**
1. Run Playwright test suite for PW-KAN-01 through PW-KAN-05 (authored by frontend-engineer
   in K-2; qa-engineer runs and validates):
   - PW-KAN-01 (AC-2.1): 2 distinct BOUND_IMPLEMENTATION sessions.
   - PW-KAN-02 (AC-2.2): 4 sessions, 1 per mode.
   - PW-KAN-03 (AC-2.3): BOUND_IMPLEMENTATION → review column locked.
   - PW-KAN-04 (AC-2.4): No session files → all columns empty.
   - PW-KAN-05 (AC-2.5): Stale session → `data-stale="true"` on card.
   All tests use deterministic `waitForSelector` — no `time.sleep` / `waitForTimeout`.
2. Capture screenshots to `.dadaia/tmp/qa-engineer/panel-kanban-v1/`.
3. Emit green QA handoff sidecar with `verdict: "APPROVED"` (uses handoff-v1.1 schema
   from K-3).

**Done criterion:**
- AC-2.1 through AC-2.5 all pass.
- Screenshots present in `.dadaia/tmp/qa-engineer/panel-kanban-v1/`.
- QA handoff sidecar emitted with `verdict: "APPROVED"`.

[x] K-QA-PW

---

## K-CI — Dual-approval CI gate

**Owner:** devops-engineer
**Depends on:** K-3 merged and propagated; activation gate satisfied
**SPEC cluster:** §9 (dual-approval gate mentioned; §3 K-3 CI check spec)
**Target files:**
- `.github/workflows/*.yml` (add `jq '.verdict'` check step)

**Preconditions:**
- K-3 merged; `dadaia public doctor` exit 0 confirmed.
- QA and security-reviewer handoff sidecar paths known.

**Work steps:**
1. Wire the `jq '.verdict'` check for qa-engineer handoff sidecar in the CI YAML:
   `jq '.verdict' <qa-handoff.json>` must equal `"APPROVED"`.
2. Wire the `jq '.verdict'` check for security-reviewer handoff sidecar:
   `jq '.verdict' <security-handoff.json>` must equal `"APPROVED"`.
3. If either sidecar is missing or `verdict != "APPROVED"`: CI step exits non-zero,
   release CLOSURE check fails, findings route back to implementer.
4. After K-3 schema edit and propagation: run `dadaia public stage &&
   dadaia public install --target all` and confirm `dadaia public doctor` exit 0.

**Done criterion:**
- CI YAML contains dual-approval check for qa-engineer and security-reviewer sidecars.
- `dadaia public doctor` exits 0 after K-3 schema propagation.
- CI run green with a `verdict: "APPROVED"` sidecar present (evidence: CI run URL or
  stdout snippet).

[x] K-CI

---

## Parallelism notes

Tasks K-1, K-2, and K-3 have disjoint write sets and may run in parallel once the
activation gate is satisfied. K-2 may begin against the SPEC §3 K-1 schema contract
without waiting for K-1 to merge; Playwright E2E (K-QA-PW) requires both K-1 and K-2
merged.

K-QA-RACE depends on K-1 (for the session-mode mapping layer) and on R2 being ARCHIVED
(for the lock layer); it may run in parallel with K-2 and K-3.

K-QA-PW depends on K-1 + K-2 merged. K-CI depends on K-3 merged.

Only one `[-]` marker is permitted per owner at a time unless the above disjoint-set
parallelism is explicitly in play between different owners.

---

## Cross-release note

This release (R3) depends on `spec-context-session-locks-v1` (R2) being ARCHIVED before
any implementation task may begin. The BOUND_REVIEW mode accepted by the operator via
grill-me 2026-05-30 is part of R2 and is a prerequisite for the K-1 review column and
for the K-QA-RACE Impl-XOR-Review tests.
