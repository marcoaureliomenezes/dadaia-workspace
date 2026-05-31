# SPEC — panel-kanban-v1

**Status:** Aprovado
**Release ID:** panel-kanban-v1
**Owner:** product-engineer
**Opened:** 2026-05-30
**Amended:** 2026-05-30 — editorial fixes (grill-me): corrected handoff schema path to `dadaia_workspace/public/schemas/handoff-v1.schema.json`; fixed QA evidence folder to `panel-kanban-v1`; clarified `kanban.py` ownership (K-1 creates/owns, K-2 contributes tab HTML only). No scope change.
**Semver target:** MINOR bump on the current feature release
**Sequencing:** Release 3 in the panel evolution track. SPEC authoring is unblocked now.
IMPLEMENTATION waits until `spec-context-session-locks-v1` (R2) is CLOSED — the Kanban
reads the R2 session files at `.dadaia/sessions/*.json` and requires BOUND_REVIEW mode
(added to R2 by the SPEC amendment in this same batch).

---

## 1. Problem and context

The dadaia-workspace panel exposes telemetry (Sessions tab, Agents tab) and navigation
(Projects tab) but has no real-time view of what agents are actually doing across spec
contexts. A product owner who opens the panel cannot tell at a glance how many agents
are implementing, reviewing, or reading specs — they must query each context individually.

The R2 state model (`spec-context-session-locks-v1`) introduces session files at
`.dadaia/sessions/<session_id>.json` that encode exactly this information: which agent is
bound to which context/release, in which mode (READ, SPEC, BOUND_IMPLEMENTATION,
BOUND_REVIEW), and whether the session is still alive. A Kanban view over these session
files gives the operator a single-pane view of the current multi-agent workflow state.

**Primary source material consumed:**
- Architect ADR: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-30T140000Z-adr-panel-hardening-kanban.html` (decision C)
- Design spec: `.dadaia/reports/dadaia-workspace/design-specialist/2026-05-30T140000Z-design-spec-panel-hardening-kanban.html` (section B)
- QA strategy: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-30T143000Z-test-strategy-panel-hardening-kanban.html` (Parts 2 + 3)

---

## 2. Objective

Deliver a read-only Kanban tab on the panel that shows the current multi-agent state:
one swimlane per Spec Context Project; four phase columns (Research, Definition,
Implementation, Review); cards = a session's binding on that context. Cards move
autonomously as session mode changes. No manual drag, no action buttons in v1.

Additionally, add a `verdict` field to the handoff-v1.1 schema so the dual-approval gate
(qa-engineer AND security-reviewer) is machine-checkable at release CLOSURE.

---

## 3. Scope clusters

### K-1 — `/api/kanban` GET endpoint (`api.py` / `kanban.py` view)

**Data source:** `.dadaia/sessions/*.json` files (R2 session files, NOT the telemetry
SQLite DAO). The `TelemetryDao` / `TelemetryAggregator` are not touched.

**Response schema:**

```json
{
  "generated_at": "<ISO-8601>",
  "swimlanes": [
    {
      "context": "dadaia-workspace",
      "columns": {
        "research":       [ SessionCard, ... ],
        "spec":           [ SessionCard, ... ],
        "implementation": [ SessionCard, ... ],
        "review":         [ SessionCard, ... ]
      }
    }
  ]
}
```

`SessionCard` shape:

```json
{
  "session_id":   "sess_8f3a2c01",
  "mode":         "BOUND_IMPLEMENTATION",
  "release":      "spec-context-tree-v2",
  "runtime":      "claude-code",
  "pid":          18423,
  "last_seen_at": "2026-05-30T10:04:30Z",
  "is_stale":     false
}
```

`is_stale` is computed at read time: `(now - last_seen_at) > ttl_seconds` (mirrors
`spec-context-session-locks-v1` §T-12 definition).

**Session mode → Kanban column map:**

| Session `mode` value | Column | Rationale |
|----------------------|--------|-----------|
| `READ` | `research` | Read-only sessions are information-gathering; no impl lock held |
| `SPEC` | `spec` | SPEC mode = authoring/reviewing specs (column displayed as "Definition" in the UI) |
| `BOUND_IMPLEMENTATION` | `implementation` | Holds impl lock; direct mapping |
| `BOUND_REVIEW` | `review` | New mode from R2 amendment; direct mapping |
| Unknown / unrecognised | `research` | Fail-safe: unknown modes go to Research, not dropped |

**Note:** Kanban shows bound sessions only. Unbound agents (no session file) do not appear
on the board. There is no "pre-bind" session state written to `.dadaia/sessions/` before
`eval $(dadaia context bind ...)` runs.

**Graceful empty:** if `.dadaia/sessions/` does not exist, return `200` with
`{"generated_at": "...", "swimlanes": []}`. Never 500 on missing directory.

**POST → 405.** The endpoint is GET only. `_RAW_ROUTES` adds `(r"^/api/kanban$", "api_kanban")`;
`api_kanban` is added to `_BEARER_AUTH_ROUTE_NAMES` / `_BEARER_ONLY_ROUTES`.

**Auth:** subject to the loopback bypass delivered by `panel-ux-fix-v1` T-PUX-06. On a
127.0.0.1 bind the endpoint is accessible without a token; on a non-loopback bind the
existing Bearer wall applies. Consistent with all other `/api/*` routes.

**Malformed session files** (unparseable JSON, missing required fields) are silently
skipped; the valid sessions proceed normally.

**Affected files:**

| File | Change |
|------|--------|
| `dadaia_workspace/features/panel/handler.py` | Add `/api/kanban` route; add to `_BEARER_ONLY_ROUTES`; update `_NOT_FOUND_BODY` |
| `dadaia_workspace/features/panel/views/kanban.py` (new) | New view: reads `.dadaia/sessions/*.json`, groups by context + mode, returns JSON |

---

### K-2 — Kanban frontend (new tab + JS + CSS)

**New files:**

| File | Purpose |
|------|---------|
| `dadaia_workspace/features/panel/views/kanban.py` (owned/created by K-1 — NOT created here) | K-2 only contributes the Kanban tab HTML markup that K-1's view serves; the `kanban.py` file itself is authored and owned by K-1 (software-engineer-python). Ownership clarified 2026-05-30 per grill-me resolution of SPEC issue #3. |
| `dadaia_workspace/features/panel/views/assets/js/kanban.js` (new) | Kanban tab JS: fetches `/api/kanban`, renders swimlanes, polls for updates |
| `dadaia_workspace/features/panel/views/assets/css/kanban.css` (new) | Kanban-specific CSS tokens and layout |
| `dadaia_workspace/features/panel/views/index.py` | Add Kanban tab to nav (`#tab-kanban`) and tab panels |
| `dadaia_workspace/features/panel/handler.py` | Route for Kanban HTML tab (already covered by K-1 for the API route) |

**Layout:** swimlane-per-context × 4-column grid. Board is horizontally scrollable below
800px. Desktop (≥1280px): all 4 columns visible side by side. Column min-width:
`--kanban-col-min-w: 200px`.

**Card anatomy (per design spec):**

```
+--------------------------------------------------+
| SESSION ID                      STATUS DOT       |
| --font-mono 0.8rem medium       --color-active-dot |
+--------------------------------------------------+
| [model name]                                     |
| --font-stack 0.78rem regular --color-muted       |
+--------------------------------------------------+
| [runtime]  ·  [age]                              |
| --font-stack 0.72rem regular --color-muted       |
+--------------------------------------------------+
  aria-label: "Session [id], [model], [runtime], [age], [status]"
  role: article
  tabindex: 0
```

**Per-column concurrency hints (header badges):**

| Column | Badge |
|--------|-------|
| Research | (none) |
| Definition | `≤2` |
| Implementation | `×1` |
| Review | `×1` |

Badge style: `--color-placeholder-bg` background, `--color-muted` text, `--font-size-xs`,
`--radius-pill`.

**Implementation ⊕ Review mutual-exclusion visual (per design spec decision):**
When a swimlane has a card in `review` column, the `implementation` column in that same
lane is dimmed (opacity: `--opacity-kanban-locked: 0.40`) and a lock badge (U+1F512 or SVG)
appears on its header. Vice versa when `implementation` is active. Both columns are shown;
the locked one has `data-locked="true"` attribute and CSS class `kanban-column--locked`.
Aria supplement on locked header: `"[Phase] column, locked — context is in [other phase]"`.
Transitions governed by `--duration-fast: 120ms` / `--easing-standard`; suppressed under
`@media (prefers-reduced-motion: reduce)`.

**Empty states:**
- Empty column within a lane: dashed-border placeholder, height `--kanban-card-min-h: 72px`,
  `aria-hidden="true"` (`data-testid="kanban-empty-placeholder"`).
- Empty lane (context with no sessions): visible text "No active sessions" in
  `--color-muted` italic (announced by screen readers).
- Empty board (no contexts): centred message "No Spec Context Projects available".

**Design tokens (new — to be added in `tokens.py`):**

```css
--color-kanban-separator:      #888888;   /* 3.54:1 on --color-bg #fafafa — WCAG 1.4.11 pass */
--color-kanban-lane-header-bg: var(--color-primary-bg);
--color-kanban-locked-overlay: var(--color-bg);   /* applied at 60% alpha via CSS */
--opacity-kanban-locked:       0.40;
--kanban-col-min-w:            200px;
--kanban-card-min-h:           72px;
--kanban-card-gap:             var(--space-sm);
--kanban-lane-gap:             var(--space-xs);
```

**WCAG AA compliance (per design-spec audit):**
- Card title text: `--color-heading: #111` on white → 18.5:1. Pass.
- Card meta text: `--color-muted: #666` on white → 5.52:1. Pass.
- Swimlane separator: `--color-kanban-separator: #888` on `--color-bg: #fafafa` → 3.54:1. Pass (1.4.11 non-text).
- Lock icon supplement prevents sole reliance on colour to convey locked state. Pass (1.4.1).
- Card `role="article"` + `tabindex="0"` for keyboard traversal. Pass (2.1.1).
- Each lane: `<section aria-labelledby="lane-[slug]-heading">`. Each column:
  `<div role="group" aria-labelledby="col-[phase]-[slug]-heading">`. Pass (1.3.1).

**Card appears animation:** `opacity: 0 → 1`, `--duration-normal: 220ms`,
`--easing-decelerate`. Suppressed under `prefers-reduced-motion`.

---

### K-3 — Handoff-v1.1 schema: `verdict` field

Add a `verdict: "APPROVED" | "REJECTED"` top-level optional field to the handoff schema
at `dadaia_workspace/public/schemas/handoff-v1.schema.json`. This enables the
dual-approval gate (qa-engineer AND security-reviewer) to be machine-checked via
`jq '.verdict'` on each handoff sidecar. One schema task; no new release required
(per QA strategy Part 3 recommendation).

Gate check (CI or product-engineer at CLOSURE):

```bash
jq '.verdict' <qa-handoff.json>       # must equal "APPROVED"
jq '.verdict' <security-handoff.json> # must equal "APPROVED"
```

If either is `"REJECTED"`: findings route back to the implementer; release stays in
REVIEW phase.

`verdict_reason` (string, optional) — human-readable summary of the verdict.

This is additive: existing handoff consumers that do not read `verdict` are unaffected.

**Affected file:** `dadaia_workspace/public/schemas/handoff-v1.schema.json` (canonical
source; confirmed path 2026-05-30). After editing, run `dadaia public stage && dadaia public
install --target all` to propagate to the staged copy at `.dadaia/agentic/schemas/`.

---

## 4. Architecture deltas

All changes are confined to `repos/dadaia-workspace/dadaia_workspace/`.

| Layer | What changes |
|-------|-------------|
| `features/panel/handler.py` | Add `/api/kanban` GET route; add to `_BEARER_ONLY_ROUTES`; update `_NOT_FOUND_BODY` |
| `features/panel/views/kanban.py` (new) | Reads `.dadaia/sessions/*.json`; groups by context + mode; returns JSON for API; serves Kanban tab HTML |
| `features/panel/views/assets/js/kanban.js` (new) | Fetches `/api/kanban`, renders board, handles XOR lock visual, polls for updates |
| `features/panel/views/assets/css/kanban.css` (new) | Kanban layout, card styles, token overrides |
| `features/panel/views/index.py` | Add Kanban nav entry (`#tab-kanban`) and section |
| `public/schemas/handoff-v1.schema.json` | Add optional `verdict` field (additive, non-breaking); then `dadaia public stage && install --target all` |
| `public/templates/` | No change (memory templates not touched) |

**No changes to:**
- The telemetry DAO (`TelemetryDao`, `TelemetryAggregator`) — Kanban reads session files only
- `sdd-spec-gate.sh` — no gate change in this release
- `spec_contexts.json` state model — that is R2's domain

---

## 5. Tech-stack deltas

No new PyPI dependencies. All implementation in Python (backend view) + vanilla JS (frontend)
+ CSS (layout tokens). Same stack as the existing panel.

---

## 6. Security and operations deltas

- Auth: `/api/kanban` is a Bearer-required route on non-loopback binds. On loopback binds,
  it benefits from the bypass introduced in `panel-ux-fix-v1` T-PUX-06 (no separate work
  needed here).
- No sensitive data exposed: session files contain session ID, mode, runtime, PID, timestamps.
  No credentials, no code, no user data.

---

## 7. Memory files affected at CLOSURE

- `specs/memory/product/index.html` — add the Kanban tab as a panel feature entry in the catalog.
- `specs/memory/product/<panel-slug>.html` — update panel feature description to include Kanban tab
  and handoff-v1.1 verdict field.
- `specs/memory/architecture.html` — note new `views/kanban.py` in the panel layer.
- `specs/memory/tech-stack.html` — no change expected (no new dependencies).

---

## 8. Acceptance criteria

### AC-1 — /api/kanban contract (from QA strategy Part 2 §2.1)

| # | Test name | Expected |
|---|-----------|----------|
| AC-1.1 | `test_kanban_schema_all_four_columns_present` | Response has `research`, `spec`, `implementation`, `review` keys; each is a list |
| AC-1.2 | `test_kanban_read_mode_lands_in_research_column` | `mode:"READ"` session → card in `research` |
| AC-1.3 | `test_kanban_spec_mode_lands_in_spec_column` | `mode:"SPEC"` session → card in `spec` |
| AC-1.4 | `test_kanban_bound_implementation_lands_in_implementation_column` | `mode:"BOUND_IMPLEMENTATION"` → card in `implementation` |
| AC-1.5 | `test_kanban_bound_review_lands_in_review_column` | `mode:"BOUND_REVIEW"` → card in `review` |
| AC-1.6 | `test_kanban_missing_sessions_dir_returns_200_empty` | No `.dadaia/sessions/` → 200, all columns empty lists |
| AC-1.7 | `test_kanban_empty_sessions_dir_returns_200_empty` | Dir exists, no JSON files → 200, all columns empty |
| AC-1.8 | `test_kanban_stale_session_flagged_is_stale_true` | `last_seen_at` 10 min ago, `ttl_seconds=180` → `is_stale:true` |
| AC-1.9 | `test_kanban_fresh_session_flagged_is_stale_false` | 30 s ago, `ttl_seconds=300` → `is_stale:false` |
| AC-1.10 | `test_kanban_unknown_mode_excluded_or_surfaced` | Unknown mode → graceful (no 500); card in `research` or excluded |
| AC-1.11 | `test_kanban_post_not_allowed` | POST `/api/kanban` → 405 |
| AC-1.12 | `test_kanban_malformed_session_file_skipped` | Corrupt JSON file silently skipped; valid session appears |
| AC-1.13 | `test_kanban_requires_auth_non_loopback` | `loopback_bypass=False`, no token → 401 |
| AC-1.14 | `test_kanban_no_auth_required_loopback_bind` | `loopback_bypass=True` → 200 without Authorization header |

### AC-2 — Playwright board scenarios (from QA strategy Part 2 §2.2)

| # | Scenario | Expected |
|---|----------|----------|
| AC-2.1 (PW-KAN-01) | 2 sessions for different contexts, both BOUND_IMPLEMENTATION | Board has 4 columns (Research, Spec/Definition, Implementation, Review); Impl column has 2 cards from 2 distinct `data-context` values |
| AC-2.2 (PW-KAN-02) | 4 sessions, one per mode (READ, SPEC, BOUND_IMPLEMENTATION, BOUND_REVIEW) | Each column has exactly 1 card; card session IDs match fixture |
| AC-2.3 (PW-KAN-03) | Context has BOUND_IMPLEMENTATION session | Review column has `data-locked="true"` + CSS `kanban-column--locked`; 0 review cards for that context |
| AC-2.4 (PW-KAN-04) | No session files (missing dir) | All 4 columns visible; each has `data-testid="kanban-empty-placeholder"` visible |
| AC-2.5 (PW-KAN-05) | One stale session file | Card has `data-stale="true"` attribute |

All Playwright tests use deterministic `waitForSelector` — no `time.sleep` / `waitForTimeout`.
Evidence folder: `.dadaia/tmp/qa-engineer/panel-kanban-v1/`.

### AC-3 — Impl-XOR-Review race tests (from QA strategy Part 2 §2.3)

| # | Test name | Expected |
|---|-----------|----------|
| AC-3.1 | `test_impl_held_blocks_review_bind` | `ReviewBlockedByImplementationError` raised |
| AC-3.2 | `test_review_held_blocks_impl_bind` | `ImplementationBlockedByReviewError` raised |
| AC-3.3 | `test_impl_and_review_different_releases_coexist` | Bind succeeds (different release = no conflict) |
| AC-3.4 | `test_impl_released_allows_review_bind` | BOUND_REVIEW succeeds after `release_lock()` |
| AC-3.5 | `test_impl_stale_blocks_review_until_reclaim` | Stale impl lock still blocks; reclaim required |
| AC-3.6 | `test_two_impl_binds_same_release_raises` | `LockHeldError` on second BOUND_IMPLEMENTATION |

Race tests (barrier-based, no `time.sleep`):

| # | Test name | Expected |
|---|-----------|----------|
| AC-3.7 | `test_r_impl_xor_review_only_one_binds` | `threading.Barrier(2)`: exactly 1 success, 1 failure (MutualExclusionError); lock file has winner as owner |
| AC-3.8 | `test_r_two_impl_sessions_race` | `threading.Barrier(2)`: exactly 1 success (LockHeldError for second) |

All race tests use real `JsonContextStore` on `tmp_path` (no `FakeContextStore`).
CI grep gate (inherited from `spec-context-session-locks-v1` AC-RACE-2):
`grep -rn "time\.sleep" tests/ | grep -v "# allowed-sleep"` — must exit non-zero.

### AC-4 — Verdict field (handoff-v1.1)

| # | Criterion |
|---|-----------|
| AC-4.1 | `handoff-v1.schema.json` accepts a top-level optional `verdict` field with values `"APPROVED"` or `"REJECTED"` |
| AC-4.2 | Existing handoff sidecars without `verdict` continue to validate (field is optional, additive) |
| AC-4.3 | `dadaia reports validate <path>` exits 0 on a v1.1 sidecar with `verdict: "APPROVED"` |

---

## 9. Out of scope

- **Unbind / session-termination action** — deferred to a Kanban v2. Operator chose read-only v1.
- **Per-card click action / detail drawer** — not in v1; board is display-only.
- **Drag / manual reorder** — v1 is autonomous; cards move only as session mode changes.
- **Cost tracking on the board** — telemetry data is intentionally excluded from the Kanban data source.
- **Mobile stacked column layout** — horizontal scroll is acceptable for v1 (panel is a desktop tool).
- **SPEC-mode session file creation** — R2 defines how session files are written; Kanban only reads them.
- **Dual-approval CI integration** — the `verdict` gate logic lives in `panel-kanban-v1`; the CI YAML
  wiring is a `devops-engineer` task (added to TASKS.md).

---

## 10. Dependencies and sequencing

### 10.1 Release dependencies

- **`spec-context-session-locks-v1` (R2) must close before IMPLEMENTATION starts.**
  The Kanban backend reads `.dadaia/sessions/*.json`. These files only exist after R2 ships.
  SPEC is authored now (unblocked); PLAN and TASKS drafting may begin now;
  no code may be merged until R2 ACTIVE.md phase = ARCHIVED.
- **`panel-ux-fix-v1` must land (or its T-PUX-06 task must be complete) before the Kanban
  `/api/kanban` endpoint ships** — the loopback bypass is a dependency for correct auth behaviour
  on the new endpoint.
- **`spec-context-session-locks-v1` R2 SPEC amendment (BOUND_REVIEW mode) must be accepted**
  before K-1's review column has data. The amendment is authored in the same spec-authoring
  batch as this SPEC (Job C). **ACCEPTED by operator via grill-me 2026-05-30** — this
  dependency is satisfied; R3's Review column is greenlit.

### 10.2 Concurrency note

This release is disjoint from `go-open-source` (public-facing lib hardening; no panel code).
Panel frontend files do not overlap with any spec-context service files. Write sets are
fully disjoint.

### 10.3 Internal task ordering (hard)

```
K-1 (API endpoint + view, backend)
  ↓
K-2 (Kanban JS + CSS + nav injection)   ← frontend-engineer; may start in parallel with K-1 once API contract is stable
  ↓
K-3 (handoff-v1.1 schema: verdict field)  ← software-engineer-python; disjoint; can run in parallel with K-1/K-2
```

---

## 11. Implementer breakdown

| Work area | Implementer |
|-----------|-------------|
| K-1 `/api/kanban` backend (kanban.py view, handler route) | `software-engineer-python` |
| K-2 Kanban frontend (kanban.js, kanban.css, index.py nav) | `frontend-engineer` |
| K-3 handoff-v1.1 schema `verdict` field | `software-engineer-python` |
| `/api/kanban` contract tests (integration) | `software-engineer-python` |
| Impl-XOR-Review race tests (unit + concurrency) | `software-engineer-python` |
| Playwright board scenarios (PW-KAN-01..05) | `frontend-engineer` (wires); `qa-engineer` (defines) |
| Dual-approval gate CI check | `devops-engineer` |

---

## 12. Open questions

None — all design decisions are locked by the three specialist reports consumed for this
SPEC. The architect ADR (decision C), design spec (section B), and QA strategy (Parts 2
and 3) provide full implementation guidance without ambiguity.

---

*Product Engineer — dadaia-workspace | 2026-05-30*
