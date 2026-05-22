# Spec: Release — dadaia-workspace-panel-r5-v1

> **Status:** Aprovado
> **Phase:** SPEC
> **Owner:** product-engineer
> **Release ID:** dadaia-workspace-panel-r5-v1
> **Created:** 2026-05-21
> **Discovery inputs:**
> - Design spec: `.dadaia/reports/dadaia-workspace/design-specialist/2026-05-21T000000Z-panel-overhaul-design.md`
> - Architecture review: `.dadaia/reports/dadaia-workspace/software-architect/2026-05-21T000000Z-panel-architecture-review.md`
> - Research report: `.dadaia/reports/dadaia-workspace/researcher/2026-05-21T000000Z-panel-overhaul-research.md`

---

## Vision

This release delivers a major overhaul of the dadaia-workspace panel — the
`127.0.0.1:4999` web surface — across all seven tabs, including two new tabs
(Academy and Reports), a visual identity refresh with an enlarged rhino logo, a
universal 4-zone card anatomy, a modal-based agent detail experience, in-panel
DAG zoom controls for workflows, a fix for the Sessions HTTP 503 error caused
by an uninitialized TelemetryService, and architecture cleanup that removes dead
`_assets.py` code, introduces a `window.Panel` JS module registry, promotes the
shared `escHtml` utility, and reorders the tab bar into the canonical sequence
`Projects | Agents | Workflows | Sessions | Reports | Academy | Servers`.

---

## Scope

### In-scope

| Area | Delta |
|------|-------|
| Tab bar | Reorder to canonical sequence; rename "Spec Context Projects" → "Projects"; add "Reports" and "Academy" tabs; move "Servers" to last position |
| Topbar | Remove PRIMARY badge; remove global Claude/Codex runtime toggle; enlarge rhino logo from 24px to 36px; retain Theme dropdown |
| Projects tab | Rename "Memories" section; remove N-primary counter; redesign card with repo/branch on separate rows, memory chips in horizontal pill row, session binding indicator; rename "active/inactive" → "local/remote"; remove PRIMARY badge from cards |
| Agents tab | Replace inline card expand with modal dialog; redesign collapsed card anatomy; add per-tab runtime toggle |
| Workflows tab | Add in-panel DAG zoom controls (+ / − / Fit, keyboard bindings); add per-tab runtime toggle |
| Sessions tab | Fix HTTP 503 root cause (TelemetryService wiring); redesign error state with Retry CTA; add per-tab runtime toggle |
| Academy tab | New tab rendering academy module infrastructure: list view + content view; backend `GET /api/academy` wired to existing `AcademyService` |
| Reports tab | New tab listing `.dadaia/reports/` via `.handoff.json` sidecars; list view + content view + delete with inline confirm; backend `GET /api/reports` + `/reports/<path>` |
| Logo | New minimalist stroke-based rhino SVG at 48×48 viewBox, rendered at 36×36px, `currentColor` via `--color-cost` (#633d2e) |
| Token additions | New CSS custom properties: `--color-session-bg`, `--color-modal-overlay`, `--color-modal-border`, `--color-delete-icon`, `--color-delete-icon-hover`, `--color-academy-chip-bg`, `--color-report-tag-bg`, `--color-error-bg`, `--color-error-border`, `--color-chip-memory-bg`, `--color-chip-memory-border`, `--radius-modal`, `--radius-pill`, `--shadow-card`, `--shadow-modal`, `--shadow-none`, `--z-modal-overlay`, `--z-modal`, `--z-toast`, `--duration-fast`, `--duration-normal`, `--duration-slow`, `--easing-standard`, `--easing-decelerate`, `--easing-accelerate`, `--space-2xs`, `--space-3xl`, `--modal-max-w`, `--modal-max-h`; update `--nav-h` from 44px to 48px |
| Architecture cleanup | Delete `PANEL_CSS`, `PANEL_JS`, `PALETTE` from `_assets.py`; move SVG references to `static.py`; introduce `window.Panel` registry in `core.js`; promote `escHtml` to `window.escHtml`; add route-category comment block in `handler.py` |
| Dark mode | Design-specialist token coverage for dark permutations of Mint/Sage/Warm palettes |
| Workspace resolver fix | Fix `_resolve_workspace()` to disambiguate workspace root vs repo root for `dadaia panel` from any cwd (`panel-workspace-resolver-fix` merged) |

### Out-of-scope

| Item | Reason |
|------|--------|
| Academy content modules (01–06) | Knowledge basis is missing; authoring deferred to next release |
| `panel-workflow-run-dispatcher` | Independent candidate; no blocking dependency on this release |
| `GET /api/academy` SSR vs client-side policy document | Documented in `handler.py` comment; no separate spec file |
| Favicon | Not requested |
| Animations beyond modal open/close | Not requested |
| E2E tests for new tabs | Deferred to `qa-engineer` post-implementation |
| Reports for HTML files without `.handoff.json` sidecar | Accepted known limitation: v1 of Reports tab requires sidecars as index |
| Consolidation of dual route dispatch in `handler.py` | Deferred to handler overhaul; comment-block mitigation only in this release |
| Academy slash command (`/dadaia-academy`) | Out of scope per legacy SPEC; deferred |
| Academy progress tracking / composite courses / LLM-driven content | Out of scope per legacy SPEC |

---

## Functional Requirements

### FR-1 — Tab bar canonical order

The panel navigation tab bar must render the tabs in this exact order:
`Projects | Agents | Workflows | Sessions | Reports | Academy | Servers`

The tab previously labelled "Spec Context Projects" becomes "Projects". "Servers"
moves from position 4 to position 7 (last). "Reports" and "Academy" are new entries
at positions 5 and 6 respectively.

**Acceptance:** loading the panel at `127.0.0.1:4999` shows 7 tab labels in the
specified order with no duplicates or renamed labels.

---

### FR-2 — Topbar cleanup

The topbar must show: `[36px rhino SVG] dadaia-workspace | panel [Theme dropdown]`.

Removed elements: PRIMARY badge (`.topbar-badge`), global runtime switcher
(`div.runtime-switcher`). The Theme dropdown remains.

The rhino SVG is replaced with the new 36×36px stroke-based logo (see FR-11).
The `.topbar-logo svg` CSS rule changes from `width:24px;height:24px` to
`width:36px;height:36px`.

**Acceptance:** topbar renders without PRIMARY badge or runtime switcher; logo is
visually larger (36px); Theme dropdown is present.

---

### FR-3 — Projects tab redesign

The section heading changes from "Memories" to "Projects". The counter "N active
contexts — 1 primary" is removed and replaced with "N projects" (plain count badge,
`--color-muted` style). A collapsed description block (expand toggle) explains
"Spec Context Projects" in one compressed line.

Cards are redesigned to the 4-zone anatomy (see design spec §5.2):
- Zone A (Header): project name, bold
- Zone B (Meta): `repo:` on its own row; `branch:` on its own row; both monospace,
  truncated with `text-overflow: ellipsis`
- Zone C (Session binding): conditional, shown only when `>= 1` active session is
  bound; tinted `--color-session-bg`; each session is one row with provider icon +
  truncated session name; max 3 sessions shown, "+N more" for overflow
- Zone D (Footer): three horizontal memory pill chips — Architecture, Tech Stack,
  Product — in `--color-chip-memory-bg` background, `--color-accent` border,
  `--color-accent-dark` text, `--radius-pill` border-radius

The PRIMARY badge and its left-border-primary-ring treatment are removed from all
cards. All cards get a uniform `4px solid var(--color-accent)` left accent bar.

The terms "active" / "inactive" for spec context projects are replaced by
"local" (repo is on disk) / "remote" (repo not on machine).

**Acceptance:** no card shows "PRIMARY" badge; all cards show repo and branch on
separate rows with truncation; memory chips are horizontal pills; session zone
appears only for projects with active sessions; terminology reads "local"/"remote".

---

### FR-4 — Agents tab redesign

The global runtime switcher is moved from the topbar into the Agents tab section
header, right-aligned (`margin-left: auto`) using the existing `.runtime-switcher`
CSS class.

The inline card expansion (`.agent-card__detail`) is replaced by a modal dialog.
Clicking any agent card opens a centered modal (`<dialog>` or `<div role="dialog"
aria-modal="true" aria-labelledby="agent-modal-title">`) with full agent details
(description, skills, tools, metrics, recent sessions, system prompt) while the
card grid remains compact and visible behind the dimmed overlay.

The collapsed card renders Zones A–D per design spec §6.2: status badge + name
(Zone A), 2-line-clamp description (Zone B), 3-column stats row (Zone C), skill
chips (Zone D). The inline expand chevron is removed.

The modal follows the design spec §3 and §6.3 pattern:
- `role="dialog"`, `aria-modal="true"`, `aria-labelledby="agent-modal-title"`
- Focus trap: Tab cycles inside modal; Escape closes; focus returns to triggering card
- Close button: 44×44px minimum, `aria-label="Close"`
- Animation: opacity 0→1, translateY(12px)→0, 250ms, `--easing-decelerate`
- `prefers-reduced-motion`: no transform, instant opacity

**Acceptance:** clicking any agent card opens a modal with full details; the card
grid does not reflow; Escape closes the modal; focus is trapped inside the modal
while open; screen reader sees `role="dialog"` and `aria-labelledby`.

---

### FR-5 — Workflows tab DAG zoom

A zoom control toolbar is added to the workflow detail view, above the DAG SVG.
The toolbar includes: `[−]` (zoom out), `[zoom%]` (current zoom display), `[+]`
(zoom in), `[Fit]` (reset to fit). Zoom range: 50%–300%, step 25%.

The SVG is wrapped in `div.workflow-dag-viewport` with `overflow: hidden`. The SVG
receives a CSS `transform: scale(N)` driven by JS. Container `min-height: 280px`.

Keyboard bindings: `+` zooms in, `−` zooms out, `0` fits — active when focus is
within the DAG section.

The per-tab runtime toggle is added to the Workflows section header (same pattern
as FR-4 for Agents).

**Acceptance:** workflow detail view shows zoom toolbar; clicking + zooms DAG SVG
in-place without browser zoom; `[Fit]` resets to 100%; keyboard shortcuts work.

---

### FR-6 — Sessions tab 503 fix and error state

The TelemetryService wiring in the panel boot path (`panel.py`) is fixed so that
the service is reliably initialized at startup. The specific failure modes
identified by the software-architect (SQLite migration failure, file-lock
contention, PermissionError when running as root) must be handled with
appropriate diagnostic logging rather than silent `None` assignment.

The error state UI is redesigned per design spec §8.2: the error container spans
the full table body area (not just one cell); it includes a `[Retry]` button
(`role="alert"`, `aria-live` or re-render on click); the heading uses
`--color-cost` (#633d2e); body text uses `--color-muted`.

The per-tab runtime toggle is added to the Sessions section header.

**Acceptance:** starting the panel on a clean workspace does not produce HTTP 503
on `GET /api/sessions` unless TelemetryService genuinely cannot initialize (root
guard, truly inaccessible state dir); when 503 occurs, the UI shows the redesigned
error state with a functional Retry button.

---

### FR-7 — Academy tab (infrastructure only)

A new "Academy" tab is added to the panel. The tab renders:

**List view:** a grid of academy module cards populated from `GET /api/academy`
(which calls `AcademyService.list_all()` and serializes the result). Each card
follows the 4-zone anatomy: Zone A (type chip), Zone B (module title), Zone C
(description, 2-line clamp), Zone D ("Open →" CTA). The card left accent is
`4px solid var(--color-warning-bg)` (warm olive).

**Content view:** clicking a module card renders the module HTML content inline
inside a scoped `<div>` with padding and a `[← Back to Academy]` breadcrumb.

If no modules exist (knowledge basis is empty), the tab renders an empty state:
"No academy modules available. Run `dadaia academy create` to add a module."

**Acceptance:** Academy tab appears in the nav; API responds without 500; an empty
state is shown when no courses exist; any existing courses render as cards.

---

### FR-8 — Reports tab

A new "Reports" tab is added to the panel. The tab renders:

**List view:** reports grouped by context (`<details>` / `<summary>` collapsible
per context group), indexed by `.handoff.json` sidecars from `.dadaia/reports/`.
Populated by `GET /api/reports` (traverses the reports directory, reads sidecars,
returns list sorted by `produced_at` descending). Each row shows: agent tag chip,
report title, date, trash icon button. The trash button shows an inline
"Are you sure? [Delete] [Cancel]" confirmation before calling `DELETE /api/reports/<path>`.

**Content view:** clicking a report title renders the HTML inline in a scoped `<div>`
with `max-height: 80vh` and `[← Back to Reports]` breadcrumb. Content is served by
`GET /reports/<path>` with a server-side path-traversal guard bounding to
`.dadaia/reports/`.

Reports without a `.handoff.json` sidecar are not shown (accepted known limitation).

**Accessibility:** delete button is 44×44px touch target; `aria-label="Delete report:
[title]"` is dynamic; report title button has `aria-label="Open report: [title]"`.

**Acceptance:** Reports tab appears in nav; list loads grouped by context; clicking
a report title renders its HTML inline; delete workflow shows inline confirm; reports
without sidecars are not visible.

---

### FR-9 — Architecture cleanup

The following dead code and coupling issues are resolved in this release:

1. **`_assets.py` cleanup:** `PANEL_CSS`, `PANEL_JS`, and `PALETTE` are deleted
   from `_assets.py`. The live dependency (`LOGO_RHINO_24`) moves to `static.py` or
   is inlined directly into `index.py`. The `_assets.py` import in `index.py` is
   removed.

2. **`window.Panel` registry:** a lightweight `window.Panel = { register(name, module),
   activate(name, opts) }` registry object is introduced in `core.js` before the tab
   loading logic. Existing `window.Agents` and `window.Workflows` registrations are
   migrated to use `window.Panel.register`. New tabs (Academy, Reports) also register
   via `window.Panel`.

3. **`escHtml` shared utility:** `escHtml` is promoted to `window.escHtml` in
   `core.js`. All new JS modules (academy.js, reports.js) use `window.escHtml`.
   Each existing local copy in `agents.js`, `workflows.js`, and `sessions.js` receives
   a `// TODO: replace with window.escHtml when touching this file` comment.

4. **`handler.py` route-category comment:** a comment block is added to `handler.py`
   enumerating the three route categories (public, bearer-only, bearer+telemetry)
   with their current members, to prevent silent mis-categorization of new routes.

**Acceptance:** `_assets.py` does not define `PANEL_CSS`, `PANEL_JS`, or `PALETTE`;
`core.js` defines `window.Panel`; new JS files use `window.Panel.register` and
`window.escHtml`; existing files retain local `escHtml` with TODO comment.

---

### FR-10 — Dark mode token coverage

The design-specialist token additions include the complete set of new tokens
required for dark permutations of the three palettes (Mint/Sage/Warm). This release
adds all new CSS custom property definitions to `tokens.py` so that dark-mode
palette overrides can be applied without further token additions.

**Note:** the actual dark palette values (dark variants of `--color-bg`,
`--color-surface`, etc.) are specified in the design spec §1.2–§1.10 token tables.
Implementation adds the named tokens; the dark palette is toggled via the existing
Theme dropdown.

**Acceptance:** all tokens listed in design spec §1.2–§1.10 as `[NEW]` are present
in `tokens.py`; no raw hex values appear in new CSS rules outside of `tokens.py`.

---

### FR-11 — Logo redesign

The rhino SVG is redesigned as a minimalist stroke-based illustration at 48×48
viewBox, rendered at 36×36px in the topbar. Key anatomical elements: body mass,
head (block shape), horn (filled triangle), ear (small triangle), eye (filled circle
r=1.5), four legs (short rectangular stubs), tail (curved open stroke).

All paths use `stroke="currentColor"`, `stroke-width="1.5"`, `stroke-linejoin="round"`,
`stroke-linecap="round"`. Body and head fills: `fill="currentColor"`,
`fill-opacity="0.12"`. Horn and ear: `fill="currentColor"` (fully opaque).

The color is inherited from `.topbar-logo` which is `var(--color-cost, #633d2e)` —
7.5:1 contrast ratio on white topbar background (WCAG AAA).

**Files:**
- `dadaia_workspace/features/panel/views/assets/logo-rhino-36.svg` (new)
- `dadaia_workspace/features/panel/views/assets/logo-rhino-24.svg` (updated to match new design)
- `dadaia_workspace/features/panel/views/assets/logo-rhino-16.svg` (retained as-is)

**Acceptance:** topbar shows the enlarged rhino logo at 36×36px; logo is clearly
recognizable as a rhinoceros with horn; `currentColor` is the only color expression;
no hardcoded hex in the SVG files.

---

### FR-12 — A11y compliance for new components

All new components in this release meet WCAG 2.2 AA:

| Component | A11y requirement |
|-----------|-----------------|
| Modal (AgentModal) | `role="dialog"`, `aria-modal="true"`, `aria-labelledby`; focus trap; Escape closes; return focus on close |
| Delete button (Reports) | 44×44px touch target; dynamic `aria-label`; no label text (icon-only with tooltip) |
| Zoom controls (WorkflowDagViewer) | `aria-label` on each button; keyboard bindings (`+`, `−`, `0`) |
| Nav tabs (all) | `--nav-h` increased to 48px; tab padding `0.75rem 1.1rem` for reliable 44px touch target |
| Session error state | `role="alert"` on container; Retry is a `<button>` with explicit text |
| `scroll-margin-top` | Applied to cards and modal triggers: `calc(var(--topbar-h) + var(--nav-h) + var(--space-sm))` |

---

## Non-Functional Requirements

### NFR-1 — Performance

- `GET /api/reports` must respond within 2 seconds for up to 200 `.handoff.json`
  sidecars. Filesystem traversal is synchronous; if the count grows beyond 500,
  pagination should be introduced (deferred).
- `GET /api/academy` must respond within 500ms (small dataset; `AcademyService.list_all()`
  reads a single JSON file).
- The new modal animation (250ms) must not cause layout thrash; use CSS transitions on
  `opacity` and `transform` only (compositor-promoted properties).

### NFR-2 — Security

- `GET /reports/<path>` must validate that the resolved absolute path starts with
  `<workspace_root>/.dadaia/reports/`. Any path outside this boundary returns HTTP 403.
- `DELETE /api/reports/<path>` applies the same traversal guard before deleting.
- No new inline `<script>` tags are added to `index.py` without updating the CSP
  `script-src` hash list in `handler.py`.
- Academy content rendered via `innerHTML` into a scoped `<div>` must not execute
  scripts from the academy HTML. If academy modules contain `<script>` tags, they are
  stripped server-side before serving. (If the operator decides an `<iframe sandbox>`
  is required for academy content, this becomes an amendment in the CLOSURE drift
  section.)

### NFR-3 — Accessibility

All new UI components comply with WCAG 2.2 AA as enumerated in FR-12. The
`prefers-reduced-motion` media query is respected for modal animations: no transform,
instant opacity change.

### NFR-4 — Backward compatibility

- The existing Python test suite (`tests/`) must continue to pass without modification
  to test files. New functionality is covered by new tests.
- The `_assets.py` cleanup must not break the `LOGO_RHINO_24` import that `index.py`
  currently relies on; the logo embed path moves to `static.py` or `index.py` directly.
- The `window.Panel` registry is additive; existing module globals (`window.Agents`,
  `window.Workflows`, `window.Runtime`) remain accessible for backward compatibility
  during the migration.

---

## Architecture Decisions

The following anti-patterns identified by software-architect are addressed in this
release:

| Anti-pattern | Severity | This release action |
|---|---|---|
| `_assets.py` dead code (`PANEL_CSS`, `PANEL_JS`, `PALETTE`) | CRITICAL | **Fixed** — removed in FR-9 |
| `window.*` global coupling, no module registry | HIGH | **Fixed** — `window.Panel` registry introduced in FR-9 |
| `escHtml` duplicated 4× across JS files | MEDIUM | **Partially fixed** — promoted to `window.escHtml` in core.js; new files use it; existing files get TODO comment |
| Dual route dispatch in `handler.py` | HIGH | **Deferred** — comment-block mitigation only (FR-9 item 4); full consolidation is a separate release |
| SSR vs client-side fetch policy undocumented | MEDIUM | **Deferred** — documented via module docstring in `views/index.py`; policy: SSR for public small-payload data (contexts, servers, academy); client-side for auth-gated or large/dynamic data (agents, sessions, workflows, reports) |

The telemetry 503 root cause (`_telemetry is None`) is fixed in FR-6 by hardening
`_try_build_telemetry()` in `panel.py` with per-exception-type handling and
meaningful warning logs instead of a silent bare `except Exception: return None`.

---

## Open Questions

The following questions emerged from the design-specialist discovery and must be
resolved by the operator before PLAN is approved. Answers should be recorded in the
PLAN as decisions.

| # | Question | Default if unanswered |
|---|---|---|
| OQ-1 | The Theme dropdown is retained in the topbar. The operator said "remove Claude/Codex global toggle from topbar" — does the Theme dropdown also move, or does it stay? | **Default: Theme stays in topbar** (design spec §12.1 retains it; operator only mentioned the runtime toggle for removal) |
| OQ-2 | The delete confirmation for Reports rows is specified as an inline row confirmation (no modal). If the operator prefers a modal or a toast-with-undo pattern, the frontend-engineer must be redirected. | **Default: inline row confirmation** (as per design spec §10.1) |
| OQ-3 | Academy HTML content injection is specified as a sandboxed `<div>` (not an `<iframe>`). If academy modules contain inline scripts, an `<iframe sandbox>` is safer. Confirm the security model for academy content rendering. | **Default: `<div>` with server-side script stripping** (NFR-2) |
| OQ-4 | The DAG zoom range is 50%–300%, step 25%, with a `min-height: 280px` floor. If specific workflows have very wide SVGs, the engineer may need to adjust initial fit-zoom calculation. Should the Fit button compute a content-aware initial scale or always reset to 1.0? | **Default: Fit resets to scale(1.0) and centers** (design spec §7.3 "Fit" spec) |
| OQ-5 | The researcher report flags that reports without `.handoff.json` sidecars are not visible in the Reports tab (75 sidecars exist; some early reports lack them). Is this accepted as a known limitation for v1, or should the Reports API also scan for orphan HTML files? | **Default: sidecar-indexed only** (accepted known limitation per architecture review §6) |

---

## Dependencies

| Dependency | Type | Notes |
|---|---|---|
| `dadaia-workspace-brand-identity-v1` | SPEC | Status: Aprovado; all brand tokens (`--color-accent`, `--color-cost`, `--color-warning-bg`, `--color-alert`, `--color-accent-secondary`) are already in `tokens.py`. This release adds new tokens on top of those — no conflict. |
| Existing `TelemetryService` | Runtime | The Sessions 503 fix requires the existing telemetry backend; no schema changes to the SQLite store are needed |
| Existing `AcademyService` | Runtime | `AcademyService.list_all()` is already wired in `container.py`; the panel boot path (`panel.py`) needs to accept it via DI |
| `.dadaia/reports/` filesystem | Runtime | Reports tab depends on existing `.handoff.json` sidecar files; no schema changes to the sidecar format |
| `dadaia public stage` + `dadaia public install` | Deploy | New CSS tokens in `tokens.py` are part of the panel Python package; no new public assets pipeline changes needed |

---

## Out of Scope (explicit restatement)

- Academy content modules (knowledge basis files 01–06): deferred to next release
- `panel-workflow-run-dispatcher`: independent candidate, not in this release
- Reports tab for HTML files without `.handoff.json` sidecars: accepted known limitation
- Dual route dispatch consolidation in `handler.py`: deferred to handler overhaul release
- E2E test coverage for new tabs (Academy, Reports): deferred to qa-engineer post-implementation
- Any changes to `specs/memory/*.html` files (CLOSURE phase only)

---

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| `_assets.py` cleanup breaks LOGO_RHINO_24 import | Medium | Explicitly move SVG reference to `static.py` before removing import from `index.py`; test build before removing |
| TelemetryService fix introduces startup regression | Low | Keep `_try_build_telemetry()` non-throwing; only change exception handling from bare `except` to per-type with logging |
| Academy tab DI wiring misses panel boot path | Medium | Phase A task explicitly wires `AcademyService` in `panel.py` composition root |
| Modal focus trap breaks in older browsers | Low | Use native `<dialog>` element where supported; `inert` attribute fallback is documented |
| Reports path traversal guard incomplete | High | Server-side validation must use `os.path.realpath()` to resolve symlinks before prefix check |
