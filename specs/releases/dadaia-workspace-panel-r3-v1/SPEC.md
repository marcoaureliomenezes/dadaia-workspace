# Spec: Release — dadaia-workspace-panel-r3-v1

> **Status:** Aprovado
> **Approved:** 2026-05-17
> **Approved-by:** operator
> **Release ID:** dadaia-workspace-panel-r3-v1
> **Owner:** product-engineer
> **Created:** 2026-05-19
> **Phase:** PLAN (post-approval)
> **Pipeline (3-phase):** PE INTAKE → 4× Phase-2 specialist reports (architect, software-engineer, frontend-engineer, qa-engineer) → PE SYNTHESIS → 4× APPROVE WITH NOTES reviews → this SPEC
> **Discovery inputs:**
> - PE INTAKE: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-18T010046Z-panel-r3-overhaul-intake.html`
> - Architect (design): `.dadaia/reports/dadaia-workspace/software-architect/2026-05-18T010801Z-panel-r3-architecture.html`
> - Software-engineer (implementation plan): `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-18T030000Z-panel-r3-implementation-plan.html`
> - Frontend-engineer (design): `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-18T120000Z-panel-r3-design.html`
> - QA (test plan): `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-18T150000Z-panel-r3-test-plan.html`
> - PE SYNTHESIS: `.dadaia/reports/dadaia-workspace/product-engineer/2026-05-19T000000Z-panel-r3-overhaul-synthesis.html`
> - Architect review: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-19T010000Z-panel-r3-synthesis-review.html`
> - SE review: `.dadaia/reports/dadaia-workspace/software-engineer/2026-05-19T060000Z-panel-r3-synthesis-review.html`
> - FE review: `.dadaia/reports/dadaia-workspace/frontend-engineer/2026-05-19T010000Z-panel-r3-synthesis-review.html`
> - QA review: `.dadaia/reports/dadaia-workspace/qa-engineer/2026-05-19T120000Z-panel-r3-synthesis-review.html`

---

## 1. Objective

Turn the panel from a "memory browser with a placeholder tab" into a real **control
surface** for the operator's canonical agent catalog and workflow catalog, with at-a-glance
metrics, server-rendered DAG visualization, and a personally tunable colour palette. R3
preserves the panel's read-only, single-process, localhost-bound posture; it ships the
spine the operator described as **"workflows are serious"** and validates that the panel
is **"very well designed"** rather than a placeholder.

---

## 2. Operator demand (verbatim, preserve voice)

The voice below is the canonical anchor for R3 acceptance. All UI and API decisions
trace back to these quotes; deviations require a documented drift in CLOSURE.md.

> "I want to look at the panel and see, at a glance, which agents I have, what they do,
> when I last used them, and how much they have cost me. That is what a **control
> surface** looks like."

> "**Workflows are serious.** They are how the agents cooperate. I cannot have them
> shown as a flat list of skills with no diagram. I need to see the order, the
> parallelism, the gates."

> "The panel must look like it was **very well designed**. Not a placeholder. A real
> piece of software."

> "Stop calling it Memories. Spec Context Projects is the real name."

These four quotes correspond directly to: the Agents tab redesign, the Workflows tab
rebuild + DAG, the theme switcher (and the asset split that makes parallel UI work
feasible), and the tab rename + reorder. They are the four product deltas.

---

## 3. Product deltas (atomic — only what changes in this release)

| Delta | Surface | One-paragraph description |
|---|---|---|
| **D1 — Tab rename + reorder** | Top-level scaffold | The "Memories" tab is renamed to "Spec Context Projects". Tab order becomes (Spec Context Projects → Agents → Workflows → Servers). Default-active tab becomes Spec Context Projects. Internal IDs stay (`section-memories`, `tab-memories`, etc.) so `#memories` hash links and DOM selectors keep working. |
| **D2 — Agents tab redesign** | Agents tab | The placeholder Agents view is replaced by a 10-card grid sourced from the canonical agent catalog at `.dadaia/agentic/agents/`. Each card overlays telemetry metrics (sessions, cost, last activity). Cards expand inline (accordion, multi-open allowed) to reveal skills, cost-by-context bars, and the agent's system prompt, lazily fetched on first expand. |
| **D3 — Workflows tab rebuild** | Workflows tab | The 2-pane skills viewer is replaced by a card grid sourced from `.dadaia/agentic/workflows/` (canonical workflow markdown files). Each card shows stage count, gates, parallel groups, and a "View DAG →" CTA. Clicking the CTA hash-routes (`#workflows?detail=<name>`) to an in-section detail view showing the full stage list, agent chips, inputs, and a server-rendered DAG SVG (longest-path layered layout). |
| **D4 — Theme switcher** | Topbar | A theme button ships with 3 light-mode palettes (Mint default, Sage, Warm), persisted in `localStorage["dadaia-panel-theme"]` and applied pre-paint via an inline `<script>` in `<head>`. Warm theme carries a mandatory WCAG-compliant double focus outline rule. The iframe `wrapper.py` adopts root tokens so memory-iframe back-bars follow the theme. |

The asset split (`views/_assets.py` → `views/assets/css/*` + `views/assets/js/*`, served
via `/static/<name>`) is the foundation that lands first and makes parallel work on D2,
D3, D4 feasible. It is not a product delta — it is an architectural delta that the
operator does not see, but without which the three UI deltas cannot be developed in
parallel without merge conflict pain.

---

## 4. Architecture deltas

| Module | Status | Purpose |
|---|---|---|
| `dadaia_workspace/features/agents/` | NEW | Canonical agent catalog reader. Reads `.dadaia/agentic/agents/*.md`, parses frontmatter via pyyaml, exposes `AgentDTO`. |
| `dadaia_workspace/infrastructure/markdown_agent_store.py` | NEW | Filesystem adapter consumed by `features/agents/`. Allowlists frontmatter fields. |
| `dadaia_workspace/features/workflows/` | NEW | `WorkflowsService` wrapping the existing `MarkdownWorkflowStore` (not a parallel parser). Adds DTO layer + DAG layout call. Per-process in-memory cache keyed by `(path, mtime, size)`. |
| `dadaia_workspace/features/workflows/dag.py` | NEW | Longest-path layered layout + SVG serialisation. Stdlib only. Rounded-rect nodes (140×40), parallel-group dashed bands, gate ⊙ marker, edge arrow polygons, `role="img"` + per-node `aria-label`. |
| `dadaia_workspace/features/panel/views/assets/` | NEW | Replaces the 1076-line `_assets.py` god module. Structure: `css/{tokens.py, structure.py, agents.py, workflows.py}` + `js/{core.js, themes.js, agents.js, workflows.js}`. |
| `dadaia_workspace/features/panel/views/static.py` | ACTIVATED | Existing dead route activated; serves files from `views/assets/` with a frozen Content-Type table (see §6) and `Cache-Control: no-cache`. |
| `infrastructure/markdown_workflow_store.py` | RE-READ + WRAP | SE must re-read this module before implementation. If it lacks `get_by_name`, `expected_output_path`, or `must_include` flow-through, a pre-implementation task adds those gaps. (SE review note absorbed.) |
| SQLite `workflows` + `workflow_agents` tables | DEAD | NOT touched in R3. SE adds one-line comment in `schema.py` next to each table definition with the literal text `# DEAD: replaced by canonical workflow reader in panel-r3; do not extend; see backlog/candidates.md`. Migration to drop them is filed in `backlog/candidates.md`. |
| `features/panel/views/wrapper.py` | FIX | Replace hard-coded `#7ec8e3` and other palette literals with `var(--color-*)` token references so the back-bar follows the active theme. |
| `features/panel/service.py` | SHRINK | Remove dead `list_unregistered_listeners()` method and the `"unregistered": []` field from `/api/servers` payload (no consumer in R3 UI). |
| `features/telemetry/reader/workflows.py` | DELETE | Workflow ingestion path replaced by canonical reader; SQLite `workflows`/`workflow_agents` no longer populated. |

**Layer-rule check:** `features/workflows/service.py` calls into
`infrastructure/markdown_workflow_store.MarkdownWorkflowStore` — same direction as
existing `features/*` → `infrastructure/*` calls. No reverse dependency introduced.
`features/agents/` mirrors that pattern via `infrastructure/markdown_agent_store.py`.

---

## 5. API contracts (locked)

All endpoints below are normative for R3. Status codes: ✱ new, △ changed, ▽ shrunk,
○ unchanged.

| Method | Path | Auth | Status | Notes |
|---|---|---|---|---|
| GET | `/` | none | △ | Tab order = (Spec Context Projects, Agents, Workflows, Servers); default-active = Spec Context Projects; theme switcher in topbar. |
| GET | `/api/servers` | none | ▽ | Existing payload **minus** `unregistered` field. |
| GET | `/api/contexts` | none | ○ | Unchanged. |
| GET | `/api/agents` | Bearer | △ | Optional `?active_window_days=N` query (default 30, range 1–365). See §5.1. |
| GET | `/api/agents/<id>/sessions` | Bearer | ○ | Unchanged. |
| GET | `/api/agents/<id>/prompt` | Bearer | ✱ | Path-traversal-guarded. See §5.2. |
| GET | `/api/workflows` | Bearer | △ | Card summaries only — **no `diagram_svg`** in this response. See §5.3. |
| GET | `/api/workflows/<name>` | Bearer | ✱ | Detail endpoint with full `stages[]` + `diagram_svg`. Path-traversal-guarded. See §5.4. |
| GET | `/memory/<slug>/<path>` | none | ○ | Unchanged. |
| GET | `/memory-view/<slug>/<path>` | none | △ | Internal `wrapper.py` change only: now consumes PANEL_CSS root tokens so the theme follows. |
| GET | `/static/<name>` | none | △ | Existing route ACTIVATED. Serves files from `views/assets/` with the frozen Content-Type table from §6. |

**Endpoint count after R3: 11 total — 2 new, 4 changed, 1 shrunk, 4 unchanged.**

### 5.1 `GET /api/agents` — response shape (normative)

The agent telemetry fields are **nested under a `telemetry` sub-object** — they are
NOT top-level. This decision is normative for R3 (resolves SE review §2.1). The
frontend reads `agent.telemetry.session_count`, not `agent.session_count`.

```json
{
  "generated_at": "ISO-8601",
  "status_window_days": 30,
  "window_days": 180,
  "pricing_age_days": 12,
  "pricing_model_date": "2026-05-01",
  "agents": [
    {
      "agent_id": "frontend-engineer",
      "display_name": "frontend-engineer",
      "description": "...",
      "status": "active" | "inactive",
      "skills": ["..."],
      "tools": ["..."],
      "model": "claude-sonnet-4-6",
      "opencode_model": null,
      "max_turns": 60,
      "input_contract": { "...": "..." } | null,
      "telemetry": {
        "session_count": 24,
        "total_cost_usd": 1.84,
        "total_cost_30d_usd": 0.42,
        "cost_known": true,
        "last_activity_at": "2026-05-17T...",
        "providers": ["claude"],
        "dominant_model": "claude-sonnet-4-6",
        "is_subagent": false,
        "suspect_count": 0,
        "token_totals": { "input": 0, "cache_creation": 0, "cache_read": 0, "output": 0 },
        "context_breakdown": [],
        "recent_sessions": []
      }
    }
  ]
}
```

- Returns **exactly 10 entries** (canonical catalog only — telemetry-only rows for
  unrecognized agent names are silently dropped).
- `status` = `"active"` if `last_activity_at IS NOT NULL AND last_activity_at >= now -
  status_window_days days`; else `"inactive"` (including never invoked).
- `window_days` is the pre-existing telemetry aggregation window (180); `status_window_days`
  is the new active/inactive threshold (default 30). Both are reported.
- `system_prompt` is **NOT** in the list response — it lives on `/api/agents/<id>/prompt`.

### 5.2 `GET /api/agents/<id>/prompt` — response shape (normative)

Path validation: `id` must match `^[a-z0-9](?:[a-z0-9_-]{0,63}[a-z0-9])?$`. **In addition**,
the reader resolves the candidate path and asserts
`Path(resolved).resolve().is_relative_to(base_dir.resolve())` before opening (defence-in-depth
against symlink escapes — architect review note absorbed).

```json
{
  "agent_id": "frontend-engineer",
  "system_prompt": "<raw body, plain text>",
  "source_path": ".dadaia/agentic/agents/frontend-engineer.md"
}
```

- 404 if agent file does not exist.
- 400 if `id` fails the regex OR the resolved path escapes `base_dir`.

### 5.3 `GET /api/workflows` — response shape (normative)

Card-summary fields only. **No `diagram_svg`, no `stages[]`** in this response.

```json
{
  "generated_at": "ISO-8601",
  "source_hint": ".dadaia/agentic/workflows/",
  "workflows": [
    {
      "name": "cross-cutting-feature",
      "display_name": "cross-cutting-feature",
      "description": "...",
      "version": "0.1.0",
      "schema_version": "1",
      "stage_count": 7,
      "agent_ids": ["product-engineer", "software-architect"],
      "has_parallel": true,
      "has_gates": true,
      "source_path": ".dadaia/agentic/workflows/cross-cutting-feature.workflow.md"
    }
  ]
}
```

- Returns 12 entries today (1 per workflow file in `.dadaia/agentic/workflows/`).
- `stage_count` is an **integer**, not the `stages` array (QA review correction
  absorbed).

### 5.4 `GET /api/workflows/<name>` — response shape (normative)

Path validation: same regex as §5.2 plus the same `Path.resolve().is_relative_to(base)`
defence-in-depth check.

```json
{
  "name": "cross-cutting-feature",
  "description": "...",
  "version": "0.1.0",
  "schema_version": "1",
  "inputs": [{ "name": "context", "type": "string", "required": true }],
  "stages": [
    {
      "id": "discovery",
      "agent": "product-engineer",
      "needs": [],
      "parallel_group": null,
      "gate": null,
      "expected_output_path": "...",
      "must_include": ["..."],
      "on_failure": "stop"
    }
  ],
  "diagram_svg": "<svg ... role=\"img\" ...>...</svg>",
  "source_path": ".dadaia/agentic/workflows/cross-cutting-feature.workflow.md"
}
```

- 404 if workflow file not found.
- 400 if `name` fails the regex OR the resolved path escapes `base_dir`.
- `diagram_svg` is HTML-escaped at every stage-id / agent-name embedding point.

### 5.5 Auth + security invariants

- Bearer required on every `/api/*` route except `/api/servers` and `/api/contexts`
  (back-compat v1).
- Constant-time token comparison (existing `auth.py`) preserved.
- CSP unchanged in R3: still `'unsafe-inline'` on `script-src` (asset split enables
  dropping it; that work is deferred to the **first hotfix release after R3** —
  see §9).
- No CDN imports, no Mermaid library, no client-side DAG layout — server renders the SVG.

### 5.6 WorkflowsService cache (normative)

- **Scope:** per-process in-memory dict keyed by `(path, mtime, size)`.
- **Eviction:** bounded implicitly by file count in source directory (12 today, ≤50
  realistic ceiling); no LRU needed.
- **No cross-process invalidation** because the panel is a single-process
  `ThreadingHTTPServer`.
- One inline comment in the service code: "cache size bounded by file count in source
  dir; ETag header is P2 follow-up."

---

## 6. Static asset Content-Type + cache table (locked)

The `/static/<name>` route MUST serve content with a strict extension-to-MIME map
(architect review §6.1 absorbed). Unknown extensions return 404.

| Extension | Content-Type | Cache-Control |
|---|---|---|
| `.css` | `text/css; charset=utf-8` | `no-cache` |
| `.js`  | `application/javascript; charset=utf-8` | `no-cache` |
| `.svg` | `image/svg+xml; charset=utf-8` | `no-cache` |
| `.map` | `application/json; charset=utf-8` | `no-cache` |
| (other) | — | route returns 404 |

`no-cache` is the R3 default because filenames are unversioned. A future hotfix that
adopts hash-named filenames can opt into `public, max-age=31536000, immutable` for
fingerprinted assets.

Unit test in `tests/features/panel/views/test_static.py` asserts the Content-Type for
each supported extension. E2E-TAB-05 carries the runtime smoke.

---

## 7. UI contracts (locked)

### 7.1 Hash navigation grammar (normative)

```
#<tab-section-id>[?key=val&...]
```

Defined patterns:
- `#memories`, `#agents`, `#workflows`, `#servers` — bare tab activation.
- `#workflows?detail=<workflow-name>` — workflow detail view in-section.
- `#agents?filter=<agent-name>` — agent filter (existing pattern; coexists).

The hash router in `core.js` parses both. All patterns must coexist without
collision; the JS module-level comment documents the grammar verbatim.

### 7.2 Top-level scaffold

- Topbar: rhino logo + wordmark `dadaia·workspace | panel`; primary-context badge;
  **theme switcher button** to the right of the badge.
- Tab bar order: **Spec Context Projects | Agents | Workflows | Servers**.
  Default-active: Spec Context Projects.
- Internal IDs unchanged: `section-memories`, `section-agents`, `section-workflows`,
  `section-servers`; `tab-memories`, etc.
- Responsive: visible label "Spec Context Projects" abbreviates to "Spec Contexts" at
  `<768px`; `aria-label` keeps the full string.

### 7.3 Spec Context Projects tab

Behaviour unchanged except for the visible label and the new default-active state.
Existing card-per-context layout retained.

### 7.4 Agents tab

- Grid of **exactly 10 agent cards** (canonical only). 2-column at ≥1024px; 1-column
  below.
- **Collapsed card:** status badge (ACTIVE/INACTIVE), agent name, description (2-line
  clamp), 3-stat row (Sessions, Cost, Last seen), skills chip row (first 2 + "+N
  more"), expand chevron.
- Card left-border 3px `--color-accent` for active agents; transparent for inactive.
- **Expanded card** (inline accordion, multi-open): full skills, cost-by-context bars,
  scrollable system prompt (lazy-loaded via `/api/agents/<id>/prompt`) with
  copy-to-clipboard button.
- **Loading state:** skeleton cards with `aria-busy="true"` on initial fetch; same
  `skeleton-pulse` keyframe disabled under `prefers-reduced-motion`.
- **Empty/zero-telemetry state:** card still renders with `Sessions=0`, `Cost=—`,
  `Last seen=Never`, status badge `INACTIVE`.
- **Error state:** 401 → explicit "Re-authenticate" instruction with the token URL
  format reminder.
- Accessibility: `aria-expanded` on chevron, `aria-controls` on detail; Enter/Space
  toggles; `prefers-reduced-motion` disables expand transition.

### 7.5 Workflows tab

- **Card grid.** 12 cards (1 per workflow file). 2-col at ≥768px; 1-col below.
- **Workflow card:** name, version pill, description (3-line clamp), agent chips,
  stats footer (`N stages · N gates · N parallel groups`), "View DAG →" CTA.
- **Detail view** (hash-routed, in-section): "← Back to Workflows" link, name,
  description, agent chips, DAG SVG, inputs section. SVG comes from
  `/api/workflows/<name>.diagram_svg`.
- **DAG visual:** rounded-rect nodes (140×40), parallel-group bands with dashed
  background, gate nodes annotated with ⊙ marker, edges with arrow polygons.
  `role="img"` + `<title>` + per-node `aria-label`.
- **Placeholder agents** (`{{var}}`): rendered with italic text + dashed border
  node style. Tooltip "agent resolved at runtime from workflow inputs".
- **DAG loading skeleton (normative — FE review note absorbed).** While the
  `/api/workflows/<name>` request is in flight, the detail view renders a skeleton
  containing 3 placeholder rounded-rects (140×40, gray, pulsing) in a horizontal
  row inside an `aria-busy="true"` container. The skeleton is NOT topology-accurate.
  The "← Back to Workflows" link is operative throughout loading. Pulse animation
  is disabled under `prefers-reduced-motion`. Error state: "Failed to load workflow
  detail." with a plain-text retry link.

### 7.6 Servers tab

- Moves to last in tab order. No internal changes (auto-refresh, grouping by repo).
- `/api/servers` drops `unregistered` field (frontend already does not render it).

### 7.7 Theme switcher

- Topbar button (icon + label "Theme"; icon only at <720px). Dropdown menu with 3
  options (Mint default, Sage, Warm).
- ARIA: button has `aria-haspopup="menu"`, `aria-expanded`; menu has `role="menu"`;
  items have `role="menuitemradio"` + `aria-checked`. Escape closes; focus returns to
  trigger.
- **Persistence:** `localStorage["dadaia-panel-theme"]`. Read pre-paint via inline
  `<script>` in `<head>` (no FOUC).
- **Warm theme focus ring (WCAG):** focus-visible includes secondary dark outline
  using `--color-accent-dark`. Locked by E2E-THM-07.
- `wrapper.py` inherits PANEL_CSS tokens so the iframe back-bar follows the theme.

---

## 8. Scope — IN vs DEFERRED

### 8.1 IN R3 (shipping)

- Tab rename + reorder (Memories → Spec Context Projects; new order).
- Agents tab redesign: canonical-catalog source + telemetry overlay; collapsed/expanded
  cards; lazy system-prompt fetch.
- Workflows tab rebuild: canonical-source reader (wrapping `MarkdownWorkflowStore`);
  card grid + hash-routed detail view; server-rendered DAG SVG via longest-path layout;
  DAG loading skeleton.
- New endpoints: `GET /api/agents/<id>/prompt`, `GET /api/workflows/<name>`.
- `?active_window_days=N` query on `/api/agents` (default 30, range 1–365).
- Theme switcher with 3 variants + localStorage persistence + WCAG focus ring rule
  for Warm; `wrapper.py` token consumption.
- `_assets.py` split into `views/assets/css/*` + `views/assets/js/*` served via
  `/static/<name>` with locked Content-Type table (§6).
- Removal of dead `unregistered` field on `/api/servers` and the dead
  `list_unregistered_listeners()` method.
- One-line `# DEAD:` comment in `schema.py` next to `workflows` and `workflow_agents`
  table definitions (literal text specified in §4).
- Deletion of `features/telemetry/reader/workflows.py`.
- Path-traversal regex guard PLUS `Path.resolve().is_relative_to(base)` defence-in-depth
  on `/api/agents/<id>/prompt` and `/api/workflows/<name>`.
- Test suites: ~38 unit + ~12 integration (SE) + 56 E2E (QA) with 21 visual evidence
  screenshots.
- CLOSURE of prerequisite releases (`v0.1.1` and `agent-monitoring-v1` if still in
  `specs/releases/`) — see §10.

### 8.2 DEFERRED (backlog)

| Item | Target | Destination |
|---|---|---|
| Drop SQLite `workflows` / `workflow_agents` tables (migration 6) | future cleanup release | `backlog/candidates.md` |
| "Run this workflow" invocation (Claude Code dispatcher integration) | future release | `backlog/candidates.md` |
| 4th theme variant ("brown-forward") | post-R3 PR | `backlog/ideas.md` |
| Dark mode (light-mode-only palette permutations in R3) | future release | `backlog/candidates.md` |
| Render `input_contract` in expanded agent card (data already exposed) | post-R3 | `backlog/ideas.md` |
| Manifest-drift banner (surface `dadaia public doctor` in panel) | post-R3 | `backlog/ideas.md` |
| **Drop `'unsafe-inline'` from script CSP** — explicit target: **first hotfix release after R3** (architect review §4 absorbed) | first hotfix post-R3 | `backlog/candidates.md` (P2, named target) |
| ETag header on detail endpoints | future perf release | `backlog/ideas.md` |
| Run-aware DAG state (highlight currently running stage) | future release | `backlog/ideas.md` |

---

## 9. Prerequisites

The synthesis (decision #24) requires both prerequisites below to be CLOSED and
archived **before** this release transitions to `phase: IMPLEMENTATION`. They do
not block writing SPEC/PLAN/TASKS; they block the implementation gate.

| Release | Current state (as of SPEC writing) | Action |
|---|---|---|
| `v0.1.1` | Active in `specs/releases/v0.1.1/`, phase IMPLEMENTATION, all T-DSR tasks `[x]` DONE per inspection | Write CLOSURE.md, render memory updates, `git mv` to `specs/_archive/releases/v0.1.1/`. |
| `agent-monitoring-v1` | Present in `specs/releases/agent-monitoring-v1/` | Verify task state; if all `[x]` DONE, write CLOSURE.md + memory updates + archive. If any task is open, finish it first. |

After both are archived, set `ACTIVE.md` to:

```
release: dadaia-workspace-panel-r3-v1
phase: SPEC
```

…and then transition to `PLAN`/`TASKS`/`IMPLEMENTATION` along the standard ladder
as each artifact reaches `**Status:** Aprovado`.

**This SPEC does not block on prerequisite completion.** It is written so that
implementation can begin the moment prerequisites resolve. The first PLAN.md task
(Phase 0) is exactly "resolve prerequisites".

---

## 10. Acceptance criteria (per surface, with E2E test IDs)

Each criterion is testable as written. Test IDs follow the QA test plan + QA review
updates (E2E total = **56**).

### Surface A — Tab rename + reorder

| # | Criterion | E2E tests |
|---|---|---|
| A1 | Visible tab labels in order are: "Spec Context Projects", "Agents", "Workflows", "Servers". | E2E-TAB-01 |
| A2 | Default-active tab on fresh load is "Spec Context Projects". | E2E-TAB-02 |
| A3 | Clicking each tab activates its section without reload. | E2E-TAB-03 |
| A4 | No CSP violations on initial load or any tab activation. | E2E-TAB-04 |
| A5 | Initial page load has no 4xx/5xx responses (including all `/static/*` assets). | E2E-TAB-05 |
| A6 | No CDN `<script>` tags in any served HTML. | E2E-TAB-06 |
| A7 | At `<768px`, label abbreviates to "Spec Contexts"; `aria-label` keeps full string. | covered under E2E-TAB-01 viewport variant |

### Surface B — Spec Context Projects tab (smoke)

| # | Criterion | E2E tests |
|---|---|---|
| B1 | The renamed tab renders the existing context-card layout unchanged. | E2E-SCP-01 |
| B2 | `#memories` hash still activates the tab (back-compat). | E2E-SCP-02 |

### Surface C — Agents tab

| # | Criterion | E2E tests |
|---|---|---|
| C1 | Exactly **10 agent cards** rendered (canonical-only). | E2E-AGT-01 |
| C2 | Each card has status badge, name, description, 3-stat row, skills chips, expand chevron. | E2E-AGT-02 |
| C3 | Zero-telemetry agent card shows graceful empty stats (`Never`, `—`, `0`) and `INACTIVE` badge. | E2E-AGT-03 |
| C4 | Expanding a card reveals skills, cost-by-context bars, and system prompt (lazy fetch). | E2E-AGT-04 |
| C5 | System prompt is non-empty and contains agent-specific content. | E2E-AGT-05 |
| C6 | Multiple cards can be expanded simultaneously (multi-open accordion). | E2E-AGT-06 |
| C7 | Collapsing restores the chevron state. | E2E-AGT-07 |
| C8 | Card expands via Enter key (keyboard accessibility). | E2E-AGT-08 |
| C9 | `/api/agents` response matches the §5.1 shape (10 entries, `telemetry` sub-object). | E2E-AGT-09 |
| C10 | `/api/agents` requires Bearer (401 without). | E2E-AGT-10 |
| C11 | axe-core audit passes on Agents tab. | E2E-AGT-11 |
| C12 | `?active_window_days=N` query is honoured; response includes matching `status_window_days` field. | **E2E-AGT-12 (new)** |

**Known coverage gap (QA review §9):** no E2E test asserts that telemetry rows for
unrecognized agent names are silently dropped. The canonical-only guarantee is covered
by C1 (exactly 10 cards). Verifying the silencing behaviour would require synthetic
telemetry rows and is integration-test territory. Accepted gap.

### Surface D — Workflows tab

| # | Criterion | E2E tests |
|---|---|---|
| D1 | Workflows tab shows exactly **12 workflow cards** (1 per file in `.dadaia/agentic/workflows/`). | E2E-WF-01 |
| D2 | Cards show real workflow names (e.g. "tdd-cycle", "cross-cutting-feature"), not skill names. | E2E-WF-02 |
| D3 | Each card has name, description, agent chips, and stats footer (`N stages · N gates · N parallel groups`). | E2E-WF-03 |
| D4 | Clicking "View DAG" on `tdd-cycle` opens the detail view, sets hash to `#workflows?detail=tdd-cycle`, **AND triggers a `GET /api/workflows/tdd-cycle` network request** (network observable). | **E2E-WF-04 (updated)** |
| D5 | tdd-cycle DAG renders with 5 nodes. | E2E-WF-05 |
| D6 | cross-cutting-feature DAG renders 7 nodes with the documented parallel groups and gates, without overlap. | E2E-WF-06 |
| D7 | spec-refinement DAG renders 7 nodes (5-node wide parallel group) without overlap. | E2E-WF-07 |
| D8 | **(a)** `GET /api/workflows` does NOT contain `diagram_svg`/`dag_svg` on any workflow entry. **(b)** `GET /api/workflows/tdd-cycle` does contain `diagram_svg` (non-empty, starts with `<svg`). | **E2E-WF-08 (two-part)** |
| D9 | No Mermaid library is loaded on the page. | E2E-WF-09 |
| D10 | "Back to Workflows" restores the grid; hash clears. | E2E-WF-10 |
| D11 | `/api/workflows` shape: 12 entries; `tdd-cycle` entry has `stage_count: 5` (integer) and does NOT have `stages` or `diagram_svg` keys. Companion: `/api/workflows/tdd-cycle` has `stages[]` with 5 elements. | **E2E-WF-11 (updated)** |
| D12 | `/api/workflows` requires Bearer (401 without). Companion: `/api/workflows/<name>` requires Bearer (401 without). | E2E-WF-12 (+ extension inside E2E-API-09) |
| D13 | axe-core audit passes on Workflows tab (both grid and detail view). | E2E-WF-13 |
| D14 | DAG SVG has `role="img"`, `<title>`, and per-node `aria-label`. | E2E-WF-14 |

### Surface E — Theme switcher

| # | Criterion | E2E tests |
|---|---|---|
| E1 | Theme switcher button visible in topbar. | E2E-THM-01 |
| E2 | Dropdown opens with 3 options (Mint, Sage, Warm). | E2E-THM-02 |
| E3 | Selecting "Sage" sets `data-theme="sage"` on root and updates visible tokens. | E2E-THM-03 |
| E4 | Selecting "Warm" sets `data-theme="warm"` and updates visible tokens. | E2E-THM-04 |
| E5 | Selection persists across reload (read from `localStorage["dadaia-panel-theme"]`). | E2E-THM-05 |
| E6 | No FOUC: `data-theme` attribute is set before first contentful paint. | E2E-THM-06 |
| E7 | Warm theme `focus-visible` rule produces a double outline (WCAG constraint). | E2E-THM-07 |
| E8 | Escape closes the dropdown; focus returns to the trigger. | E2E-THM-08 |
| E9 | axe-core audit passes on all 3 themes. | E2E-THM-09 |

### Surface F — Servers tab (smoke)

| # | Criterion | E2E tests |
|---|---|---|
| F1 | Servers tab still renders (auto-refresh, repo grouping intact); `/api/servers` payload does NOT contain the `unregistered` field. | E2E-SRV-01 |

### Surface G — API security (cross-cutting)

| # | Criterion | E2E tests |
|---|---|---|
| G1 | `/api/agents` shape validation. | E2E-API-01 |
| G2 | `/api/agents/<id>/prompt` returns plain text body inside JSON. | E2E-API-02 |
| G3 | `/api/agents/unknown-agent/prompt` returns 404. | E2E-API-03 |
| G4 | `/api/workflows` shape validation (12 entries, summary fields, no `stages[]`, no `diagram_svg`). | E2E-API-04 |
| G5 | `/api/workflows`: `tdd-cycle` has `stage_count: 5`. | E2E-API-05 |
| G6 | `/api/workflows/cross-cutting-feature` (detail): stage `red_test_frontend` has `needs=["contract_review"]` and `parallel_group="red_tests"`. | E2E-API-06 |
| G7 | **Split:** (a) `GET /api/workflows` 200 — no workflow entry contains `diagram_svg` or `dag_svg`. (b) `GET /api/workflows/tdd-cycle` 200 — root `diagram_svg` is non-empty and parses as valid XML. | **E2E-API-07 (split)** |
| G8 | `/api/agents` returns 401 without Bearer. | E2E-API-08 |
| G9 | `/api/workflows` returns 401 without Bearer. (Companion: `/api/workflows/<name>` also returns 401 without Bearer — extension assertion inside same test ID.) | E2E-API-09 |
| G10 | `/api/agents/<id>/prompt` returns 401 without Bearer. | E2E-API-10 |
| G11 | `/api/agents/../../etc/passwd` returns 400 (path traversal guard). | E2E-API-11 |
| G12 | `/api/workflows/../../etc/passwd` returns 400 (path traversal guard, workflow detail). | **E2E-API-12 (new)** |

### Surface H — Cross-cutting visual evidence

| # | Criterion |
|---|---|
| H1 | 21 screenshots captured under `.dadaia/reports/dadaia-workspace/qa-engineer/<run>/screenshots/` per QA test plan §4. |
| H2 | The DAG SVGs for `tdd-cycle`, `cross-cutting-feature`, and `spec-refinement` are visually free of overlap (manual operator review on the captured screenshots). |
| H3 | Optional: `workflow-detail-loading-state.png` capturing the DAG skeleton. P2 — add if FE delivers stable skeleton timing. |

---

## 11. Memory files affected at CLOSURE

| Memory file | Change |
|---|---|
| `specs/memory/product/index.html` | Catalog entry for "panel" updated to reflect new tab order and the new control-surface framing. No new feature added or removed; only the description and ordering. |
| `specs/memory/product/panel.html` | Rewrite of Propósito, Fluxo de uso, Diferencial, and Trigger to describe the post-R3 control surface (4 tabs, DAG visualisation, theme switcher). |
| `specs/memory/architecture.html` | Note the new `features/agents/` and `features/workflows/` modules and the new `views/assets/` split. Remove any prior reference to telemetry-fed workflow tables. |
| `specs/memory/tech-stack.html` | Verify pyyaml is recorded (already in `pyproject.toml`); no other change expected. Document as "no change: pyyaml already declared" in CLOSURE.md if unchanged. |

No changelog/history section in any memory file. Past behaviour belongs in this release's
CLOSURE.md and the archived release directory.

---

## 12. Risk register

| Risk | Likelihood | Impact | Mitigation | Owner |
|---|---|---|---|---|
| DAG layout looks cramped for `cross-cutting-feature` and `spec-refinement` (widest parallel groups). | Medium | Medium | SE delivers SVG prototype for the two hardest workflows BEFORE final renderer tuning; FE reviews on the design mockup; E2E-WF-06/07 assert no overlap. Fallback: widen `node_w`/`gap_x` or 2-column overflow band. | SE + FE |
| Asset split introduces unexpected CSP or static-route bugs. | Medium | Medium | Split is the FIRST coding task (Phase 1); everything else lands on top. E2E-TAB-05 covers `/static/*` smoke; unit test in `test_static.py` asserts the Content-Type table from §6. | SE |
| `MarkdownWorkflowStore` lacks `get_by_name` / `expected_output_path` / `must_include` flow-through. | Medium | Low | SE re-reads the store before implementation; if gaps exist, a pre-implementation task (PR3-12a) is added to PLAN/TASKS to extend the store. | SE |
| Manifest drift: `.dadaia/agentic/agents/` or `.dadaia/agentic/workflows/` out of sync with `public/`. | Medium | Low | `dadaia public doctor` catches this; R3 does NOT add a panel banner (deferred). CI gate runs `dadaia public install` before E2E. | DevOps + operator |
| Existing test surface breaks (frozen dataclass extension, telemetry aggregator with canonical overlay). | High | Low | SE §6.3 of implementation plan enumerates the breaks: `test_views_index.py` assertion update; `test_aggregator` empty-telemetry assertion update; removal of `test_reader_workflows.py`. All planned, none load-bearing. | SE |
| Hash navigation collides with existing `#agents?filter=...` cross-link. | Low | Low | FE designs the grammar `#<tab>[?key=val]` (see §7.1); same parser handles both patterns. JS module-level comment documents grammar. | FE |
| Warm-theme focus-ring contrast regression when palette tokens change. | Low | Medium | E2E-THM-07 + E2E-THM-09 (axe-core) lock the rule; CI fails on regression. | FE + QA |
| System prompt size for `software-architect.md` exceeds ~60KB → slow expand. | Low | Low | Lazy fetch on first expand; `<pre>` block bounded by max-height + scroll; copy button works regardless of length. | FE |
| Operator dissatisfied with 3 themes; wants more or different mappings. | Medium | Low | `[data-theme="X"]` extension point makes adding a 4th variant a trivial PR post-R3; do not re-open the release. | FE (post-R3) |
| `v0.1.1` and/or `agent-monitoring-v1` closures not yet written → cannot open R3 IMPLEMENTATION phase. | High | Medium | PR3-00 (the very first task) writes both closures, updates memory, archives. | PE |
| SQLite `workflows`/`workflow_agents` tables stay dead and confuse future devs. | Medium | Low | Backlog candidate filed; literal `# DEAD:` comment added in `schema.py` next to both table definitions. | SE |
| Static-route Content-Type drift if `views/static.py` ships without the locked mapping. | Low | Medium | §6 of this SPEC locks the table; unit test in `tests/features/panel/views/test_static.py` asserts Content-Type per extension; E2E-TAB-05 carries runtime smoke. | SE |
| WorkflowsService cache grows unbounded if many workflow files churn. | Low | Low | Cache size bounded by file count in source dir (12 today, ≤50 realistic). One-line code comment documents the bound. ETag deferred to backlog (P2). | SE |
| Path-traversal regex bug or symlink escape on new path-param endpoints. | Low | Medium | Regex + `Path.resolve().is_relative_to(base)` defence-in-depth check on both endpoints. E2E-API-11 and E2E-API-12 cover. | SE |

---

## 13. Definition of Done

The release is DONE when:

1. All acceptance criteria in §10 are satisfied with the listed E2E test IDs green.
2. `pytest -q` is green for unit + integration suites (~38 + ~12 tests added in R3,
   no regressions in existing tests).
3. `dadaia specs doctor` returns `[ok]` with the SPEC, PLAN, TASKS all at
   `**Status:** Aprovado` and CLOSURE drafted (the doctor invocation runs via
   `.dadaia/.venv/bin/dadaia` since the CLI is not on global PATH).
4. `dadaia public doctor` is `[ok]` for all projection targets.
5. `npx playwright test` runs the 56-test E2E suite with zero failures.
6. axe-core audits pass on the three themes (Mint, Sage, Warm).
7. 21 visual evidence screenshots captured under
   `.dadaia/reports/dadaia-workspace/qa-engineer/<run>/screenshots/` and listed in
   CLOSURE §Validations.
8. Manual operator smoke: open the panel, switch themes, expand 2 agents, open the
   `cross-cutting-feature` DAG. Operator confirms it "feels like a control surface".
9. CLOSURE.md written with all sections per template; memory updated atomically per
   §11; release `git mv`'d to `specs/_archive/releases/dadaia-workspace-panel-r3-v1/`.
10. ACTIVE.md repointed (next release or `release: none`).

---

## 14. Out of scope (re-stated for emphasis)

- Any write/mutate endpoint on the panel.
- Multi-host or remote panel access.
- Real-time push (SSE/WebSocket).
- Telemetry recompute when `pricing.py` changes (denormalisation preserved).
- opencode telemetry integration (deferred to v1.1 per `agent-monitoring-v1`).
- Workflow invocation / dispatch.
- Dark mode.
- Any change to the constitution.

---

## 15. Acceptance gate

Operator transitions `**Status:** Draft → Em revisão → Aprovado`. Once `Aprovado`,
update `specs/releases/ACTIVE.md` phase to `PLAN` and proceed to PLAN.md drafting.
