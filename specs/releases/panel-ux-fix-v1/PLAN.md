# PLAN — panel-ux-fix-v1

**Status:** Aprovado
**Release ID:** panel-ux-fix-v1
**Owner:** product-engineer
**Based on SPEC:** Aprovado (2026-05-30)

## Overview

Five targeted UX/visual fixes in the dadaia-workspace panel. All changes are confined to
`dadaia_workspace/features/panel/` and `dadaia_workspace/cli/commands/panel.py`. No new
PyPI dependencies. No data-model changes. No CI pipeline changes.

The release is queued: `go-open-source` is the currently active release. Implementation
resumes once `go-open-source` closes and this release is promoted to ACTIVE.

### Implementation status note (as of 2026-05-30)

T-PUX-02 (toggle fix), T-PUX-03 (memory pages), and T-PUX-04 (agent cards) are `[x]`
DONE. T-PUX-01 (sessions columns) and T-PUX-05 (QA validation) are `[-]` in progress.
T-PUX-06 (loopback auth bypass) is `[ ]` not yet started. The remaining critical path
is: **T-PUX-01 → T-PUX-06 → T-PUX-05**.

---

## Layers affected

| Layer | Files touched | Finding(s) |
|-------|--------------|------------|
| Panel CSS — sessions | `dadaia_workspace/features/panel/views/assets/css/sessions.py` | F2 |
| Panel view — sessions | `dadaia_workspace/features/panel/views/sessions.py` | F2 |
| Panel JS — runtime | `dadaia_workspace/features/panel/views/assets/js/runtime.js` | F3 (done) |
| Panel CSS — memory | `dadaia_workspace/features/panel/views/assets/css/memory.py` | F1 (done) |
| Panel view — wrapper | `dadaia_workspace/features/panel/views/wrapper.py` | F1 (done) |
| Panel view — agents | `dadaia_workspace/features/panel/views/agents.py` | F4 (done) |
| Panel HTTP handler | `dadaia_workspace/features/panel/handler.py` | F5 |
| Panel CLI command | `dadaia_workspace/cli/commands/panel.py` | F5 |

No other modules, services, or packages are modified.

---

## Execution order and phasing

### Phase 1 — T-PUX-01: Sessions table column widths (in progress)

**Owner:** frontend-engineer  
**Files:** `views/sessions.py`, `views/assets/css/sessions.py`

The previous fix used `<col>` percentage widths under `table-layout:fixed`, which silently
ignores `min-width` on `<col>` elements (MDN spec). The correct approach uses per-cell CSS
class selectors on every `<th>`/`<td>` pair.

Implementation steps:

1. Add `.cell-session`, `.cell-project`, `.cell-model`, `.cell-turns`, `.cell-context`,
   `.cell-cost`, `.cell-activity`, `.cell-status` rules to `sessions.css` with the
   required `min-width` floor values (120/96/160/72/80/72/112/80 px). Keep the existing
   `<colgroup>` percentage allocations for proportional rendering on wide viewports.
2. Add `overflow-x: auto` to `.sessions-table-container` (verify it is not already set).
3. In `sessions.py` HTML generation: add the matching CSS class to every `<th>` and `<td>`
   in the sessions table.
4. For Codex rows where `project` is absent: render
   `<span class="cell-placeholder" title="Project context not applicable for Codex sessions">&mdash;</span>`
   in the PROJECT cell. Add `.cell-placeholder { color: var(--color-muted); font-style: italic; }`
   to `sessions.css` (contrast ratio #666 on white = 5.52:1, AA pass).

### Phase 2 — T-PUX-06: Loopback no-token auth bypass (not started)

**Owner:** software-engineer-python  
**Files:** `dadaia_workspace/cli/commands/panel.py`, `dadaia_workspace/features/panel/handler.py`

This task has a strict dependency on T-PUX-01 completing first only in the sense that QA
(T-PUX-05) validates both together. T-PUX-06 itself has no code dependency on T-PUX-01 and
can be worked in parallel if a second implementer is available.

Implementation steps:

1. In `panel.py` (~L123): pass `loopback_bypass=(bind == "127.0.0.1")` as a new keyword
   argument to `make_handler_class()`. The `_LOOPBACK_ONLY` sentinel already exists in
   `panel.py`; the comparison `bind == "127.0.0.1"` must use a string literal matching that
   set, not the set itself.
2. In `handler.py` (~L210): add `loopback_bypass: bool = False` to `make_handler_class()`
   signature. Capture it as `_loopback_bypass` in the closure (same pattern as `_token`).
3. In `handler.py` (~L283–284): wrap the existing 401 branch so that it only fires when
   `_loopback_bypass` is False:
   ```python
   if not _loopback_bypass and (_token is None or not _validate_bearer(auth_header, _token)):
       # respond 401
   ```
4. Log one-line startup warning immediately after the `make_handler_class()` call in
   `panel.py`: `logger.warning("[PANEL] Auth disabled for loopback (127.0.0.1) connections.")`
   (or `typer.echo` if the logger is not active at that point — check existing boot log
   patterns).

Detection is at the **server bind address** (`bind == "127.0.0.1"` evaluated in `panel.py`),
not from `self.client_address[0]` at request time. This is intentional and is the security
boundary documented below.

### Phase 3 — T-PUX-05: QA validation (in progress, blocked pending T-PUX-01 + T-PUX-06)

**Owner:** qa-engineer  
**Files:** Playwright scripts under `.dadaia/tmp/qa-engineer/panel-ux-fix-v1/`

QA gates are additive — previous passing screenshots for T-PUX-02/03/04 must be
re-verified for regression before closing the release.

Mandatory assertions:
- Sessions table: all 8 column headers visible at 1280px and 768px.
- Every `tr.session-row` has exactly 8 `<td>` children.
- PROJECT column cells show `'—'` (em-dash) not empty/None for Codex rows.
- No column has computed width below declared `min-width` at 900px viewport.
- Table container overflows-x at 600px (does not collapse below 792px total).
- Codex gate: use `tests/fixtures/telemetry/seed_codex_fixture.py`; all assertions use
  `waitForSelector`, no `time.sleep`.
- Loopback-auth assertion 1: `GET /api/sessions` with no `Authorization` header returns
  200 on a panel bound to 127.0.0.1 (`loopback_bypass=True`).
- Loopback-auth assertion 2: `GET /api/sessions` with no `Authorization` header returns
  401 on a handler instantiated with `loopback_bypass=False`.

---

## Technical risks and mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `<colgroup>` percentages conflict with per-cell `min-width` at mid-range viewports | Medium | At wide viewports `<colgroup>` allocations dominate; at narrow viewports `min-width` clamps kick in. Test at 900px explicitly (Playwright assertion). |
| CSP `script-src` SHA hashes in `handler.py` become stale if inline scripts change | Low | T-PUX-01/T-PUX-06 do not touch inline script content. No SHA recomputation needed. |
| `make_handler_class()` call sites in tests pass positional `token=` — new param breaks signature | Low | `loopback_bypass` is keyword-only with default `False`. Existing call sites (`panel.py` L123, test stubs) are unaffected unless they explicitly override. Verify with `grep make_handler_class`. |
| QA Playwright test picks up stale panel process from prior session | Medium | QA must launch a fresh panel fixture per test run; no assumption of pre-running panel. |

### F5 — Security risk acceptance (loopback bypass)

**Classification:** Deliberate, documented, dev-local trade-off.

When the panel binds to `127.0.0.1`, `loopback_bypass=True` is set at boot time. From
that point, **any local process** (not just the operator's browser) can call `GET /api/*`
and read panel data without presenting a Bearer token. This is structurally identical to
how `http://localhost` services behave by convention in developer tooling.

Scope of exposure: read-only `GET` endpoints; no write or destructive operations are
exposed by the panel API in this release.

Detection boundary: the bypass is determined by the `--bind` value supplied to
`dadaia panel start`, resolved at server boot time in `panel.py`. It is NOT determined
from the TCP peer address of each incoming request. This means:

- `dadaia panel start` (default `--bind 127.0.0.1`) → bypass active for all clients.
- `dadaia panel start --bind 0.0.0.0` → bypass inactive; full Bearer enforcement.
  (Note: `--bind 0.0.0.0` is rejected by current `_LOOPBACK_ONLY` guard in `panel.py`
  in this release; enforcement path is there for when loopback restriction lifts.)

This risk is accepted by the operator. The startup warning
`[PANEL] Auth disabled for loopback (127.0.0.1) connections.` makes the bypass
observable in logs. No further mitigation is in scope for this release.

---

## Dependencies

### Intra-release

- T-PUX-05 (QA) depends on T-PUX-01 and T-PUX-06 both being complete before final
  validation can close.
- T-PUX-06 has no code dependency on T-PUX-01 but the two can only be considered
  validated together via T-PUX-05.

### Cross-release

- **panel-kanban-v1 (R3)** depends on T-PUX-06. The `/api/kanban` endpoint planned in
  panel-kanban-v1 relies on the loopback bypass being active so that the bot client can
  call the kanban API from a local process without a Bearer token. T-PUX-06 must be
  merged and available before panel-kanban-v1 begins implementation of that endpoint.
  panel-kanban-v1 must not be moved to IMPLEMENTATION until panel-ux-fix-v1 is archived.

---

## Validation plan

| Step | Description | Owner |
|------|-------------|-------|
| V1 | Playwright screenshots at 1280px + 768px for all 5 fixes | qa-engineer |
| V2 | Codex fixture gate: 8-column assertions + PROJECT='—' + h-scroll at 600px | qa-engineer |
| V3 | Loopback-auth: 200 on loopback, 401 on non-loopback handler | qa-engineer |
| V4 | WCAG AA contrast check on agent card status badges and `.cell-placeholder` | qa-engineer |
| V5 | Regression check: T-PUX-02/03/04 screenshots re-captured, no visual diff | qa-engineer |
| V6 | `pytest` suite passes (no regressions in Python unit tests) | software-engineer-python |

Evidence for V1–V5 lands in `.dadaia/reports/dadaia-workspace/qa-engineer/` (HTML report
with embedded screenshots). V6 evidence is a commit SHA with green CI output.
